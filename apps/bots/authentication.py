from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import Bot


class APIKeyAuthentication(BaseAuthentication):
    """Authenticate via X-API-Key header."""

    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None  # No credentials provided; let other authenticators handle it

        try:
            bot = Bot.objects.get(api_key=api_key, is_active=True)
        except Bot.DoesNotExist:
            raise AuthenticationFailed('Invalid or inactive API key.')

        return (bot, api_key)

    def authenticate_header(self, request):
        return 'X-API-Key'
