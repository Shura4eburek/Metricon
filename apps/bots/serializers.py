from rest_framework import serializers

from .models import Bot, Heartbeat


class BotRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bot
        fields = ['id', 'name', 'description', 'api_key', 'created_at']
        read_only_fields = ['id', 'api_key', 'created_at']


class HeartbeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Heartbeat
        fields = ['uptime_seconds', 'cpu_percent', 'memory_mb', 'active_connections']


class BotStatusSerializer(serializers.ModelSerializer):
    is_online = serializers.SerializerMethodField()

    class Meta:
        model = Bot
        fields = ['id', 'name', 'description', 'is_active', 'is_online', 'last_seen_at', 'created_at']

    def get_is_online(self, obj):
        return obj.is_online
