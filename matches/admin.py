from django.contrib import admin

from .models import Match, MatchInvitation, MatchPlayer, MatchResultAcceptance, MatchResultProposal

admin.site.register(Match)
admin.site.register(MatchPlayer)
admin.site.register(MatchInvitation)
admin.site.register(MatchResultProposal)
admin.site.register(MatchResultAcceptance)
