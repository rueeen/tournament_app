from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from decks.models import Deck
from matches.models import Match, MatchInvitation


@login_required
def dashboard(request):
    user_model = request.user.__class__
    regular_users = user_model.objects.filter(is_superuser=False)
    invitations = MatchInvitation.objects.filter(invited_user=request.user, status=MatchInvitation.Status.PENDING).select_related('match')[:5]
    my_matches = Match.objects.filter(players__user=request.user).distinct().order_by('-created_at')[:5]
    my_decks = Deck.objects.filter(owner=request.user).order_by('-created_at')[:5]

    context = {
        'invitations': invitations,
        'my_matches': my_matches,
        'my_decks': my_decks,
        'global_stats': {
            'players': regular_users.count(),
            'decks': Deck.objects.count(),
            'matches': Match.objects.count(),
            'finalized': Match.objects.filter(status=Match.Status.FINALIZED).count(),
        },
        'active_players': regular_users.annotate(total=Count('matchplayer')).order_by('-total')[:5],
    }
    return render(request, 'core/dashboard.html', context)


@user_passes_test(lambda user: user.is_superuser)
def superuser_panel(request):
    players = User.objects.filter(is_superuser=False).annotate(total_matches=Count('matchplayer')).order_by('username')
    matches = Match.objects.select_related('created_by').order_by('-created_at')
    return render(request, 'core/superuser_panel.html', {'players': players, 'matches': matches})


@user_passes_test(lambda user: user.is_superuser)
def delete_player(request, user_id):
    if request.method != 'POST':
        return redirect('superuser_panel')

    player = get_object_or_404(User, pk=user_id, is_superuser=False)
    username = player.username
    player.delete()
    messages.success(request, f'Jugador {username} eliminado correctamente.')
    return redirect('superuser_panel')


@user_passes_test(lambda user: user.is_superuser)
def delete_match(request, match_id):
    if request.method != 'POST':
        return redirect('superuser_panel')

    match = get_object_or_404(Match, pk=match_id)
    match_label = f'#{match.id}'
    match.delete()
    messages.success(request, f'Partida {match_label} eliminada correctamente.')
    return redirect('superuser_panel')


def custom_404(request, exception):
    return render(request, '404.html', status=404)


def custom_500(request):
    return render(request, '500.html', status=500)
