"""Metricon URL configuration."""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/bots/', include('apps.bots.urls')),
    path('api/v1/metrics/', include('apps.metrics.urls')),
    path('api/v1/dashboard/', include('apps.dashboard.api_urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
]
