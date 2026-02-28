"""
Dashboard HTML views + JSON API helpers.
"""
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView

from apps.bots.models import Bot, ClientVersion
from apps.metrics.models import ErrorEvent, RequestLog


class OverviewView(TemplateView):
    """GET /dashboard/ — overview of all bots."""
    template_name = 'dashboard/overview.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        one_hour_ago = now - timedelta(hours=1)
        latest_version = ClientVersion.get_latest()

        bots = Bot.objects.all()
        bot_stats = []
        for bot in bots:
            logs_1h = RequestLog.objects.filter(bot=bot, recorded_at__gte=one_hour_ago)
            agg = logs_1h.aggregate(
                total=Count('id'),
                avg_ms=Avg('response_time_ms'),
                errors=Count('id', filter=Q(success=False)),
            )
            errors_1h = ErrorEvent.objects.filter(bot=bot, recorded_at__gte=one_hour_ago).count()

            # Latest heartbeat for CPU
            last_hb = bot.heartbeats.first()

            bot_stats.append({
                'bot': bot,
                'req_per_hour': agg['total'] or 0,
                'avg_ms': round(agg['avg_ms'] or 0),
                'errors_1h': errors_1h,
                'cpu_percent': last_hb.cpu_percent if last_hb else None,
                'memory_mb': last_hb.memory_mb if last_hb else None,
                'uptime_seconds': last_hb.uptime_seconds if last_hb else None,
                'client_version': bot.client_version,
                'needs_update': bool(bot.client_version and bot.client_version != latest_version),
            })

        ctx['bot_stats'] = bot_stats
        ctx['online_count'] = sum(1 for s in bot_stats if s['bot'].is_online)
        ctx['total_count'] = len(bot_stats)
        return ctx


class BotDetailView(TemplateView):
    """GET /dashboard/bots/<id>/ — bot detail page."""
    template_name = 'dashboard/bot_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        bot = get_object_or_404(Bot, pk=kwargs['bot_id'])
        now = timezone.now()
        day_ago = now - timedelta(hours=24)

        logs_24h = RequestLog.objects.filter(bot=bot, recorded_at__gte=day_ago)
        agg = logs_24h.aggregate(
            total=Count('id'),
            avg_ms=Avg('response_time_ms'),
        )
        errors_24h = ErrorEvent.objects.filter(bot=bot, recorded_at__gte=day_ago).count()

        last_hb = bot.heartbeats.first()

        ctx['bot'] = bot
        ctx['req_24h'] = agg['total'] or 0
        ctx['avg_ms_24h'] = round(agg['avg_ms'] or 0)
        ctx['errors_24h'] = errors_24h
        ctx['last_hb'] = last_hb
        ctx['recent_errors'] = ErrorEvent.objects.filter(bot=bot).order_by('-recorded_at')[:20]
        ctx['custom_keys'] = list(
            bot.custom_metrics.values_list('key', flat=True).distinct().order_by('key')
        )
        return ctx
