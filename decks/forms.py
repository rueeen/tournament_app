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
        fields = ('name', 'cover_image_url', 'colors')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self._ensure_default_colors()
        self.fields['colors'].queryset = DeckColor.objects.order_by('name')
        self.fields['cover_image_url'].widget = forms.HiddenInput()

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            return name

        if self.user is not None:
            queryset = Deck.objects.filter(owner=self.user, name__iexact=name)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError('Ya tienes un mazo con ese nombre.')

        return name

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
