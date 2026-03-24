import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

SCRYFALL_SEARCH_URL = 'https://api.scryfall.com/cards/search?q={query}'
COLOR_NAME_MAP = {
    'W': 'Plains',
    'U': 'Island',
    'B': 'Swamp',
    'R': 'Mountain',
    'G': 'Forest',
}


def search_commanders(term, limit=8):
    """Search commanders in Scryfall.

    First we prioritize true EDH commanders (legendary creatures in paper).
    If Scryfall returns no rows for that strict query, we run a fallback by name
    and keep cards that are commander-legal (legendary creature or explicit
    "can be your commander" text).
    """
    primary_query = f'{term} type:legendary type:creature game:paper'
    cards = _fetch_cards(primary_query, limit=limit)

    if not cards:
        fallback_query = f'!"{term}" game:paper'
        fallback_cards = _fetch_cards(fallback_query, limit=limit * 2)
        cards = [card for card in fallback_cards if is_commander_legal(card)][:limit]

    return [serialize_commander(card) for card in cards]


def _fetch_cards(query, limit):
    payload = _fetch_payload(query)
    if not payload:
        return []
    return payload.get('data', [])[:limit]


def _fetch_payload(query):
    url = SCRYFALL_SEARCH_URL.format(query=quote_plus(query))
    request = Request(url, headers={'User-Agent': 'tournament-app/1.0'})

    try:
        with urlopen(request, timeout=6) as response:
            return json.loads(response.read().decode('utf-8'))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def is_commander_legal(card):
    typeline = (card.get('type_line') or '').lower()
    oracle_text = (card.get('oracle_text') or '').lower()

    return (
        'legendary' in typeline and 'creature' in typeline
    ) or 'can be your commander' in oracle_text


def serialize_commander(card):
    image_uris = card.get('image_uris', {})
    if not image_uris:
        card_faces = card.get('card_faces') or []
        if card_faces:
            image_uris = card_faces[0].get('image_uris', {})

    image_url = image_uris.get('art_crop') or image_uris.get('normal', '')
    color_identity = card.get('color_identity', [])

    return {
        'id': card.get('id'),
        'name': card.get('name', ''),
        'image_url': image_url,
        'color_identity': color_identity,
        'land_suggestion': land_suggestion(color_identity),
    }


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
