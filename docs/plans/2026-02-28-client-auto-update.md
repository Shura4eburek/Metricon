# Client Auto-Update Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bots automatically receive and apply `metricon_client.py` updates via a dashboard button, with zero manual intervention.

**Architecture:** The heartbeat response carries an `update` flag when the bot's client version is behind the server's latest. The client downloads the new file from a dedicated endpoint, replaces itself on disk, and restarts in-place with `os.execv`. A "Push Update" button on the dashboard bumps the server's latest version.

**Tech Stack:** Django, DRF, `os.execv`, `pathlib`, `threading`

---

### Task 1: Add VERSION to metricon_client.py

**Files:**
- Modify: `metricon_client.py` (top of file, after imports)

**Step 1: Add VERSION constant and import os/sys/pathlib**

Add after the existing imports at the top of `metricon_client.py`:

```python
VERSION = "1.1.0"
```

`os`, `sys`, `pathlib` are stdlib — no new deps needed. They're used later in Task 5.

**Step 2: Send version in heartbeat payload**

In `_send_heartbeat`, add `"client_version": VERSION` to the payload dict:

```python
payload = {
    "uptime_seconds": uptime,
    "cpu_percent": round(cpu, 2),
    "memory_mb": round(memory_mb, 2),
    "active_connections": connections,
    "client_version": VERSION,
}
```

**Step 3: Commit**

```bash
git add metricon_client.py
git commit -m "feat: add VERSION and send client_version in heartbeat"
```

---

### Task 2: Add ClientVersion model

**Files:**
- Modify: `apps/bots/models.py`
- Create: migration via `python manage.py makemigrations`

**Step 1: Add ClientVersion model to apps/bots/models.py**

Append at the bottom of the file:

```python
class ClientVersion(models.Model):
    """Singleton: stores the latest approved client version."""
    version = models.CharField(max_length=32)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Client Version"

    @classmethod
    def get_latest(cls) -> str:
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"version": VERSION_DEFAULT})
        return obj.version

    @classmethod
    def set_latest(cls, version: str) -> None:
        cls.objects.update_or_create(pk=1, defaults={"version": version})
```

Add this constant at the top of `models.py` (after imports):

```python
VERSION_DEFAULT = "1.0.0"
```

**Step 2: Create migration**

```bash
source .venv/Scripts/activate
python manage.py makemigrations bots --name client_version
```

Expected output: `Migrations for 'bots': apps/bots/migrations/0002_clientversion.py`

**Step 3: Apply locally to verify**

```bash
python manage.py migrate
```

**Step 4: Commit**

```bash
git add apps/bots/models.py apps/bots/migrations/
git commit -m "feat: add ClientVersion singleton model"
```

---

### Task 3: Update HeartbeatView to return update flag

**Files:**
- Modify: `apps/bots/views.py`
- Modify: `apps/bots/serializers.py`

**Step 1: Make client_version optional in HeartbeatSerializer**

In `apps/bots/serializers.py`, add `client_version` as a write-only field:

```python
class HeartbeatSerializer(serializers.ModelSerializer):
    client_version = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Heartbeat
        fields = ['uptime_seconds', 'cpu_percent', 'memory_mb', 'active_connections', 'client_version']
```

**Step 2: Update HeartbeatView to check version and respond**

Replace the `post` method in `HeartbeatView` in `apps/bots/views.py`:

```python
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
        bot.save(update_fields=['last_seen_at'])

        latest = ClientVersion.get_latest()
        needs_update = bool(client_version and client_version != latest)
        return Response({'status': 'ok', 'update': needs_update}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

Add import at the top of `apps/bots/views.py`:

```python
from .models import Bot, Heartbeat, ClientVersion
```

**Step 3: Commit**

```bash
git add apps/bots/views.py apps/bots/serializers.py
git commit -m "feat: heartbeat response returns update flag when client is outdated"
```

---

### Task 4: Add /api/v1/client/latest/ endpoint

**Files:**
- Modify: `apps/bots/views.py`
- Modify: `apps/bots/urls.py`

**Step 1: Add ClientLatestView to apps/bots/views.py**

Add at the bottom of `apps/bots/views.py`:

```python
from pathlib import Path
from django.http import HttpResponse
from django.conf import settings


class ClientLatestView(APIView):
    """GET /api/v1/client/latest/ — serve current metricon_client.py."""

    def get(self, request):
        file_path = Path(settings.BASE_DIR) / "metricon_client.py"
        try:
            content = file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return Response({"detail": "Client file not found."}, status=404)
        return HttpResponse(content, content_type="text/plain; charset=utf-8")
```

**Step 2: Register URL in apps/bots/urls.py**

```python
from .views import BotRegisterView, HeartbeatView, ClientLatestView

urlpatterns = [
    path('register/', BotRegisterView.as_view(), name='bot-register'),
    path('heartbeat/', HeartbeatView.as_view(), name='bot-heartbeat'),
    path('client/latest/', ClientLatestView.as_view(), name='client-latest'),
]
```

**Step 3: Verify endpoint responds**

```bash
curl http://localhost:8000/api/v1/client/latest/ | head -5
```

Expected: first lines of `metricon_client.py`

**Step 4: Commit**

```bash
git add apps/bots/views.py apps/bots/urls.py
git commit -m "feat: serve latest metricon_client.py at /api/v1/client/latest/"
```

---

### Task 5: Add self-update logic to metricon_client.py

**Files:**
- Modify: `metricon_client.py`

**Step 1: Add _check_for_update call in _send_heartbeat**

In `_send_heartbeat`, replace:
```python
self._post("/api/v1/bots/heartbeat/", payload)
```
With:
```python
response_data = self._post_json("/api/v1/bots/heartbeat/", payload)
if response_data:
    self._check_for_update(response_data)
