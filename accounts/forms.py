from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile, ProfileComment


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('avatar',)


class ProfileCommentForm(forms.ModelForm):
    class Meta:
        model = ProfileComment
        fields = ('message',)
        widgets = {
            'message': forms.Textarea(
                attrs={
                    'rows': 3,
                    'placeholder': 'Escribe un comentario para este jugador...',
                    'class': 'form-control',
                }
            )
        }
