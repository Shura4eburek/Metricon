import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone


def generate_api_key():
    return secrets.token_hex(32)


class Bot(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True)
    api_key = models.CharField(max_length=64, unique=True, default=generate_api_key)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def is_online(self):
        if self.last_seen_at is None:
            return False
        return timezone.now() - self.last_seen_at < timedelta(seconds=90)

    def regenerate_api_key(self):
        self.api_key = generate_api_key()
        self.save(update_fields=['api_key'])


class Heartbeat(models.Model):
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name='heartbeats')
    recorded_at = models.DateTimeField(auto_now_add=True)
    uptime_seconds = models.PositiveIntegerField()
    cpu_percent = models.FloatField()
    memory_mb = models.FloatField()
    active_connections = models.PositiveIntegerField()

    class Meta:
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['bot', '-recorded_at']),
        ]

    def __str__(self):
        return f"{self.bot.name} @ {self.recorded_at}"
