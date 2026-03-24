from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from decks.models import Deck
from matches.models import Match, MatchInvitation, MatchNotification, MatchPlayer, MatchResultAcceptance, MatchResultProposal


class NotificationFlowTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='creator', password='testpass123')
        self.invited = User.objects.create_user(username='invited', password='testpass123')
        self.third = User.objects.create_user(username='third', password='testpass123')

        self.creator_deck = Deck.objects.create(owner=self.creator, name='Creator Deck')
        self.invited_deck = Deck.objects.create(owner=self.invited, name='Invited Deck')
        self.third_deck = Deck.objects.create(owner=self.third, name='Third Deck')

    def _build_match(self):
        match = Match.objects.create(created_by=self.creator, status=Match.Status.IN_PROGRESS)
        MatchPlayer.objects.create(match=match, user=self.creator, deck=self.creator_deck)
        MatchPlayer.objects.create(match=match, user=self.invited, deck=self.invited_deck)
        return match

    def test_invitation_creation_generates_structured_notification(self):
        match = Match.objects.create(created_by=self.creator)
        MatchInvitation.objects.create(match=match, invited_user=self.invited, invited_by=self.creator)

        notification = MatchNotification.objects.get(recipient=self.invited)
        self.assertEqual(notification.notification_type, MatchNotification.Type.MATCH_CREATED)
        self.assertEqual(notification.title, 'Nueva invitación')
        self.assertTrue(notification.action_url.endswith(reverse('match_detail', kwargs={'pk': match.id})))
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)

    def test_proposer_autoaccept_does_not_create_redundant_accepted_notification(self):
        match = self._build_match()
        proposal = MatchResultProposal.objects.create(match=match, proposed_by=self.creator, winner=self.creator)

        MatchResultAcceptance.objects.create(
            proposal=proposal,
            user=self.creator,
            decision=MatchResultAcceptance.Decision.ACCEPTED,
        )

        accepted_notifications = MatchNotification.objects.filter(notification_type=MatchNotification.Type.RESULT_ACCEPTED)
        self.assertEqual(accepted_notifications.count(), 0)

    def test_mark_one_notification_as_read(self):
        match = self._build_match()
        notification = MatchNotification.objects.create(
            recipient=self.invited,
            actor=self.creator,
            match=match,
            notification_type=MatchNotification.Type.RESULT_PROPOSED,
            title='Resultado propuesto',
            message='Mensaje de prueba',
            action_url=reverse('match_detail', kwargs={'pk': match.id}),
        )

        self.client.force_login(self.invited)
        response = self.client.post(reverse('mark_notification_read', kwargs={'pk': notification.id}))

        self.assertEqual(response.status_code, 302)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_mark_all_notifications_requires_post(self):
        match = self._build_match()
        MatchNotification.objects.create(
            recipient=self.invited,
            actor=self.creator,
            match=match,
            notification_type=MatchNotification.Type.RESULT_PROPOSED,
            title='Resultado propuesto',
            message='Mensaje de prueba',
            action_url=reverse('match_detail', kwargs={'pk': match.id}),
        )

        self.client.force_login(self.invited)

        get_response = self.client.get(reverse('mark_notifications_read'))
        self.assertEqual(get_response.status_code, 405)

        post_response = self.client.post(reverse('mark_notifications_read'))
        self.assertEqual(post_response.status_code, 302)
        self.assertEqual(MatchNotification.objects.filter(recipient=self.invited, is_read=False).count(), 0)

    def test_open_notification_marks_as_read_and_redirects(self):
        match = self._build_match()
        notification = MatchNotification.objects.create(
            recipient=self.invited,
            actor=self.creator,
            match=match,
            notification_type=MatchNotification.Type.RESULT_PROPOSED,
            title='Resultado propuesto',
            message='Mensaje de prueba',
            action_url=reverse('match_detail', kwargs={'pk': match.id}),
        )

        self.client.force_login(self.invited)
        response = self.client.get(reverse('open_notification', kwargs={'pk': notification.id}))

        self.assertRedirects(response, reverse('match_detail', kwargs={'pk': match.id}))
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_notifications_feed_supports_incremental_updates(self):
        match = self._build_match()
        first = MatchNotification.objects.create(
            recipient=self.invited,
            actor=self.creator,
            match=match,
            notification_type=MatchNotification.Type.RESULT_PROPOSED,
            title='N1',
            message='Primera',
            action_url=reverse('match_detail', kwargs={'pk': match.id}),
        )
        second = MatchNotification.objects.create(
            recipient=self.invited,
            actor=self.creator,
            match=match,
            notification_type=MatchNotification.Type.RESULT_REJECTED,
            title='N2',
            message='Segunda',
            action_url=reverse('match_detail', kwargs={'pk': match.id}),
        )

        self.client.force_login(self.invited)
        response = self.client.get(reverse('notifications_feed'), {'since_id': first.id})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['last_id'], second.id)
        self.assertEqual(len(payload['new_notifications']), 1)
        self.assertEqual(payload['new_notifications'][0]['id'], second.id)
