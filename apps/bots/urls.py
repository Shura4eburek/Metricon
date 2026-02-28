from django.urls import path

from .views import BotRegisterView, HeartbeatView, ClientLatestView

urlpatterns = [
    path('register/', BotRegisterView.as_view(), name='bot-register'),
    path('heartbeat/', HeartbeatView.as_view(), name='bot-heartbeat'),
    path('client/latest/', ClientLatestView.as_view(), name='client-latest'),
]
