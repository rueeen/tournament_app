from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse

from .models import Match, MatchInvitation, MatchNotification, MatchResultAcceptance, MatchResultProposal
from .notifications import notify_users


@receiver(pre_save, sender=MatchInvitation)
def cache_previous_invitation_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    instance._previous_status = sender.objects.filter(pk=instance.pk).values_list('status', flat=True).first()


@receiver(post_save, sender=MatchInvitation)
def notify_invitation_events(sender, instance, created, **kwargs):
    action_url = reverse('match_detail', kwargs={'pk': instance.match_id})
    if created:
        notify_users(
            recipients=[instance.invited_user],
            actor=instance.invited_by,
            match=instance.match,
            notification_type=MatchNotification.Type.MATCH_CREATED,
            title='Nueva invitación',
            message=f'{instance.invited_by.username} te invitó a la partida #{instance.match.id}.',
            action_url=action_url,
            action_label='Ver partida',
        )
        return

    previous_status = getattr(instance, '_previous_status', None)
    if previous_status == instance.status:
        return

    if instance.status == MatchInvitation.Status.ACCEPTED:
        notify_users(
            recipients=[instance.invited_by],
            actor=instance.invited_user,
            match=instance.match,
            notification_type=MatchNotification.Type.INVITATION_ACCEPTED,
            title='Invitación aceptada',
            message=f'{instance.invited_user.username} aceptó la invitación de la partida #{instance.match.id}.',
            action_url=action_url,
            action_label='Ver partida',
        )
    elif instance.status == MatchInvitation.Status.REJECTED:
        notify_users(
            recipients=[instance.invited_by],
            actor=instance.invited_user,
            match=instance.match,
            notification_type=MatchNotification.Type.INVITATION_REJECTED,
            title='Invitación rechazada',
            message=f'{instance.invited_user.username} rechazó la invitación de la partida #{instance.match.id}.',
            action_url=action_url,
            action_label='Ver partida',
        )


@receiver(post_save, sender=MatchResultProposal)
def notify_proposal_created(sender, instance, created, **kwargs):
    if not created:
        return

    participants = [player.user for player in instance.match.players.select_related('user')]
    notify_users(
        recipients=participants,
        actor=instance.proposed_by,
        match=instance.match,
        notification_type=MatchNotification.Type.RESULT_PROPOSED,
        title='Resultado propuesto',
        message=f'{instance.proposed_by.username} propuso un resultado en la partida #{instance.match.id}.',
        action_url=reverse('match_detail', kwargs={'pk': instance.match_id}),
        action_label='Revisar resultado',
    )


@receiver(post_save, sender=MatchResultAcceptance)
def notify_result_decision(sender, instance, created, **kwargs):
    if not created:
        return

    participants = [player.user for player in instance.proposal.match.players.select_related('user')]
    if instance.decision == MatchResultAcceptance.Decision.REJECTED:
        notify_users(
            recipients=participants,
            actor=instance.user,
            match=instance.proposal.match,
            notification_type=MatchNotification.Type.RESULT_REJECTED,
            title='Resultado rechazado',
            message=f'{instance.user.username} rechazó un resultado en la partida #{instance.proposal.match.id}.',
            action_url=reverse('match_detail', kwargs={'pk': instance.proposal.match_id}),
            action_label='Ver detalles',
        )
    elif instance.decision == MatchResultAcceptance.Decision.ACCEPTED:
        if instance.user_id == instance.proposal.proposed_by_id:
            return
        notify_users(
            recipients=participants,
            actor=instance.user,
            match=instance.proposal.match,
            notification_type=MatchNotification.Type.RESULT_ACCEPTED,
            title='Resultado aceptado',
            message=f'{instance.user.username} aceptó el resultado de la partida #{instance.proposal.match.id}.',
            action_url=reverse('match_detail', kwargs={'pk': instance.proposal.match_id}),
            action_label='Ver detalles',
        )


@receiver(pre_save, sender=Match)
def cache_previous_match_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    instance._previous_status = sender.objects.filter(pk=instance.pk).values_list('status', flat=True).first()


@receiver(post_save, sender=Match)
def notify_match_finalized(sender, instance, created, **kwargs):
    if created:
        return

    previous_status = getattr(instance, '_previous_status', None)
    if previous_status == instance.status:
        return

    if instance.status == Match.Status.FINALIZED:
        participants = [player.user for player in instance.players.select_related('user')]
        notify_users(
            recipients=participants,
            actor=instance.created_by,
            match=instance,
            notification_type=MatchNotification.Type.MATCH_FINALIZED,
            title='Partida finalizada',
            message=f'La partida #{instance.id} quedó finalizada.',
            action_url=reverse('match_detail', kwargs={'pk': instance.id}),
            action_label='Ver partida',
        )
