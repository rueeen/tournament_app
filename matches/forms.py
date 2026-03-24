from django import forms
from django.contrib.auth.models import User
from django.db.models import Q

from decks.models import Deck

from .models import Match, MatchInvitation, MatchPlayer, MatchResultAcceptance, MatchResultProposal


class MatchCreateForm(forms.Form):
    participants = forms.ModelMultipleChoiceField(
        label='Participantes',
        queryset=User.objects.all(),
        required=True,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}),
        help_text='Selecciona entre 1 y 3 jugadores adicionales.',
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['participants'].queryset = (
                User.objects.filter(is_active=True)
                .exclude(pk=user.pk)
                .filter(Q(decks__isnull=False) | Q(is_superuser=True))
                .distinct()
                .order_by('username')
            )

    def clean_participants(self):
        participants = self.cleaned_data['participants']
        total = len(participants) + 1
        if total < 2 or total > 4:
            raise forms.ValidationError('La partida debe tener entre 2 y 4 jugadores en total.')
        return participants


class InvitationResponseForm(forms.ModelForm):
    deck = forms.ModelChoiceField(queryset=Deck.objects.none(), required=False)

    class Meta:
        model = MatchInvitation
        fields = ()

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['deck'].queryset = Deck.objects.filter(owner=user)


class MatchResultProposalForm(forms.ModelForm):
    class Meta:
        model = MatchResultProposal
        fields = ('winner', 'observations')
        widgets = {
            'observations': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, match=None, **kwargs):
        super().__init__(*args, **kwargs)
        if match:
            self.fields['winner'].queryset = User.objects.filter(matchplayer__match=match).distinct()


class ResultDecisionForm(forms.ModelForm):
    class Meta:
        model = MatchResultAcceptance
        fields = ('decision', 'reason')
        widgets = {
            'decision': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }


class MatchPlayerDeckForm(forms.ModelForm):
    class Meta:
        model = MatchPlayer
        fields = ('deck',)
