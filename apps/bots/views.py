from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import APIKeyAuthentication
from .models import Bot, Heartbeat, ClientVersion
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
            data = serializer.validated_data
            client_version = data.pop('client_version', None)
            Heartbeat.objects.create(bot=bot, **data)
            bot.last_seen_at = timezone.now()
            update_fields = ['last_seen_at']
            if client_version:
                bot.client_version = client_version
                update_fields.append('client_version')
            bot.save(update_fields=update_fields)

            latest = ClientVersion.get_latest()
            needs_update = bool(client_version and client_version != latest)
            return Response({'status': 'ok', 'update': needs_update}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClientLatestView(APIView):
    """GET /api/v1/client/latest/ — serve current metricon_client.py."""

    def get(self, request):
        file_path = Path(settings.BASE_DIR) / "metricon_client.py"
        try:
            content = file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return HttpResponse("Client file not found.", status=404, content_type="text/plain; charset=utf-8")
        return HttpResponse(content, content_type="text/plain; charset=utf-8")
