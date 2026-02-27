"""HTML dashboard URL patterns."""
from django.urls import path

from apps.bots.dashboard_views import (
    APIKeysView,
    BotRegenerateKeyView,
    BotToggleActiveView,
)

from .views import BotDetailView, OverviewView

urlpatterns = [
    path('', OverviewView.as_view(), name='dashboard-overview'),
    path('bots/<int:bot_id>/', BotDetailView.as_view(), name='dashboard-bot-detail'),
    path('api-keys/', APIKeysView.as_view(), name='dashboard-api-keys'),
    path('api-keys/<int:bot_id>/regenerate/', BotRegenerateKeyView.as_view(), name='bot-regenerate-key'),
    path('api-keys/<int:bot_id>/toggle/', BotToggleActiveView.as_view(), name='bot-toggle-active'),
]
