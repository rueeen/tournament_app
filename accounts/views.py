from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from decks.models import Deck
from matches.models import Match

from .forms import ProfileCommentForm, ProfileForm, RegisterForm
from .models import ProfileComment


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cuenta creada. Inicia sesión para continuar.')
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)

    return render(
        request,
        'accounts/profile.html',
        {
            'form': form,
            'profile': profile,
            'decks_count': Deck.objects.filter(owner=request.user).count(),
            'matches_count': Match.objects.filter(players__user=request.user).distinct().count(),
            'users_count': User.objects.count(),
        },
    )


@login_required
def players_list_view(request):
    players = (
        User.objects.exclude(pk=request.user.pk)
        .select_related('profile')
        .annotate(decks_count=Count('decks', distinct=True))
        .order_by('username')
    )

    return render(
        request,
        'accounts/players_list.html',
        {
            'players': players,
        },
    )


@login_required
def player_profile_view(request, user_id):
    player = get_object_or_404(User.objects.select_related('profile'), pk=user_id)
    decks = Deck.objects.filter(owner=player).prefetch_related('colors')
    comments = ProfileComment.objects.filter(target=player).select_related('author', 'author__profile')

    if request.method == 'POST':
        comment_form = ProfileCommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.author = request.user
            new_comment.target = player
            new_comment.save()
            messages.success(request, 'Comentario publicado.')
            return redirect('player_profile', user_id=player.id)
    else:
        comment_form = ProfileCommentForm()

    return render(
        request,
        'accounts/player_profile.html',
        {
            'player': player,
            'decks': decks,
            'comments': comments,
            'comment_form': comment_form,
        },
    )
