# Client Version Display & List/Grid Toggle Design

**Date:** 2026-02-28

## Goal

Show each bot's `metricon_client.py` version on the overview page with a warning badge when it's outdated. Add a grid/list toggle so users can switch between card tiles and a compact table view.

## Features

### 1. Client Version on Bot Cards

- Each bot tracks which version of `metricon_client.py` it's running
- Version is shown on each card/row
- If bot's version differs from the latest pushed version → yellow "Update needed" badge
- If bot has never sent a version → no badge, no version shown

### 2. Grid / List Toggle on Overview

- Two views: existing card grid + new compact table
- Toggle buttons in the overview header: `⊞ Grid` / `≡ List`
- Preference saved in `localStorage('metricon_view')` — persists across sessions
- Switching is instant (JS show/hide), no page reload

## Architecture

### Data Layer

**Store version on `Bot` model:**
- Add `client_version = CharField(max_length=32, blank=True, default="")`
- Update on each heartbeat: `bot.client_version = client_version; bot.save(update_fields=[..., 'client_version'])`
- Rationale: version is a property of the bot, not of a single heartbeat event

**Needs-update logic:**
- `OverviewView` fetches `ClientVersion.get_latest()` once
- Each `bot_stats` entry gets `needs_update = bool(bot.client_version and bot.client_version != latest_version)`

### View Layer

**`OverviewView`** (apps/dashboard/views.py):
- Add `latest_version = ClientVersion.get_latest()` to context
- Add `needs_update` flag per bot in `bot_stats`
- Add `client_version` to `bot_stats`

### Template Layer

**`templates/dashboard/overview.html`:**

Header row: add Grid/List toggle buttons next to online counter.

Card footer: add version + badge below "Last seen":
```
v1.1.0  ⚠ Update needed     Detail →
```

New list view (Bootstrap table, hidden by default):
| ● | Name | Version | req/hr | avg ms | errors | Last seen | |
|---|------|---------|--------|--------|--------|-----------|---|

JS at bottom: read localStorage on load, bind toggle buttons, show/hide `#bot-cards` and `#bot-list`.

## Decisions

| Decision | Choice | Reason |
|---|---|---|
| Where to store version | `Bot.client_version` field | Semantic fit; one query; clean access |
| Toggle implementation | Client-side JS + localStorage | Instant UX, no server round-trip |
| Outdated indicator | Yellow badge on card + table row | Immediately visible without detail page |

## Files to Change

- `apps/bots/models.py` — add `client_version` field to `Bot`
- `apps/bots/views.py` — save `client_version` in `HeartbeatView`
- `apps/dashboard/views.py` — add `latest_version` + `needs_update` to context
- `templates/dashboard/overview.html` — add toggle UI, version badges, list view table
- Migration: `apps/bots/migrations/` — new migration for `Bot.client_version`
