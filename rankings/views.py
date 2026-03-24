from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, F, FloatField, Q
from django.db.models.functions import Cast
from django.shortcuts import render

from decks.models import Deck
from matches.models import Match


@login_required
def ranking_dashboard(request):
    players_by_wins = User.objects.filter(profile__total_matches__gt=0).order_by('-profile__wins', '-profile__total_matches')[:10]
    players_by_rate = User.objects.filter(profile__total_matches__gt=0).annotate(
        win_rate=(Cast(F('profile__wins'), FloatField()) * 100.0) / Cast(F('profile__total_matches'), FloatField())
    ).order_by('-win_rate', '-profile__wins', '-profile__total_matches')[:10]

    decks_by_wins = Deck.objects.filter(total_matches__gt=0).order_by('-wins', '-total_matches')[:10]
    decks_by_rate = Deck.objects.filter(total_matches__gt=0).annotate(
        win_rate=(Cast(F('wins'), FloatField()) * 100.0) / Cast(F('total_matches'), FloatField())
    ).order_by('-win_rate', '-wins', '-total_matches')[:10]

    color_rankings = (
        Deck.objects.filter(total_matches__gt=0)
        .values('colors__name')
        .annotate(
            decks_count=Count('id', distinct=True),
            total_wins=Count('id', filter=Q(wins__gt=0)),
            total_matches=Count('id', filter=Q(total_matches__gt=0)),
        )
        .order_by('-total_wins', '-total_matches')
    )

    players_by_games = User.objects.order_by('-profile__total_matches', '-profile__wins')[:10]

    global_stats = {
        'total_players': User.objects.count(),
        'total_decks': Deck.objects.count(),
        'total_matches': Match.objects.count(),
        'finalized_matches': Match.objects.filter(status=Match.Status.FINALIZED).count(),
    }

    return render(
        request,
        'rankings/ranking_dashboard.html',
        {
            'players_by_wins': players_by_wins,
            'players_by_rate': players_by_rate,
            'decks_by_wins': decks_by_wins,
            'decks_by_rate': decks_by_rate,
            'color_rankings': color_rankings,
            'players_by_games': players_by_games,
            'global_stats': global_stats,
        },
    )