```

**Step 2: Add _post_json method (returns parsed JSON)**

Rename existing `_post` to `_post_json` and make it return parsed response:

```python
def _post_json(self, path: str, payload: Any) -> Optional[dict]:
    try:
        resp = _requests.post(
            self.server_url + path,
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        return resp.json() if resp.ok else None
    except Exception as exc:
        log.debug("Metricon POST %s failed: %s", path, exc)
        return None
```

Update all other calls that used `_post` to use `_post_json` (track_error, track_metric, _flush_batch).

**Step 3: Add _check_for_update and _perform_update methods**

```python
def _check_for_update(self, response_data: dict) -> None:
    if not response_data.get("update"):
        return
    log.info("metricon_client update available — downloading")
    threading.Thread(
        target=self._perform_update, name="metricon-update", daemon=True
    ).start()

def _perform_update(self) -> None:
    import os
    import sys
    from pathlib import Path

    try:
        resp = _requests.get(
            self.server_url + "/api/v1/client/latest/",
            timeout=15,
        )
        resp.raise_for_status()

        client_path = Path(__file__).resolve()
        tmp_path = client_path.with_suffix(".tmp")
        tmp_path.write_text(resp.text, encoding="utf-8")
        tmp_path.replace(client_path)

        log.info("metricon_client updated to latest — restarting process")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as exc:
        log.warning("metricon_client auto-update failed: %s", exc)
```

**Step 4: Commit**

```bash
git add metricon_client.py
git commit -m "feat: self-update via heartbeat response flag + os.execv restart"
```

---

### Task 6: Add Push Update button to dashboard

**Files:**
- Modify: `apps/bots/dashboard_views.py`
- Modify: `apps/dashboard/urls.py`
- Modify: `templates/bots/api_keys.html`

**Step 1: Add PushUpdateView to apps/bots/dashboard_views.py**

```python
@method_decorator(csrf_exempt, name='dispatch')
class PushUpdateView(View):
    """POST /dashboard/api-keys/push-update/ — mark latest client version."""

    def post(self, request):
        # Read VERSION from metricon_client.py on disk
        import re
        from pathlib import Path
        from apps.bots.models import ClientVersion

        client_file = Path(settings.BASE_DIR) / "metricon_client.py"
        try:
            content = client_file.read_text(encoding="utf-8")
            match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            version = match.group(1) if match else "unknown"
        except Exception:
            version = "unknown"

        ClientVersion.set_latest(version)
        return JsonResponse({"pushed": True, "version": version})
```

Add `from django.conf import settings` at top of `dashboard_views.py`.

**Step 2: Register URL in apps/dashboard/urls.py**

```python
from apps.bots.dashboard_views import (
    APIKeysView,
    BotDeleteView,
    BotRegenerateKeyView,
    BotRegisterFormView,
    BotToggleActiveView,
    PushUpdateView,
)

urlpatterns = [
    ...existing routes...
    path('api-keys/push-update/', PushUpdateView.as_view(), name='push-update'),
]
```

**Step 3: Add button + JS to templates/bots/api_keys.html**

Add button next to "Register New Bot" in the header div:

```html
<div class="d-flex justify-content-between align-items-center mb-4">
  <h4 class="mb-0 text-light"><i class="bi bi-key me-2 text-info"></i>Bot API Keys</h4>
  <div class="d-flex gap-2">
    <button class="btn btn-outline-success btn-sm" onclick="pushUpdate()" title="Push latest client to all bots">
      <i class="bi bi-cloud-upload me-1"></i>Push Update
    </button>
    <button class="btn btn-info btn-sm" data-bs-toggle="modal" data-bs-target="#registerModal">
      <i class="bi bi-plus-lg me-1"></i>Register New Bot
    </button>
  </div>
</div>
```

Add JS function in `{% block extra_js %}`:

```javascript
async function pushUpdate() {
  if (!confirm('Push latest client version to all bots? They will auto-update on next heartbeat.')) return;
  try {
    const res = await fetch('/dashboard/api-keys/push-update/', {method: 'POST'});
    if (res.ok) {
      const data = await res.json();
      alert(`Update pushed! Bots will receive version ${data.version} on next heartbeat.`);
    } else {
      alert('Failed to push update.');
    }
  } catch (e) { alert('Failed: ' + e.message); }
}
```

**Step 4: Commit**

```bash
git add apps/bots/dashboard_views.py apps/dashboard/urls.py templates/bots/api_keys.html
git commit -m "feat: add Push Update button to dashboard"
```

---

### Task 7: Deploy and verify

**Step 1: Push to Railway**

```bash
git push origin master
```

**Step 2: Verify heartbeat endpoint returns update flag**

```bash
# Register test bot
curl -s -X POST https://web-production-37313.up.railway.app/api/v1/bots/register/ \
  -H "Content-Type: application/json" \
  -d '{"name":"update-test","description":""}' | python3 -m json.tool

# Send heartbeat with old version — should return update: false (no version pushed yet)
curl -s -X POST https://web-production-37313.up.railway.app/api/v1/bots/heartbeat/ \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"uptime_seconds":1,"cpu_percent":0,"memory_mb":0,"active_connections":0,"client_version":"0.0.1"}'
```

Expected: `{"status": "ok", "update": false}` (before push), `{"status": "ok", "update": true}` (after push)

**Step 3: Test push update via dashboard**

Go to `/dashboard/api-keys/`, click "Push Update", confirm.
Then re-send heartbeat — should return `"update": true`.

**Step 4: Clean up test bot**

```bash
curl -s -X POST https://web-production-37313.up.railway.app/dashboard/api-keys/<id>/delete/
```
