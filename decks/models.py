from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models


class DeckColor(models.Model):
    class ColorChoices(models.TextChoices):
        GREEN = 'green', 'Verde'
        BLACK = 'black', 'Negro'
        WHITE = 'white', 'Blanco'
        BLUE = 'blue', 'Azul'
        RED = 'red', 'Rojo'

    name = models.CharField(max_length=20, choices=ColorChoices.choices, unique=True)

    def __str__(self):
        return self.get_name_display()


class Deck(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='decks')
    name = models.CharField(max_length=120)
    cover_image = models.ImageField(upload_to='deck_covers/', blank=True, null=True)
    colors = models.ManyToManyField(DeckColor, related_name='decks')
    wins = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    losses = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    total_matches = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('owner', 'name')

    def __str__(self):
        return f'{self.name} ({self.owner.username})'

    @property
    def win_rate(self):
        if self.total_matches == 0:
            return 0
        return round((self.wins / self.total_matches) * 100, 2)
