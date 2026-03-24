from django import forms

from .models import Deck, DeckColor


class DeckForm(forms.ModelForm):
    colors = forms.ModelMultipleChoiceField(
        queryset=DeckColor.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )

    class Meta:
        model = Deck
        fields = ('name', 'cover_image', 'colors')

    def clean_colors(self):
        colors = self.cleaned_data['colors']
        if not colors:
            raise forms.ValidationError('Selecciona al menos un color para el mazo.')
        return colors
