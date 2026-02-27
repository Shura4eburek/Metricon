"""
Dashboard JSON API views — no auth required (read-only aggregates).
"""
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bots.models import Bot, Heartbeat
from apps.bots.serializers import BotStatusSerializer
from apps.metrics.models import CustomMetric, ErrorEvent, RequestLog

# Window configuration: name → (hours, bucket_minutes)
WINDOWS = {
    '1h': (1, 5),
    '6h': (6, 15),
    '24h': (24, 60),
    '7d': (24 * 7, 360),
}


def _floor_to_bucket(dt, bucket_minutes):
    """Floor a datetime to the nearest bucket boundary."""
    total_minutes = dt.hour * 60 + dt.minute
    floored = (total_minutes // bucket_minutes) * bucket_minutes
    return dt.replace(hour=floored // 60, minute=floored % 60, second=0, microsecond=0)


class BotListAPIView(APIView):
    """GET /api/v1/dashboard/bots/ — list all bots with 1h stats."""

    def get(self, request):
        now = timezone.now()
        one_hour_ago = now - timedelta(hours=1)
        bots = Bot.objects.all()
        result = []
        for bot in bots:
            logs_1h = RequestLog.objects.filter(bot=bot, recorded_at__gte=one_hour_ago)
            agg = logs_1h.aggregate(
                total=Count('id'),
                avg_ms=Avg('response_time_ms'),
                errors=Count('id', filter=Q(success=False)),
            )
            last_hb = bot.heartbeats.order_by('-recorded_at').first()
            result.append({
                **BotStatusSerializer(bot).data,
                'req_1h': agg['total'] or 0,
                'avg_ms_1h': round(agg['avg_ms'] or 0),
                'errors_1h': agg['errors'] or 0,
                'cpu_percent': last_hb.cpu_percent if last_hb else None,
                'memory_mb': last_hb.memory_mb if last_hb else None,
            })
        return Response(result)


class BotSummaryAPIView(APIView):
    """GET /api/v1/dashboard/bots/{id}/summary/ — aggregated 24h stats."""

    def get(self, request, bot_id):
        try:
            bot = Bot.objects.get(pk=bot_id)
        except Bot.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)

        now = timezone.now()
        day_ago = now - timedelta(hours=24)

        logs = RequestLog.objects.filter(bot=bot, recorded_at__gte=day_ago)
        agg = logs.aggregate(
            total=Count('id'),
            avg_ms=Avg('response_time_ms'),
            errors=Count('id', filter=Q(success=False)),
        )
        errors_24h = ErrorEvent.objects.filter(bot=bot, recorded_at__gte=day_ago).count()
        last_hb = bot.heartbeats.order_by('-recorded_at').first()

        # Top 5 commands
        top_commands = (
            logs.values('command')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        return Response({
            'bot': BotStatusSerializer(bot).data,
            'req_24h': agg['total'] or 0,
            'avg_ms_24h': round(agg['avg_ms'] or 0),
            'request_errors_24h': agg['errors'] or 0,
            'errors_24h': errors_24h,
            'uptime_seconds': last_hb.uptime_seconds if last_hb else None,
            'cpu_percent': last_hb.cpu_percent if last_hb else None,
            'memory_mb': last_hb.memory_mb if last_hb else None,
            'active_connections': last_hb.active_connections if last_hb else None,
            'top_commands': list(top_commands),
        })


class BotTimeseriesAPIView(APIView):
    """
    GET /api/v1/dashboard/bots/{id}/timeseries/?metric=cpu&window=1h

    Supported metrics: cpu, memory, requests, response_time, errors, custom:<key>
    """

    def get(self, request, bot_id):
        try:
            bot = Bot.objects.get(pk=bot_id)
        except Bot.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)

        metric = request.query_params.get('metric', 'requests')
        window_key = request.query_params.get('window', '1h')

        if window_key not in WINDOWS:
            return Response({'detail': f"Invalid window. Choose from: {', '.join(WINDOWS)}"}, status=400)

        hours, bucket_minutes = WINDOWS[window_key]
        now = timezone.now()
        since = now - timedelta(hours=hours)

        data = self._build_series(bot, metric, since, bucket_minutes)
        return Response({'metric': metric, 'window': window_key, 'data': data})

    def _build_series(self, bot, metric, since, bucket_minutes):
        if metric in ('cpu', 'memory'):
            return self._heartbeat_series(bot, metric, since, bucket_minutes)
        elif metric == 'requests':
            return self._request_count_series(bot, since, bucket_minutes)
        elif metric == 'response_time':
            return self._response_time_series(bot, since, bucket_minutes)
        elif metric == 'errors':
            return self._error_series(bot, since, bucket_minutes)
        elif metric.startswith('custom:'):
            key = metric[7:]
            return self._custom_metric_series(bot, key, since, bucket_minutes)
        return []

    def _bucket_timestamps(self, since, bucket_minutes):
        """Generate bucket start times from since to now."""
        now = timezone.now()
        buckets = []
        current = _floor_to_bucket(since, bucket_minutes)
        while current <= now:
            buckets.append(current)
            current += timedelta(minutes=bucket_minutes)
        return buckets

    def _heartbeat_series(self, bot, metric, since, bucket_minutes):
        field = 'cpu_percent' if metric == 'cpu' else 'memory_mb'
        heartbeats = (
            bot.heartbeats
            .filter(recorded_at__gte=since)
            .order_by('recorded_at')
            .values('recorded_at', field)
        )
        # Bucket by averaging
        buckets = {}
        for hb in heartbeats:
            bucket = _floor_to_bucket(hb['recorded_at'], bucket_minutes)
            key = bucket.isoformat()
            buckets.setdefault(key, []).append(hb[field])

        return [
            {'t': k, 'v': round(sum(v) / len(v), 2)}
            for k, v in sorted(buckets.items())
        ]

    def _request_count_series(self, bot, since, bucket_minutes):
        logs = (
            RequestLog.objects
            .filter(bot=bot, recorded_at__gte=since)
            .order_by('recorded_at')
            .values('recorded_at')
        )
        buckets = {}
        for log in logs:
            bucket = _floor_to_bucket(log['recorded_at'], bucket_minutes)
            key = bucket.isoformat()
            buckets[key] = buckets.get(key, 0) + 1

        return [{'t': k, 'v': v} for k, v in sorted(buckets.items())]

    def _response_time_series(self, bot, since, bucket_minutes):
        logs = (
            RequestLog.objects
            .filter(bot=bot, recorded_at__gte=since)
            .order_by('recorded_at')
            .values('recorded_at', 'response_time_ms')
        )
        buckets = {}
        for log in logs:
            bucket = _floor_to_bucket(log['recorded_at'], bucket_minutes)
            key = bucket.isoformat()
            buckets.setdefault(key, []).append(log['response_time_ms'])

        return [
            {'t': k, 'v': round(sum(v) / len(v))}
            for k, v in sorted(buckets.items())
        ]

    def _error_series(self, bot, since, bucket_minutes):
        errors = (
            ErrorEvent.objects
            .filter(bot=bot, recorded_at__gte=since)
            .order_by('recorded_at')
            .values('recorded_at')
        )
        buckets = {}
        for err in errors:
            bucket = _floor_to_bucket(err['recorded_at'], bucket_minutes)
            key = bucket.isoformat()
            buckets[key] = buckets.get(key, 0) + 1

        return [{'t': k, 'v': v} for k, v in sorted(buckets.items())]

    def _custom_metric_series(self, bot, key, since, bucket_minutes):
        metrics = (
            CustomMetric.objects
            .filter(bot=bot, key=key, recorded_at__gte=since)
            .order_by('recorded_at')
            .values('recorded_at', 'value')
        )
        buckets = {}
        for m in metrics:
            bucket = _floor_to_bucket(m['recorded_at'], bucket_minutes)
            bkey = bucket.isoformat()
            buckets.setdefault(bkey, []).append(m['value'])

        return [
            {'t': k, 'v': round(sum(v) / len(v), 4)}
            for k, v in sorted(buckets.items())
        ]
