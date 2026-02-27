"""
Management command: purge_old_metrics

Deletes RequestLog, ErrorEvent, CustomMetric, and Heartbeat records older
than a configurable number of days (default: 30).

Usage:
    python manage.py purge_old_metrics               # purge > 30 days
    python manage.py purge_old_metrics --days 7      # purge > 7 days
    python manage.py purge_old_metrics --dry-run     # preview only

Scheduling (cron / Windows Task Scheduler):
    # Daily at 02:00
    0 2 * * * /path/to/.venv/bin/python /path/to/manage.py purge_old_metrics

    # Windows Task Scheduler action:
    Program: C:\\path\\to\\.venv\\Scripts\\python.exe
    Arguments: C:\\path\\to\\manage.py purge_old_metrics
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.bots.models import Heartbeat
from apps.metrics.models import CustomMetric, ErrorEvent, RequestLog


class Command(BaseCommand):
    help = "Delete metrics older than N days (default 30). Use --dry-run to preview."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Delete records older than this many days (default: 30).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Print counts without deleting anything.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(days=days)

        models_fields = [
            (RequestLog,   "recorded_at"),
            (ErrorEvent,   "recorded_at"),
            (CustomMetric, "recorded_at"),
            (Heartbeat,    "recorded_at"),
        ]

        total = 0
        for model, field in models_fields:
            qs = model.objects.filter(**{f"{field}__lt": cutoff})
            count = qs.count()
            total += count
            label = model.__name__

            if dry_run:
                self.stdout.write(f"  [dry-run] {label}: {count} rows would be deleted")
            else:
                deleted, _ = qs.delete()
                self.stdout.write(
                    self.style.SUCCESS(f"  Deleted {deleted} {label} rows")
                )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n[dry-run] Total: {total} rows older than {days} days "
                    f"(cutoff: {cutoff:%Y-%m-%d %H:%M UTC})"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nPurge complete. {total} rows removed "
                    f"(older than {days} days, cutoff: {cutoff:%Y-%m-%d %H:%M UTC})"
                )
            )
