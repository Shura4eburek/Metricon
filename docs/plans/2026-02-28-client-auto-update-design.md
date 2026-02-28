# Client Auto-Update Design

**Date:** 2026-02-28

## Problem

`metricon_client.py` is copied manually into each bot project. When the client
is updated, all running bots keep using the old version. Bots run non-stop on
Railway, so manual intervention per bot is impractical.

## Solution: Update flag via heartbeat response (Option A)

### How it works

1. `metricon_client.py` gets a `VERSION` constant (e.g. `"1.1.0"`).
2. The client sends its version in every heartbeat payload.
3. The server tracks the "latest approved version" in a `ClientVersion` DB model.
4. Heartbeat response includes `"update": true` when the bot's version is behind.
5. Client reacts: downloads new file from `/api/v1/client/latest/`, replaces
   itself on disk, then calls `os.execv` to restart the process in-place.
6. Dashboard has a "Push Update" button that bumps the latest approved version.

### Components

| Component | Change |
|-----------|--------|
| `metricon_client.py` | Add `VERSION`, send version in heartbeat, handle `update` flag |
| `apps/bots/models.py` | Add `ClientVersion` model (latest_version, updated_at) |
| `apps/bots/views.py` (HeartbeatView) | Read client version, return `update: true` if outdated |
| `apps/bots/urls.py` | Add `/api/v1/client/latest/` endpoint |
| `apps/bots/dashboard_views.py` | Add `PushUpdateView` |
| `apps/dashboard/urls.py` | Add `/dashboard/api-keys/push-update/` route |
| `templates/bots/api_keys.html` | Add "Push Update" button + JS |
| Migration | New migration for `ClientVersion` |

### Railway compatibility

`os.execv(sys.executable, [sys.executable] + sys.argv)` replaces the process
image in-place — same PID, transparent to Railway's process monitor.
The container filesystem is writable, so file replacement works fine.

### Safety

- Update is fire-and-forget: if download fails, the client logs and continues
  running the old version — no crash.
- `os.execv` only called after the new file is successfully written to disk.
- The server only serves the file that is committed to the repo (no arbitrary code injection).
