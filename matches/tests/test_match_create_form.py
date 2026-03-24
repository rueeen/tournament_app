from django.contrib.auth.models import User
from django.test import TestCase

from decks.models import Deck
from matches.forms import MatchCreateForm


class MatchCreateFormTests(TestCase):
    def test_participants_include_superuser_even_without_deck(self):
        creator = User.objects.create_user(username='creator', password='testpass123')
        Deck.objects.create(owner=creator, name='Creator Deck')

        super_admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass123',
        )

        form = MatchCreateForm(user=creator)

        self.assertIn(super_admin, form.fields['participants'].queryset)

    def test_participants_exclude_regular_users_without_decks(self):
        creator = User.objects.create_user(username='creator2', password='testpass123')
        Deck.objects.create(owner=creator, name='Creator Deck 2')

        with_deck = User.objects.create_user(username='withdeck', password='testpass123')
        Deck.objects.create(owner=with_deck, name='Playable Deck')

        without_deck = User.objects.create_user(username='withoutdeck', password='testpass123')

        form = MatchCreateForm(user=creator)
        queryset = form.fields['participants'].queryset

        self.assertIn(with_deck, queryset)
        self.assertNotIn(without_deck, queryset)
