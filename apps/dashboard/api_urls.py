"""Dashboard JSON API URL patterns."""
from django.urls import path

from .api_views import BotListAPIView, BotSummaryAPIView, BotTimeseriesAPIView

urlpatterns = [
    path('bots/', BotListAPIView.as_view(), name='api-bot-list'),
    path('bots/<int:bot_id>/summary/', BotSummaryAPIView.as_view(), name='api-bot-summary'),
    path('bots/<int:bot_id>/timeseries/', BotTimeseriesAPIView.as_view(), name='api-bot-timeseries'),
]
