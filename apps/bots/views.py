from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import APIKeyAuthentication
from .models import Bot, Heartbeat
from .serializers import BotRegisterSerializer, HeartbeatSerializer


class BotRegisterView(APIView):
    """POST /api/v1/bots/register/ — no auth required."""

    def post(self, request):
        serializer = BotRegisterSerializer(data=request.data)
        if serializer.is_valid():
            bot = serializer.save()
            return Response(
                BotRegisterSerializer(bot).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HeartbeatView(APIView):
    """POST /api/v1/bots/heartbeat/ — requires X-API-Key."""
    authentication_classes = [APIKeyAuthentication]

    def post(self, request):
        if not request.user or not isinstance(request.user, Bot):
            return Response({'detail': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)

        bot = request.user
        serializer = HeartbeatSerializer(data=request.data)
        if serializer.is_valid():
            Heartbeat.objects.create(bot=bot, **serializer.validated_data)
            bot.last_seen_at = timezone.now()
            bot.save(update_fields=['last_seen_at'])
            return Response({'status': 'ok'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
