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
    query = f'{term} type:legendary type:creature game:paper'
    url = SCRYFALL_SEARCH_URL.format(query=quote_plus(query))
    request = Request(url, headers={'User-Agent': 'tournament-app/1.0'})

    try:
        with urlopen(request, timeout=6) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return []

    cards = payload.get('data', [])[:limit]
    return [serialize_commander(card) for card in cards]


def serialize_commander(card):
    image_uris = card.get('image_uris', {})
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
