from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from decks.models import Deck
from matches.models import Match, MatchInvitation, MatchPlayer


class MatchAccessAndClosureTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='creator2', password='testpass123')
        self.invited = User.objects.create_user(username='invited2', password='testpass123')
        self.other = User.objects.create_user(username='other2', password='testpass123')

        self.creator_deck = Deck.objects.create(owner=self.creator, name='Creator Deck 2')
        self.invited_deck = Deck.objects.create(owner=self.invited, name='Invited Deck 2')

    def _create_match_with_pending_invitation(self):
        match = Match.objects.create(created_by=self.creator, status=Match.Status.IN_PROGRESS)
        MatchPlayer.objects.create(match=match, user=self.creator, deck=self.creator_deck)
        invitation = MatchInvitation.objects.create(match=match, invited_user=self.invited, invited_by=self.creator)
        return match, invitation

    def test_invited_user_can_open_match_detail_from_notification_link(self):
        match, _ = self._create_match_with_pending_invitation()
        self.client.force_login(self.invited)

        response = self.client.get(reverse('match_detail', kwargs={'pk': match.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Detalle partida #{match.id}')

    def test_match_detail_hides_propose_button_while_invitations_are_pending(self):
        match, _ = self._create_match_with_pending_invitation()
        self.client.force_login(self.creator)

        response = self.client.get(reverse('match_detail', kwargs={'pk': match.id}))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Proponer resultado')
        self.assertContains(response, 'todas las invitaciones estén aceptadas')

    def test_propose_result_is_blocked_if_some_invitation_is_not_accepted(self):
        match, _ = self._create_match_with_pending_invitation()
        self.client.force_login(self.creator)

        response = self.client.get(reverse('propose_result', kwargs={'pk': match.id}))

        self.assertRedirects(response, reverse('match_detail', kwargs={'pk': match.id}))

