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
        fields = ('name', 'cover_image', 'cover_image_url', 'colors')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ensure_default_colors()
        self.fields['colors'].queryset = DeckColor.objects.order_by('name')
        self.fields['cover_image_url'].widget = forms.HiddenInput()

    def _ensure_default_colors(self):
        for color_value, _ in DeckColor.ColorChoices.choices:
            DeckColor.objects.get_or_create(name=color_value)

    def clean_colors(self):
        colors = self.cleaned_data['colors']
        if not colors:
            raise forms.ValidationError('Selecciona al menos un color para el mazo.')
        return colors

    def clean_cover_image_url(self):
        image_url = self.cleaned_data.get('cover_image_url', '').strip()
        return image_url
