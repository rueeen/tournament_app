from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from decks.models import Deck

from .forms import MatchCreateForm, MatchResultProposalForm, ResultDecisionForm
from .models import Match, MatchInvitation, MatchNotification, MatchPlayer, MatchResultAcceptance, MatchResultProposal
from .notifications import notify_users


@login_required
def match_list(request):
    matches = Match.objects.filter(players__user=request.user).distinct().order_by('-created_at')
    created_matches = Match.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'matches/match_list.html', {'matches': matches, 'created_matches': created_matches})


@login_required
def invitation_list(request):
    invitations = MatchInvitation.objects.filter(invited_user=request.user, status=MatchInvitation.Status.PENDING).select_related('match', 'invited_by')
    return render(request, 'matches/invitations.html', {'invitations': invitations})


@login_required
@transaction.atomic
def match_create(request):
    if request.method == 'POST':
        form = MatchCreateForm(request.POST, user=request.user)
        if form.is_valid():
            participants = list(form.cleaned_data['participants'])
            creator_deck = Deck.objects.filter(owner=request.user).first()
            if not creator_deck:
                messages.error(request, 'Debes crear al menos un mazo para iniciar partidas.')
                return redirect('deck_create')

            match = Match.objects.create(created_by=request.user, status=Match.Status.PENDING)
            MatchPlayer.objects.create(match=match, user=request.user, deck=creator_deck)

            for invited in participants:
                MatchInvitation.objects.create(match=match, invited_user=invited, invited_by=request.user)

            notify_users(
                recipients=participants,
                actor=request.user,
                match=match,
                notification_type=MatchNotification.Type.MATCH_CREATED,
                message=f'{request.user.username} te invitó a la partida #{match.id}.',
            )
            messages.success(request, 'Partida creada. Se enviaron invitaciones.')
            return redirect('match_detail', pk=match.pk)
    else:
        form = MatchCreateForm(user=request.user)
    return render(request, 'matches/match_create.html', {'form': form})


@login_required
@transaction.atomic
def invitation_respond(request, pk, decision):
    invitation = get_object_or_404(MatchInvitation, pk=pk, invited_user=request.user)
    if invitation.status != MatchInvitation.Status.PENDING:
        messages.info(request, 'Esta invitación ya fue respondida.')
        return redirect('invitation_list')

    if decision == 'accept':
        deck_id = request.POST.get('deck_id')
        deck = get_object_or_404(Deck, pk=deck_id, owner=request.user)
        MatchPlayer.objects.create(match=invitation.match, user=request.user, deck=deck)
        invitation.status = MatchInvitation.Status.ACCEPTED
        invitation.save(update_fields=['status'])
        if invitation.match.players.count() >= 2:
            invitation.match.status = Match.Status.IN_PROGRESS
            invitation.match.save(update_fields=['status', 'updated_at'])
        notify_users(
            recipients=[invitation.invited_by],
            actor=request.user,
            match=invitation.match,
            notification_type=MatchNotification.Type.INVITATION_ACCEPTED,
            message=f'{request.user.username} aceptó la invitación de la partida #{invitation.match.id}.',
        )
        messages.success(request, 'Invitación aceptada.')
    else:
        invitation.status = MatchInvitation.Status.REJECTED
        invitation.save(update_fields=['status'])
        notify_users(
            recipients=[invitation.invited_by],
            actor=request.user,
            match=invitation.match,
            notification_type=MatchNotification.Type.INVITATION_REJECTED,
            message=f'{request.user.username} rechazó la invitación de la partida #{invitation.match.id}.',
        )
        messages.warning(request, 'Invitación rechazada.')
    return redirect('invitation_list')


@login_required
def match_detail(request, pk):
    match = get_object_or_404(Match.objects.prefetch_related('players__user', 'players__deck', 'invitations'), pk=pk)
    if not match.players.filter(user=request.user).exists() and match.created_by_id != request.user.id:
        messages.error(request, 'No tienes permiso para ver esta partida.')
        return redirect('match_list')

    active_proposal = match.result_proposals.filter(is_active=True).first()
    latest_proposal = match.result_proposals.first()
    my_acceptance = None
    if active_proposal:
        my_acceptance = active_proposal.acceptances.filter(user=request.user).first()

    return render(
        request,
        'matches/match_detail.html',
        {'match': match, 'active_proposal': active_proposal, 'latest_proposal': latest_proposal, 'my_acceptance': my_acceptance},
    )


