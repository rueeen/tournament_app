from django.urls import path

from .views import player_profile_view, players_list_view, profile_view, register_view

urlpatterns = [
    path('register/', register_view, name='register'),
    path('profile/', profile_view, name='profile'),
    path('players/', players_list_view, name='players_list'),
    path('players/<int:user_id>/', player_profile_view, name='player_profile'),
]
