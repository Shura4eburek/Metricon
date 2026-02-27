from django.contrib import admin

from .models import CustomMetric, ErrorEvent, RequestLog


@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = ['bot', 'command', 'response_time_ms', 'success', 'recorded_at']
    list_filter = ['bot', 'success']
    search_fields = ['command']


@admin.register(CustomMetric)
class CustomMetricAdmin(admin.ModelAdmin):
    list_display = ['bot', 'key', 'value', 'recorded_at']
    list_filter = ['bot', 'key']


@admin.register(ErrorEvent)
class ErrorEventAdmin(admin.ModelAdmin):
    list_display = ['bot', 'error_type', 'command', 'recorded_at']
    list_filter = ['bot', 'error_type']
