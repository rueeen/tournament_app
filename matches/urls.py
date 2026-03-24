from django.urls import path

from .views import decide_result, invitation_list, invitation_respond, match_create, match_detail, match_list, propose_result

urlpatterns = [
    path('', match_list, name='match_list'),
    path('create/', match_create, name='match_create'),
    path('invitations/', invitation_list, name='invitation_list'),
    path('invitations/<int:pk>/<str:decision>/', invitation_respond, name='invitation_respond'),
    path('<int:pk>/', match_detail, name='match_detail'),
    path('<int:pk>/propose-result/', propose_result, name='propose_result'),
    path('proposal/<int:proposal_id>/decide/', decide_result, name='decide_result'),
]
