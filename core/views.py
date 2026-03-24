from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

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


def custom_404(request, exception):
    return render(request, '404.html', status=404)


def custom_500(request):
    return render(request, '500.html', status=500)
