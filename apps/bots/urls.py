from django.urls import path

from .views import BotRegisterView, HeartbeatView

urlpatterns = [
    path('register/', BotRegisterView.as_view(), name='bot-register'),
    path('heartbeat/', HeartbeatView.as_view(), name='bot-heartbeat'),
]
