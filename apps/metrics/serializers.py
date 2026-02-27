from rest_framework import serializers

from .models import CustomMetric, ErrorEvent, RequestLog


class RequestLogSerializer(serializers.Serializer):
    command = serializers.CharField(max_length=256)
    user_id = serializers.CharField(max_length=256)  # raw; will be hashed before save
    response_time_ms = serializers.IntegerField(min_value=0)
    success = serializers.BooleanField()


class RequestLogBatchSerializer(serializers.Serializer):
    logs = RequestLogSerializer(many=True)

    def validate_logs(self, value):
        if not value:
            raise serializers.ValidationError("Batch must contain at least one log entry.")
        if len(value) > 500:
            raise serializers.ValidationError("Batch may not exceed 500 entries.")
        return value


class CustomMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomMetric
        fields = ['key', 'value']


class ErrorEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ErrorEvent
        fields = ['error_type', 'message', 'traceback', 'command']
