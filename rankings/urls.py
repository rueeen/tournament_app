from django.urls import path

from .views import ranking_dashboard

urlpatterns = [
    path('', ranking_dashboard, name='ranking_dashboard'),
]
