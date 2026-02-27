from django.contrib import admin

from .models import Bot, Heartbeat


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'is_online', 'last_seen_at', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']
    readonly_fields = ['api_key', 'created_at', 'last_seen_at']


@admin.register(Heartbeat)
class HeartbeatAdmin(admin.ModelAdmin):
    list_display = ['bot', 'recorded_at', 'cpu_percent', 'memory_mb', 'uptime_seconds']
    list_filter = ['bot']
