import json
import logging
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

SCRYFALL_SEARCH_URL = 'https://api.scryfall.com/cards/search?q={query}'
SCRYFALL_NAMED_URL = 'https://api.scryfall.com/cards/named?{query}'
DEFAULT_TIMEOUT_SECONDS = 6
MAX_RETRIES = 2
BACKOFF_BASE_SECONDS = 0.3
CACHE_TTL_SECONDS = 300

logger = logging.getLogger(__name__)

COLOR_NAME_MAP = {
    'W': 'Plains',
    'U': 'Island',
    'B': 'Swamp',
    'R': 'Mountain',
    'G': 'Forest',
}

_payload_cache: dict[str, tuple[float, dict[str, Any]]] = {}


@dataclass
class ScryfallError:
    status: int | None
    code: str | None
    details: str


def search_commanders(term, limit=8):
    """Search commanders in Scryfall.

    Strategy:
    1) Query /cards/search with commander-oriented filters.
    2) If no rows are returned, try /cards/named exact and fuzzy lookups.
    3) Serialize cards to the shape expected by the frontend.
    """
    clean_term = term.strip()
    if not clean_term:
        return []

    primary_query = f'{clean_term} type:legendary type:creature game:paper'
    cards = _fetch_cards_paginated(primary_query, limit=limit)

    if not cards:
        fallback_cards = _fetch_named_candidates(clean_term)
        cards = [card for card in fallback_cards if is_commander_legal(card)][:limit]

    return [serialize_commander(card) for card in cards]


def _fetch_named_candidates(term):
    candidates = []

    exact_payload = _fetch_payload_from_url(
        SCRYFALL_NAMED_URL.format(query=f'exact={quote_plus(term)}')
    )
    if exact_payload and exact_payload.get('object') == 'card':
        candidates.append(exact_payload)

    fuzzy_payload = _fetch_payload_from_url(
        SCRYFALL_NAMED_URL.format(query=f'fuzzy={quote_plus(term)}')
    )
    if (
        fuzzy_payload
        and fuzzy_payload.get('object') == 'card'
        and fuzzy_payload.get('id') not in {card.get('id') for card in candidates}
    ):
        candidates.append(fuzzy_payload)

    return candidates


def _fetch_cards_paginated(query, limit):
    cards = []
    next_url = SCRYFALL_SEARCH_URL.format(query=quote_plus(query))

    while next_url and len(cards) < limit:
        payload = _fetch_payload_from_url(next_url)
        if not payload or payload.get('object') != 'list':
            break

        cards.extend(payload.get('data', []))
        if not payload.get('has_more'):
            break
        next_url = payload.get('next_page')

    return cards[:limit]


def _fetch_payload_from_url(url):
    now = time.monotonic()
    cache_hit = _payload_cache.get(url)
    if cache_hit and cache_hit[0] > now:
        return cache_hit[1]

    request = Request(url, headers={'User-Agent': 'tournament-app/1.1'})

    for attempt in range(MAX_RETRIES + 1):
        try:
            with urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode('utf-8'))
                _payload_cache[url] = (now + CACHE_TTL_SECONDS, payload)
                return payload
        except HTTPError as exc:
            error = _parse_http_error(exc)
            if _is_retryable_status(exc.code) and attempt < MAX_RETRIES:
                time.sleep(BACKOFF_BASE_SECONDS * (2**attempt))
                continue

            logger.warning(
                'Scryfall HTTP error status=%s code=%s details=%s url=%s',
                error.status,
                error.code,
                error.details,
                url,
            )
            return None
        except (URLError, TimeoutError) as exc:
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_BASE_SECONDS * (2**attempt))
                continue
            logger.warning('Scryfall network error: %s url=%s', exc, url)
            return None
        except json.JSONDecodeError:
            logger.warning('Scryfall returned invalid JSON url=%s', url)
            return None

    return None


def _is_retryable_status(status_code):
    return status_code == 429 or 500 <= status_code <= 599


def _parse_http_error(exc):
    status = getattr(exc, 'code', None)
    details = str(exc)
    code = None

    try:
        raw_body = exc.read().decode('utf-8')
        payload = json.loads(raw_body)
        if isinstance(payload, dict) and payload.get('object') == 'error':
            details = payload.get('details') or details
            code = payload.get('code')
    except Exception:  # noqa: BLE001
        pass

    return ScryfallError(status=status, code=code, details=details)


def is_commander_legal(card):
    typeline = (card.get('type_line') or '').lower()
    oracle_text = _combined_oracle_text(card)

    if 'legendary' in typeline and 'creature' in typeline:
        return True

    if 'can be your commander' in oracle_text:
        return True

    legalities = card.get('legalities') or {}
    return legalities.get('commander') == 'legal'


def _combined_oracle_text(card):
    oracle_text = (card.get('oracle_text') or '').lower()
    if oracle_text:
        return oracle_text

    card_faces = card.get('card_faces') or []
    face_texts = [((face or {}).get('oracle_text') or '').lower() for face in card_faces]
    return ' '.join(text for text in face_texts if text)


def serialize_commander(card):
    image_url = _extract_image_url(card)
    color_identity = card.get('color_identity', [])

    return {
        'id': card.get('id'),
        'name': card.get('name', ''),
        'image_url': image_url,
        'color_identity': color_identity,
        'land_suggestion': land_suggestion(color_identity),
    }


def _extract_image_url(card):
    image_uris = card.get('image_uris') or {}
    if image_uris:
        return image_uris.get('art_crop') or image_uris.get('normal', '')

    card_faces = card.get('card_faces') or []
    for face in card_faces:
        face_uris = (face or {}).get('image_uris') or {}
        if face_uris:
            return face_uris.get('art_crop') or face_uris.get('normal', '')

    return ''


def land_suggestion(color_identity, total_lands=36):
    if not color_identity:
        return [{'land': 'Wastes', 'count': total_lands}]

    per_color, remainder = divmod(total_lands, len(color_identity))
    suggestions = []
    for index, color in enumerate(color_identity):
        suggestions.append(
            {
                'land': COLOR_NAME_MAP.get(color, 'Land'),
                'count': per_color + (1 if index < remainder else 0),
            }
        )
    return suggestions
