from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import TemplateView

from .models import Bot


class APIKeysView(TemplateView):
    """GET /dashboard/api-keys/ — Bot management page."""
    template_name = 'bots/api_keys.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['bots'] = Bot.objects.all().order_by('name')
        return ctx


class BotRegenerateKeyView(View):
    """POST /dashboard/api-keys/<id>/regenerate/ — regenerate API key."""

    def post(self, request, bot_id):
        bot = get_object_or_404(Bot, pk=bot_id)
        bot.regenerate_api_key()
        return JsonResponse({'api_key': bot.api_key})


class BotToggleActiveView(View):
    """POST /dashboard/api-keys/<id>/toggle/ — activate/deactivate bot."""

    def post(self, request, bot_id):
        bot = get_object_or_404(Bot, pk=bot_id)
        bot.is_active = not bot.is_active
        bot.save(update_fields=['is_active'])
        return JsonResponse({'is_active': bot.is_active})
