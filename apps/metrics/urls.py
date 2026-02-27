from django.urls import path

from .views import CustomMetricView, ErrorEventView, RequestLogBatchView

urlpatterns = [
    path('request/batch/', RequestLogBatchView.as_view(), name='metric-request-batch'),
    path('custom/', CustomMetricView.as_view(), name='metric-custom'),
    path('error/', ErrorEventView.as_view(), name='metric-error'),
]
