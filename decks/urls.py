from django.urls import path

from .views import deck_create, deck_delete, deck_list, deck_update

urlpatterns = [
    path('', deck_list, name='deck_list'),
    path('create/', deck_create, name='deck_create'),
    path('<int:pk>/edit/', deck_update, name='deck_update'),
    path('<int:pk>/delete/', deck_delete, name='deck_delete'),
]
