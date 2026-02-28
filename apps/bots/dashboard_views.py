import re
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from .models import Bot, ClientVersion


class APIKeysView(TemplateView):
    """GET /dashboard/api-keys/ — Bot management page."""
    template_name = 'bots/api_keys.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['bots'] = Bot.objects.all().order_by('name')
        # Pass newly registered bot key from session flash
        ctx['new_bot_key'] = self.request.session.pop('new_bot_key', None)
        ctx['new_bot_name'] = self.request.session.pop('new_bot_name', None)
        ctx['reg_error'] = self.request.session.pop('reg_error', None)
        return ctx


class BotRegisterFormView(View):
    """POST /dashboard/api-keys/register/ — server-side bot registration."""

    def post(self, request):
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if not name:
            request.session['reg_error'] = 'Name is required.'
            return redirect('dashboard-api-keys')

        if Bot.objects.filter(name=name).exists():
            request.session['reg_error'] = f'A bot named "{name}" already exists.'
            return redirect('dashboard-api-keys')

        bot = Bot.objects.create(name=name, description=description)
        request.session['new_bot_key'] = bot.api_key
        request.session['new_bot_name'] = bot.name
        return redirect('dashboard-api-keys')


@method_decorator(csrf_exempt, name='dispatch')
class BotRegenerateKeyView(View):
    """POST /dashboard/api-keys/<id>/regenerate/ — regenerate API key."""

    def post(self, request, bot_id):
        bot = get_object_or_404(Bot, pk=bot_id)
        bot.regenerate_api_key()
        return JsonResponse({'api_key': bot.api_key})


@method_decorator(csrf_exempt, name='dispatch')
class BotToggleActiveView(View):
    """POST /dashboard/api-keys/<id>/toggle/ — activate/deactivate bot."""

    def post(self, request, bot_id):
        bot = get_object_or_404(Bot, pk=bot_id)
        bot.is_active = not bot.is_active
        bot.save(update_fields=['is_active'])
        return JsonResponse({'is_active': bot.is_active})


@method_decorator(csrf_exempt, name='dispatch')
class BotDeleteView(View):
    """POST /dashboard/api-keys/<id>/delete/ — permanently delete a bot."""

    def post(self, request, bot_id):
        bot = get_object_or_404(Bot, pk=bot_id)
        bot.delete()
        return JsonResponse({'deleted': True})


@method_decorator(csrf_exempt, name='dispatch')
class PushUpdateView(View):
    """POST /dashboard/api-keys/push-update/ — mark latest client version."""

    def post(self, request):
        client_file = Path(settings.BASE_DIR) / "metricon_client.py"
        try:
            content = client_file.read_text(encoding="utf-8")
            match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            version = match.group(1) if match else "unknown"
        except Exception:
            version = "unknown"

        ClientVersion.set_latest(version)
        return JsonResponse({"pushed": True, "version": version})
