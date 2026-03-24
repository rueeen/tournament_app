from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from decks.models import Deck


class Match(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        IN_PROGRESS = 'in_progress', 'En curso'
        CLOSED_PENDING = 'closed_pending', 'Cerrada pendiente de confirmación'
        FINALIZED = 'finalized', 'Finalizada'
        CANCELED = 'canceled', 'Cancelada'
        DISPUTED = 'disputed', 'Disputada'

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_matches')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Partida #{self.id}'

    def clean(self):
        players_count = self.players.count() if self.pk else 0
        if self.pk and players_count and not 2 <= players_count <= 4:
            raise ValidationError('La partida debe tener entre 2 y 4 jugadores.')

    def finalize_if_all_accepted(self):
        proposal = self.result_proposals.filter(is_active=True).first()
        if not proposal:
            return False
        player_ids = set(self.players.values_list('user_id', flat=True))
        accepted_ids = set(
            proposal.acceptances.filter(decision=MatchResultAcceptance.Decision.ACCEPTED).values_list('user_id', flat=True)
        )
        if player_ids and player_ids.issubset(accepted_ids):
            with transaction.atomic():
                self.status = Match.Status.FINALIZED
                self.save(update_fields=['status', 'updated_at'])
                proposal.is_active = False
                proposal.save(update_fields=['is_active'])
                proposal.apply_stats()
            return True
        return False


class MatchPlayer(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='players')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matchplayer')
    deck = models.ForeignKey(Deck, on_delete=models.PROTECT, related_name='match_players')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('match', 'user')

    def __str__(self):
        return f'{self.user.username} en partida {self.match_id}'


class MatchInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        ACCEPTED = 'accepted', 'Aceptada'
        REJECTED = 'rejected', 'Rechazada'

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='invitations')
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='match_invitations')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('match', 'invited_user')


class MatchResultProposal(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='result_proposals')
    proposed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='proposed_results')
    winner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='won_result_proposals')
    closed_at = models.DateTimeField(default=timezone.now)
    observations = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        participant_ids = set(self.match.players.values_list('user_id', flat=True)) if self.match_id else set()
        if self.winner_id and participant_ids and self.winner_id not in participant_ids:
            raise ValidationError('El ganador debe ser participante de la partida.')

    @transaction.atomic
    def apply_stats(self):
        if getattr(self, '_stats_applied', False):
            return
        winner_player = self.match.players.select_related('user__profile', 'deck').get(user=self.winner)
        for match_player in self.match.players.select_related('user__profile', 'deck'):
            profile = match_player.user.profile
            deck = match_player.deck
            profile.total_matches += 1
            deck.total_matches += 1
            if match_player.id == winner_player.id:
                profile.wins += 1
                deck.wins += 1
            else:
                profile.losses += 1
                deck.losses += 1
            profile.save(update_fields=['wins', 'losses', 'total_matches'])
            deck.save(update_fields=['wins', 'losses', 'total_matches'])
        self._stats_applied = True


class MatchResultAcceptance(models.Model):
    class Decision(models.TextChoices):
        ACCEPTED = 'accepted', 'Aceptado'
        REJECTED = 'rejected', 'Rechazado'

    proposal = models.ForeignKey(MatchResultProposal, on_delete=models.CASCADE, related_name='acceptances')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='result_acceptances')
    decision = models.CharField(max_length=20, choices=Decision.choices)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('proposal', 'user')

    def __str__(self):
        return f'{self.user.username} - {self.decision}'


class MatchNotification(models.Model):
    class Type(models.TextChoices):
        MATCH_CREATED = 'match_created', 'Partida creada'
        INVITATION_ACCEPTED = 'invitation_accepted', 'Invitación aceptada'
        INVITATION_REJECTED = 'invitation_rejected', 'Invitación rechazada'
        RESULT_PROPOSED = 'result_proposed', 'Resultado propuesto'
        RESULT_ACCEPTED = 'result_accepted', 'Resultado aceptado'
        RESULT_REJECTED = 'result_rejected', 'Resultado rechazado'
        MATCH_FINALIZED = 'match_finalized', 'Partida finalizada'

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='match_notifications')
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='triggered_match_notifications')
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=32, choices=Type.choices)
    message = models.CharField(max_length=220)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Notificación para {self.recipient.username}: {self.message}'
