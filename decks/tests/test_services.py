import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.test import SimpleTestCase

from decks import services


class SearchCommandersTests(SimpleTestCase):
    def test_search_commanders_includes_planeswalker_commander_clause(self):
        with patch('decks.services._fetch_cards_paginated') as mock_fetch_cards:
            mock_fetch_cards.return_value = []

            services.search_commanders('tevesh')

        query_sent = mock_fetch_cards.call_args.args[0]
        self.assertIn('type:legendary', query_sent)
        self.assertIn('type:creature', query_sent)
        self.assertIn('type:planeswalker oracle:"can be your commander"', query_sent)

    def test_fallback_named_query_returns_commander_legal_cards(self):
        with patch('decks.services._fetch_cards_paginated') as mock_fetch_cards, patch(
            'decks.services._fetch_named_candidates'
        ) as mock_named_candidates:
            mock_fetch_cards.return_value = []
            mock_named_candidates.return_value = [
                {
                    'id': 'card-1',
                    'name': 'Cloud, Ex-SOLDIER',
                    'type_line': 'Legendary Creature — Human Soldier',
                    'color_identity': ['R', 'W'],
                    'image_uris': {'large': 'https://img.test/cloud-large.jpg', 'art_crop': 'https://img.test/cloud.jpg'},
                }
            ]

            results = services.search_commanders('Cloud, Ex-SOLDIER')

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'Cloud, Ex-SOLDIER')
        self.assertEqual(results[0]['color_identity'], ['R', 'W'])

    def test_is_commander_legal_allows_oracle_text_commanders(self):
        card = {
            'type_line': 'Legendary Planeswalker — Jeska',
            'oracle_text': 'Jeska can be your commander.',
        }

        self.assertTrue(services.is_commander_legal(card))

    def test_is_commander_legal_uses_faces_oracle_text(self):
        card = {
            'type_line': 'Legendary Artifact',
            'card_faces': [
                {'oracle_text': 'Front text.'},
                {'oracle_text': 'This can be your commander.'},
            ],
        }

        self.assertTrue(services.is_commander_legal(card))

    def test_serialize_commander_uses_card_face_image_when_missing_top_level_image(self):
        card = {
            'id': 'face-card',
            'name': 'Sample Front // Sample Back',
            'color_identity': ['U'],
            'card_faces': [
                {
                    'image_uris': {
                        'large': 'https://img.test/face-large.jpg',
                        'normal': 'https://img.test/face.jpg',
                    }
                }
            ],
        }

        payload = services.serialize_commander(card)

        self.assertEqual(payload['image_url'], 'https://img.test/face-large.jpg')


class ScryfallClientBehaviorTests(SimpleTestCase):

    def test_parse_payload_text_supports_escaped_json_string(self):
        raw_text = '"{\"object\":\"list\",\"data\":[{\"id\":\"abc\"}]}"'

        payload = services._parse_payload_text(raw_text)

        self.assertEqual(payload.get('object'), 'list')
        self.assertEqual(payload.get('data')[0]['id'], 'abc')

    def test_parse_payload_text_supports_concatenated_json(self):
        raw_text = '{"object":"list","data":[{"id":"first"}],"has_more":false}{"object":"list","data":[{"id":"second"}]}'

        payload = services._parse_payload_text(raw_text)

        self.assertEqual(payload.get('data')[0]['id'], 'first')

    def test_fetch_cards_paginated_uses_next_page_until_limit(self):
        with patch('decks.services._fetch_payload_from_url') as mock_payload:
            mock_payload.side_effect = [
                {
                    'object': 'list',
                    'data': [{'id': '1'}, {'id': '2'}],
                    'has_more': True,
                    'next_page': 'https://api.scryfall.com/cards/search?page=2',
                },
                {
                    'object': 'list',
                    'data': [{'id': '3'}],
                    'has_more': False,
                },
            ]

            cards = services._fetch_cards_paginated('atraxa', limit=3)

        self.assertEqual([card['id'] for card in cards], ['1', '2', '3'])

    def test_fetch_payload_retries_on_429(self):
        error_payload = json.dumps(
            {
                'object': 'error',
                'status': 429,
                'code': 'rate_limited',
                'details': 'Slow down.',
            }
        ).encode('utf-8')

        first_error = HTTPError(
            url='https://api.scryfall.com/cards/named?exact=test',
            code=429,
            msg='Too Many Requests',
            hdrs=None,
            fp=MagicMock(read=MagicMock(return_value=error_payload)),
        )

        success_response = MagicMock()
        success_response.__enter__.return_value = success_response
        success_response.read.return_value = b'{"object":"card","id":"ok"}'

        with patch('decks.services.urlopen', side_effect=[first_error, success_response]), patch(
            'decks.services.time.sleep'
        ) as mock_sleep:
            payload = services._fetch_payload_from_url('https://api.scryfall.com/cards/named?exact=test')

        self.assertEqual(payload.get('id'), 'ok')
        mock_sleep.assert_called_once()

    def test_parse_http_error_extracts_scryfall_error_fields(self):
        error_payload = b'{"object":"error","status":404,"code":"not_found","details":"No card found."}'
        exc = HTTPError(
            url='https://api.scryfall.com/cards/named?exact=zzz',
            code=404,
            msg='Not Found',
            hdrs=None,
            fp=MagicMock(read=MagicMock(return_value=error_payload)),
        )

        parsed = services._parse_http_error(exc)

        self.assertEqual(parsed.status, 404)
        self.assertEqual(parsed.code, 'not_found')
        self.assertEqual(parsed.details, 'No card found.')
