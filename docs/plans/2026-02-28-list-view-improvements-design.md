# List View Improvements Design

**Date:** 2026-02-28

## Goal

Enhance the overview list view with CPU, Memory, and Uptime columns, better visual styling, and a more prominent Detail button pinned to the right edge.

## New Columns

- **CPU** — percentage from latest heartbeat, with inline mini progress bar. Color-coded: green < 50%, yellow 50–80%, red > 80%
- **RAM** — memory_mb from latest heartbeat, formatted as MB or GB
- **Uptime** — uptime_seconds from latest heartbeat, formatted as `2д 4ч` / `45м` / `< 1м` via JS

## Visual Improvements

- Detail button styled as `btn-sm btn-primary` with left border separator — visually distinct from data columns
- Numeric columns use monospace font, right-aligned
- Row padding `py-2` for better readability
- CPU color: `text-success` < 50%, `text-warning` 50–80%, `text-danger` > 80%
- Memory formatted: < 1024 MB → "X MB", ≥ 1024 → "X.X GB"
- Uptime formatted in JS: seconds → `Xд Xч` / `Xч Xм` / `Xм` / `< 1м`

## Column Order

```
● | Name | Version | CPU (bar + %) | RAM | Uptime | req/hr | avg ms | errors | Last seen ║ Detail
```

## Files to Change

- `apps/dashboard/views.py` — add `uptime_seconds` to each `bot_stats` entry from last heartbeat
- `templates/dashboard/overview.html` — rebuild `#bot-list` table with new columns, styles, and JS helpers
