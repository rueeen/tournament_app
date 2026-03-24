from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

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
    if created:
        notify_users(
            recipients=[instance.invited_user],
            actor=instance.invited_by,
            match=instance.match,
            notification_type=MatchNotification.Type.MATCH_CREATED,
            message=f'{instance.invited_by.username} te invitó a la partida #{instance.match.id}.',
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
            message=f'{instance.invited_user.username} aceptó la invitación de la partida #{instance.match.id}.',
        )
    elif instance.status == MatchInvitation.Status.REJECTED:
        notify_users(
            recipients=[instance.invited_by],
            actor=instance.invited_user,
            match=instance.match,
            notification_type=MatchNotification.Type.INVITATION_REJECTED,
            message=f'{instance.invited_user.username} rechazó la invitación de la partida #{instance.match.id}.',
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
        message=f'{instance.proposed_by.username} propuso un resultado en la partida #{instance.match.id}.',
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
            message=f'{instance.user.username} rechazó un resultado en la partida #{instance.proposal.match.id}.',
        )
    elif instance.decision == MatchResultAcceptance.Decision.ACCEPTED:
        notify_users(
            recipients=participants,
            actor=instance.user,
            match=instance.proposal.match,
            notification_type=MatchNotification.Type.RESULT_ACCEPTED,
            message=f'{instance.user.username} aceptó el resultado de la partida #{instance.proposal.match.id}.',
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
            message=f'La partida #{instance.id} quedó finalizada.',
        )
