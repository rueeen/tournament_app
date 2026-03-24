from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from decks.models import Deck
from matches.models import Match

from .forms import ProfileForm, RegisterForm


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