@login_required
@transaction.atomic
def propose_result(request, pk):
    match = get_object_or_404(Match, pk=pk)
    if not match.players.filter(user=request.user).exists():
        messages.error(request, 'Solo participantes pueden proponer resultados.')
        return redirect('match_detail', pk=pk)
    if match.status == Match.Status.FINALIZED:
        messages.info(request, 'La partida ya está finalizada y no admite nuevos resultados.')
        return redirect('match_detail', pk=pk)

    if request.method == 'POST':
        form = MatchResultProposalForm(request.POST, match=match)
        if form.is_valid():
            match.result_proposals.filter(is_active=True).update(is_active=False)
            proposal = form.save(commit=False)
            proposal.match = match
            proposal.proposed_by = request.user
            proposal.is_active = True
            proposal.save()

            MatchResultAcceptance.objects.update_or_create(
                proposal=proposal,
                user=request.user,
                defaults={'decision': MatchResultAcceptance.Decision.ACCEPTED, 'reason': ''},
            )

            match.status = Match.Status.CLOSED_PENDING
            match.save(update_fields=['status', 'updated_at'])
            is_finalized = match.finalize_if_all_accepted()
            participants = [player.user for player in match.players.select_related('user')]
            notify_users(
                recipients=participants,
                actor=request.user,
                match=match,
                notification_type=MatchNotification.Type.RESULT_PROPOSED,
                message=f'{request.user.username} propuso un resultado en la partida #{match.id}.',
            )
            if is_finalized:
                notify_users(
                    recipients=participants,
                    actor=request.user,
                    match=match,
                    notification_type=MatchNotification.Type.MATCH_FINALIZED,
                    message=f'La partida #{match.id} quedó finalizada.',
                )
            messages.success(request, 'Resultado propuesto. Pendiente de confirmaciones.')
            return redirect('match_detail', pk=pk)
    else:
        form = MatchResultProposalForm(match=match)

    return render(request, 'matches/propose_result.html', {'form': form, 'match': match})


@login_required
@transaction.atomic
def decide_result(request, proposal_id):
    proposal = get_object_or_404(MatchResultProposal.objects.select_related('match'), pk=proposal_id, is_active=True)
    if not proposal.match.players.filter(user=request.user).exists():
        messages.error(request, 'No puedes votar este resultado.')
        return redirect('match_list')
    if proposal.match.status == Match.Status.FINALIZED:
        messages.info(request, 'La partida ya está finalizada. No se pueden registrar más decisiones.')
        return redirect('match_detail', pk=proposal.match.pk)

    if request.method == 'POST':
        form = ResultDecisionForm(request.POST)
        if form.is_valid():
            acceptance, created = MatchResultAcceptance.objects.get_or_create(
                proposal=proposal,
                user=request.user,
                defaults=form.cleaned_data,
            )
            if not created:
                messages.warning(request, 'Ya registraste una decisión para este resultado.')
                return redirect('match_detail', pk=proposal.match.pk)

            if acceptance.decision == MatchResultAcceptance.Decision.REJECTED:
                proposal.match.status = Match.Status.DISPUTED
                proposal.match.save(update_fields=['status', 'updated_at'])
                participants = [player.user for player in proposal.match.players.select_related('user')]
                notify_users(
                    recipients=participants,
                    actor=request.user,
                    match=proposal.match,
                    notification_type=MatchNotification.Type.RESULT_REJECTED,
                    message=f'{request.user.username} rechazó un resultado en la partida #{proposal.match.id}.',
                )
                messages.error(request, 'Resultado rechazado. La partida quedó en disputa.')
            else:
                proposal.match.status = Match.Status.CLOSED_PENDING
                proposal.match.save(update_fields=['status', 'updated_at'])
                participants = [player.user for player in proposal.match.players.select_related('user')]
                is_finalized = proposal.match.finalize_if_all_accepted()
                notify_users(
                    recipients=participants,
                    actor=request.user,
                    match=proposal.match,
                    notification_type=MatchNotification.Type.RESULT_ACCEPTED,
                    message=f'{request.user.username} aceptó el resultado de la partida #{proposal.match.id}.',
                )
                if is_finalized:
                    notify_users(
                        recipients=participants,
                        actor=request.user,
                        match=proposal.match,
                        notification_type=MatchNotification.Type.MATCH_FINALIZED,
                        message=f'La partida #{proposal.match.id} quedó finalizada.',
                    )
                messages.success(request, 'Resultado aceptado.')

            return redirect('match_detail', pk=proposal.match.pk)
    else:
        form = ResultDecisionForm()

    return render(request, 'matches/decide_result.html', {'form': form, 'proposal': proposal})


@login_required
@transaction.atomic
def mark_notifications_read(request):
    MatchNotification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or 'dashboard'
    return redirect(next_url)
