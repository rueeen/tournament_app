from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DeckForm
from .models import Deck


@login_required
def deck_list(request):
    decks = Deck.objects.filter(owner=request.user).prefetch_related('colors')
    return render(request, 'decks/deck_list.html', {'decks': decks})


@login_required
def deck_create(request):
    if request.method == 'POST':
        form = DeckForm(request.POST, request.FILES)
        if form.is_valid():
            deck = form.save(commit=False)
            deck.owner = request.user
            deck.save()
            form.save_m2m()
            messages.success(request, 'Mazo creado correctamente.')
            return redirect('deck_list')
    else:
        form = DeckForm()
    return render(request, 'decks/deck_form.html', {'form': form, 'title': 'Crear mazo'})


@login_required
def deck_update(request, pk):
    deck = get_object_or_404(Deck, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = DeckForm(request.POST, request.FILES, instance=deck)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mazo actualizado correctamente.')
            return redirect('deck_list')
    else:
        form = DeckForm(instance=deck)
    return render(request, 'decks/deck_form.html', {'form': form, 'title': 'Editar mazo'})


@login_required
def deck_delete(request, pk):
    deck = get_object_or_404(Deck, pk=pk, owner=request.user)
    if request.method == 'POST':
        deck.delete()
        messages.success(request, 'Mazo eliminado correctamente.')
        return redirect('deck_list')
    return render(request, 'decks/deck_confirm_delete.html', {'deck': deck})
