from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from decks.models import Deck, DeckColor
from matches.models import Match, MatchInvitation, MatchPlayer


class Command(BaseCommand):
    help = 'Carga datos demo para pruebas locales.'

    @transaction.atomic
    def handle(self, *args, **options):
        colors = ['green', 'black', 'white', 'blue', 'red']
        color_objs = {}
        for c in colors:
            color_objs[c], _ = DeckColor.objects.get_or_create(name=c)

        users = []
        for username in ['alice', 'bob', 'carla', 'dario']:
            user, created = User.objects.get_or_create(username=username, defaults={'email': f'{username}@example.com'})
            if created:
                user.set_password('Pass1234!')
                user.save()
            users.append(user)

        for user, color in zip(users, colors):
            deck, _ = Deck.objects.get_or_create(owner=user, name=f'{user.username.title()} Aggro')
            deck.colors.set([color_objs[color]])

        match, _ = Match.objects.get_or_create(created_by=users[0], status=Match.Status.PENDING)
        MatchPlayer.objects.get_or_create(match=match, user=users[0], defaults={'deck': users[0].decks.first()})
        for user in users[1:3]:
            MatchInvitation.objects.get_or_create(match=match, invited_user=user, invited_by=users[0])

        self.stdout.write(self.style.SUCCESS('Datos demo cargados correctamente.'))
