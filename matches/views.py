from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core.paginator import Paginator
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

from decks.models import Deck

from .forms import MatchCreateForm, MatchResultProposalForm, ResultDecisionForm
from .models import Match, MatchInvitation, MatchNotification, MatchPlayer, MatchResultAcceptance, MatchResultProposal
from .notifications import NotificationService


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
        messages.success(request, 'Invitación aceptada.')
    else:
        invitation.status = MatchInvitation.Status.REJECTED
        invitation.save(update_fields=['status'])
        messages.warning(request, 'Invitación rechazada.')
    return redirect('invitation_list')


@login_required
def match_detail(request, pk):
    match = get_object_or_404(Match.objects.prefetch_related('players__user', 'players__deck', 'invitations'), pk=pk)
    is_participant = match.players.filter(user=request.user).exists()
    has_invitation = match.invitations.filter(invited_user=request.user).exists()
    can_view_match = is_participant or has_invitation or match.created_by_id == request.user.id
    if not can_view_match:
        messages.error(request, 'No tienes permiso para ver esta partida.')
        return redirect('match_list')

    all_invitations_accepted = not match.invitations.exclude(status=MatchInvitation.Status.ACCEPTED).exists()
    can_propose_result = is_participant and match.status != Match.Status.FINALIZED and all_invitations_accepted
    active_proposal = match.result_proposals.filter(is_active=True).first()
    latest_proposal = match.result_proposals.first()
    my_acceptance = None
    if active_proposal:
        my_acceptance = active_proposal.acceptances.filter(user=request.user).first()

    return render(
        request,
        'matches/match_detail.html',
        {
            'match': match,
            'active_proposal': active_proposal,
            'latest_proposal': latest_proposal,
            'my_acceptance': my_acceptance,
            'can_propose_result': can_propose_result,
            'all_invitations_accepted': all_invitations_accepted,
        },
    )


@login_required
@transaction.atomic
def propose_result(request, pk):
    match = get_object_or_404(Match, pk=pk)
    if not match.players.filter(user=request.user).exists():
        messages.error(request, 'Solo participantes pueden proponer resultados.')
        return redirect('match_detail', pk=pk)
    if match.invitations.exclude(status=MatchInvitation.Status.ACCEPTED).exists():
        messages.error(request, 'No se puede proponer resultado hasta que todas las invitaciones estén aceptadas.')
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
            match.finalize_if_all_accepted()
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
                messages.error(request, 'Resultado rechazado. La partida quedó en disputa.')
            else:
                proposal.match.status = Match.Status.CLOSED_PENDING
                proposal.match.save(update_fields=['status', 'updated_at'])
                proposal.match.finalize_if_all_accepted()
                messages.success(request, 'Resultado aceptado.')

            return redirect('match_detail', pk=proposal.match.pk)
    else:
        form = ResultDecisionForm()

    return render(request, 'matches/decide_result.html', {'form': form, 'proposal': proposal})


@login_required
@transaction.atomic
def mark_notifications_read(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    NotificationService.mark_all_read_for_user(request.user)
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('dashboard')
    return redirect(next_url)


@login_required
def mark_notification_read(request, pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    notification = get_object_or_404(MatchNotification, pk=pk, recipient=request.user)
    NotificationService.mark_notification_read(notification)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'notification_id': notification.id})
    return redirect(request.POST.get('next') or reverse('notifications_center'))


@login_required
def open_notification(request, pk):
    notification = get_object_or_404(MatchNotification, pk=pk, recipient=request.user)
    NotificationService.mark_notification_read(notification)
    return redirect(notification.action_url or reverse('match_detail', kwargs={'pk': notification.match_id}))


@login_required
def notifications_center(request):
    notifications_qs = MatchNotification.objects.filter(recipient=request.user).select_related('actor', 'match')
    status_filter = request.GET.get('status', 'all')
    type_filter = request.GET.get('type', 'all')

    if status_filter == 'unread':
        notifications_qs = notifications_qs.filter(is_read=False)
    if type_filter != 'all':
        notifications_qs = notifications_qs.filter(notification_type=type_filter)

    notifications_qs = notifications_qs.order_by('-created_at')
    paginator = Paginator(notifications_qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'matches/notifications_center.html',
        {
            'page_obj': page_obj,
            'status_filter': status_filter,
            'type_filter': type_filter,
            'notification_types': MatchNotification.Type.choices,
        },
    )

@login_required
@never_cache
def notifications_feed(request):
    since_id = request.GET.get('since_id')
    base_qs = MatchNotification.objects.filter(recipient=request.user)
    latest = base_qs.select_related('match').order_by('-created_at')[:7]
    incremental_qs = base_qs
    if since_id and str(since_id).isdigit():
        incremental_qs = incremental_qs.filter(id__gt=int(since_id))
    else:
        incremental_qs = incremental_qs.none()

    def serialize(item):
        return {
            'id': item.id,
            'title': item.title,
            'message': item.message,
            'notification_type': item.notification_type,
            'action_url': item.action_url or reverse('match_detail', kwargs={'pk': item.match_id}),
            'open_url': reverse('open_notification', kwargs={'pk': item.id}),
            'action_label': item.action_label,
            'is_read': item.is_read,
            'created_at': item.created_at.strftime('%d/%m %H:%M'),
        }

    payload = [serialize(item) for item in latest]
    new_items = [serialize(item) for item in incremental_qs.order_by('id')[:20]]
    unread_count = MatchNotification.objects.filter(recipient=request.user, is_read=False).count()
    last_id = base_qs.order_by('-id').values_list('id', flat=True).first() or 0
    return JsonResponse({
        'notifications': payload,
        'new_notifications': new_items,
        'unread_count': unread_count,
        'last_id': last_id,
    })
