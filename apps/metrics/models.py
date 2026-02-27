import hashlib

from django.db import models

from apps.bots.models import Bot


class RequestLog(models.Model):
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name='request_logs')
    recorded_at = models.DateTimeField(auto_now_add=True)
    command = models.CharField(max_length=256)
    user_id_hash = models.CharField(max_length=64)  # SHA-256, never raw user ID
    response_time_ms = models.PositiveIntegerField()
    success = models.BooleanField()

    class Meta:
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['bot', '-recorded_at']),
            models.Index(fields=['bot', 'command']),
        ]

    @staticmethod
    def hash_user_id(user_id: str) -> str:
        return hashlib.sha256(user_id.encode()).hexdigest()

    def __str__(self):
        return f"{self.bot.name} {self.command} @ {self.recorded_at}"


class CustomMetric(models.Model):
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name='custom_metrics')
    recorded_at = models.DateTimeField(auto_now_add=True)
    key = models.CharField(max_length=128)
    value = models.FloatField()

    class Meta:
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['bot', 'key', '-recorded_at']),
        ]

    def __str__(self):
        return f"{self.bot.name} {self.key}={self.value} @ {self.recorded_at}"


class ErrorEvent(models.Model):
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name='error_events')
    recorded_at = models.DateTimeField(auto_now_add=True)
    error_type = models.CharField(max_length=256)
    message = models.TextField()
    traceback = models.TextField(blank=True)
    command = models.CharField(max_length=256, blank=True)

    class Meta:
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['bot', '-recorded_at']),
        ]

    def __str__(self):
        return f"{self.bot.name} {self.error_type} @ {self.recorded_at}"
