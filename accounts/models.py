from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    total_matches = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Perfil de {self.user.username}"

    @property
    def win_rate(self):
        if self.total_matches == 0:
            return 0
        return round((self.wins / self.total_matches) * 100, 2)


class ProfileComment(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile_comments_sent')
    target = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile_comments_received')
    message = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Comentario de {self.author.username} para {self.target.username}'
