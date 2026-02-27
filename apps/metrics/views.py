from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bots.authentication import APIKeyAuthentication
from apps.bots.models import Bot

from .models import CustomMetric, ErrorEvent, RequestLog
from .serializers import (
    CustomMetricSerializer,
    ErrorEventSerializer,
    RequestLogBatchSerializer,
)


class _BotAuthMixin:
    authentication_classes = [APIKeyAuthentication]

    def get_bot(self, request):
        if not request.user or not isinstance(request.user, Bot):
            return None
        return request.user


class RequestLogBatchView(_BotAuthMixin, APIView):
    """POST /api/v1/metrics/request/batch/"""

    def post(self, request):
        bot = self.get_bot(request)
        if bot is None:
            return Response({'detail': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = RequestLogBatchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        logs_data = serializer.validated_data['logs']
        objs = [
            RequestLog(
                bot=bot,
                command=entry['command'],
                user_id_hash=RequestLog.hash_user_id(entry['user_id']),
                response_time_ms=entry['response_time_ms'],
                success=entry['success'],
            )
            for entry in logs_data
        ]
        RequestLog.objects.bulk_create(objs)

        # Update last_seen_at
        bot.last_seen_at = timezone.now()
        bot.save(update_fields=['last_seen_at'])

        return Response({'created': len(objs)}, status=status.HTTP_201_CREATED)


class CustomMetricView(_BotAuthMixin, APIView):
    """POST /api/v1/metrics/custom/"""

    def post(self, request):
        bot = self.get_bot(request)
        if bot is None:
            return Response({'detail': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = CustomMetricSerializer(data=request.data)
        if serializer.is_valid():
            CustomMetric.objects.create(bot=bot, **serializer.validated_data)
            bot.last_seen_at = timezone.now()
            bot.save(update_fields=['last_seen_at'])
            return Response({'status': 'ok'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ErrorEventView(_BotAuthMixin, APIView):
    """POST /api/v1/metrics/error/"""

    def post(self, request):
        bot = self.get_bot(request)
        if bot is None:
            return Response({'detail': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = ErrorEventSerializer(data=request.data)
        if serializer.is_valid():
            ErrorEvent.objects.create(bot=bot, **serializer.validated_data)
            bot.last_seen_at = timezone.now()
            bot.save(update_fields=['last_seen_at'])
            return Response({'status': 'ok'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
