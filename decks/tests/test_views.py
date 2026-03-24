from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from decks.models import Deck, DeckColor


class DeckCreateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='testpass123')
        self.client.login(username='tester', password='testpass123')
        self.green, _ = DeckColor.objects.get_or_create(name=DeckColor.ColorChoices.GREEN)

    def test_duplicate_deck_name_shows_validation_message(self):
        Deck.objects.create(owner=self.user, name='Mazo Único')

        response = self.client.post(
            reverse('deck_create'),
            data={'name': 'Mazo Único', 'colors': [self.green.id]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya tienes un mazo con ese nombre.')
        self.assertEqual(Deck.objects.filter(owner=self.user, name='Mazo Único').count(), 1)
