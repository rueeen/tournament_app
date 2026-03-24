from unittest.mock import patch

from django.test import SimpleTestCase

from decks import services


class SearchCommandersTests(SimpleTestCase):
    def test_fallback_query_returns_commander_legal_cards(self):
        with patch('decks.services._fetch_cards') as mock_fetch_cards:
            mock_fetch_cards.side_effect = [
                [],
                [
                    {
                        'id': 'card-1',
                        'name': 'Cloud, Ex-SOLDIER',
                        'type_line': 'Legendary Creature — Human Soldier',
                        'color_identity': ['R', 'W'],
                        'image_uris': {'art_crop': 'https://img.test/cloud.jpg'},
                    }
                ],
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

    def test_serialize_commander_uses_card_face_image_when_missing_top_level_image(self):
        card = {
            'id': 'face-card',
            'name': 'Sample Front // Sample Back',
            'color_identity': ['U'],
            'card_faces': [
                {
                    'image_uris': {
                        'normal': 'https://img.test/face.jpg',
                    }
                }
            ],
        }

        payload = services.serialize_commander(card)

        self.assertEqual(payload['image_url'], 'https://img.test/face.jpg')
