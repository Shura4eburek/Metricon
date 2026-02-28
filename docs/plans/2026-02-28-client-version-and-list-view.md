# Client Version Display & List/Grid Toggle Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Show each bot's client version with an "Update needed" badge on the overview page, and add a grid/list toggle with localStorage persistence.

**Architecture:** Add `client_version` CharField to `Bot`, update it on heartbeat, compare with `ClientVersion.get_latest()` in OverviewView to set a `needs_update` flag. The overview template renders both grid and table views; JS toggles visibility and persists the choice in localStorage.

**Tech Stack:** Django, DRF, Bootstrap 5, vanilla JS, localStorage

---

### Task 1: Add `client_version` field to Bot model

**Files:**
- Modify: `apps/bots/models.py`
- Run: `python manage.py makemigrations bots --name bot_client_version`

**Step 1: Add field to Bot model**

In `apps/bots/models.py`, add one field to the `Bot` class after `is_active`:

```python
client_version = models.CharField(max_length=32, blank=True, default="")
```

Result — `Bot` class fields in order:
```python
class Bot(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True)
    api_key = models.CharField(max_length=64, unique=True, default=generate_api_key)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    client_version = models.CharField(max_length=32, blank=True, default="")
```

**Step 2: Create migration**

```bash
source .venv/Scripts/activate
python manage.py makemigrations bots --name bot_client_version
```

Expected output: `Migrations for 'bots': apps/bots/migrations/0003_bot_client_version.py`

**Step 3: Apply migration locally**

```bash
python manage.py migrate
```

Expected: `Applying bots.0003_bot_client_version... OK`

**Step 4: Commit**

```bash
git add apps/bots/models.py apps/bots/migrations/0003_bot_client_version.py
git commit -m "feat: add client_version field to Bot model"
```

---

### Task 2: Save client_version on heartbeat

**Files:**
- Modify: `apps/bots/views.py` (lines 29–49, the `HeartbeatView.post` method)

**Step 1: Update HeartbeatView.post to save client_version**

The current code in `apps/bots/views.py` already pops `client_version` from validated data but doesn't save it. Change the `bot.save(...)` call to also update `client_version`.

Replace this block (lines ~40–48):
```python
        data = serializer.validated_data
        client_version = data.pop('client_version', None)
        Heartbeat.objects.create(bot=bot, **data)
        bot.last_seen_at = timezone.now()
        bot.save(update_fields=['last_seen_at'])
```

With:
```python
        data = serializer.validated_data
        client_version = data.pop('client_version', None)
        Heartbeat.objects.create(bot=bot, **data)
        bot.last_seen_at = timezone.now()
        update_fields = ['last_seen_at']
        if client_version:
            bot.client_version = client_version
            update_fields.append('client_version')
        bot.save(update_fields=update_fields)
```

**Step 2: Manual smoke test**

```bash
# Register a test bot
curl -s -X POST http://localhost:8000/api/v1/bots/register/ \
  -H "Content-Type: application/json" \
  -d '{"name":"version-test","description":""}' | python3 -m json.tool
# Note the api_key

# Send heartbeat with client_version
curl -s -X POST http://localhost:8000/api/v1/bots/heartbeat/ \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"uptime_seconds":5,"cpu_percent":1.0,"memory_mb":30,"active_connections":0,"client_version":"1.1.0"}'
```

Expected: `{"status": "ok", "update": false}`

Then check Django shell:
```bash
python manage.py shell -c "from apps.bots.models import Bot; b = Bot.objects.get(name='version-test'); print(b.client_version)"
```

Expected: `1.1.0`

**Step 3: Commit**

```bash
git add apps/bots/views.py
git commit -m "feat: persist client_version on Bot from heartbeat"
```

---

### Task 3: Add needs_update flag to OverviewView

**Files:**
- Modify: `apps/dashboard/views.py`

**Step 1: Import ClientVersion**

In `apps/dashboard/views.py`, change the import on line 11:
```python
from apps.bots.models import Bot
```
To:
```python
from apps.bots.models import Bot, ClientVersion
```

**Step 2: Add latest_version lookup and needs_update to bot_stats**

In `OverviewView.get_context_data`, add `latest_version` lookup before the loop, and `needs_update` + `client_version` to each `bot_stats` entry.

Full updated method:
```python
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

        last_hb = bot.heartbeats.first()

        bot_stats.append({
            'bot': bot,
            'req_per_hour': agg['total'] or 0,
            'avg_ms': round(agg['avg_ms'] or 0),
            'errors_1h': errors_1h,
            'cpu_percent': last_hb.cpu_percent if last_hb else None,
            'memory_mb': last_hb.memory_mb if last_hb else None,
            'client_version': bot.client_version,
            'needs_update': bool(bot.client_version and bot.client_version != latest_version),
        })

    ctx['bot_stats'] = bot_stats
    ctx['online_count'] = sum(1 for s in bot_stats if s['bot'].is_online)
    ctx['total_count'] = len(bot_stats)
    return ctx
```

**Step 3: Commit**

```bash
git add apps/dashboard/views.py
git commit -m "feat: add needs_update and client_version to overview context"
```

---

### Task 4: Update overview template — version badge on cards + list view

**Files:**
- Modify: `templates/dashboard/overview.html`

This is the largest task. Replace the entire file content with the version below.

Key changes:
1. Header: add Grid/List toggle buttons
2. Card footer: add version + "Update needed" badge
3. After `#bot-cards` div: add `#bot-list` table (hidden by default)
4. JS block: toggle logic + localStorage persistence

**Full new content of `templates/dashboard/overview.html`:**

```html
{% extends "base.html" %}
{% block title %}Overview{% endblock %}
{% block nav_overview %}active{% endblock %}

{% block content %}
<div class="d-flex align-items-center justify-content-between mb-4">
  <h4 class="mb-0 text-light">
    <i class="bi bi-grid-1x2 me-2 text-info"></i>Bot Overview
  </h4>
  <div class="d-flex align-items-center gap-3">
    <span class="text-muted small">
      <span class="text-success fw-bold">{{ online_count }}</span> /
      <span class="text-light">{{ total_count }}</span> online
      &nbsp;·&nbsp;
      <span id="last-refresh" class="text-muted"></span>
    </span>
    {% if bot_stats %}
    <div class="btn-group btn-group-sm" role="group">
      <button id="btn-grid" type="button" class="btn btn-outline-secondary" onclick="setView('grid')" title="Grid view">
        <i class="bi bi-grid-3x2-gap"></i>
      </button>
      <button id="btn-list" type="button" class="btn btn-outline-secondary" onclick="setView('list')" title="List view">
        <i class="bi bi-list-ul"></i>
      </button>
    </div>
    {% endif %}
  </div>
</div>

{% if not bot_stats %}
  <div class="card text-center py-5">
    <div class="card-body">
      <i class="bi bi-robot display-4 text-muted"></i>
      <p class="mt-3 text-muted">No bots registered yet.</p>
      <a href="/dashboard/api-keys/" class="btn btn-outline-info btn-sm">Register a bot</a>
    </div>
  </div>
{% else %}

  {# ── Grid view ── #}
  <div class="row g-3" id="bot-cards">
    {% for s in bot_stats %}
    <div class="col-12 col-md-6 col-xl-4">
      <div class="card h-100">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start mb-2">
            <h5 class="card-title mb-0">
              <a href="/dashboard/bots/{{ s.bot.id }}/" class="text-decoration-none text-light">
                {{ s.bot.name }}
              </a>
            </h5>
            {% if s.bot.is_online %}
              <span class="badge badge-online">ONLINE</span>
            {% else %}
              <span class="badge badge-offline">OFFLINE</span>
            {% endif %}
          </div>

          {% if s.bot.description %}
            <p class="text-muted small mb-3">{{ s.bot.description }}</p>
          {% endif %}

          <div class="row text-center g-2 mb-3">
            <div class="col-4">
              <div class="rounded p-2" style="background:#1e2535">
                <div class="fw-bold text-info">{{ s.req_per_hour }}</div>
                <div class="text-muted" style="font-size:.7rem">req/hr</div>
              </div>
            </div>
            <div class="col-4">
              <div class="rounded p-2" style="background:#1e2535">
                <div class="fw-bold text-warning">{{ s.avg_ms }}ms</div>
                <div class="text-muted" style="font-size:.7rem">avg resp</div>
              </div>
            </div>
            <div class="col-4">
              <div class="rounded p-2" style="background:#1e2535">
                <div class="fw-bold {% if s.errors_1h > 0 %}text-danger{% else %}text-success{% endif %}">
                  {{ s.errors_1h }}
                </div>
                <div class="text-muted" style="font-size:.7rem">errors/hr</div>
              </div>
            </div>
          </div>

          {% if s.cpu_percent is not None %}
          <div class="mb-1 d-flex justify-content-between" style="font-size:.75rem">
            <span class="text-muted">CPU</span>
            <span>{{ s.cpu_percent|floatformat:1 }}%</span>
          </div>
          <div class="progress cpu-bar mb-2" style="height:6px">
            <div class="progress-bar bg-info" style="width:{{ s.cpu_percent }}%"></div>
          </div>
          {% endif %}
        </div>
        <div class="card-footer d-flex justify-content-between align-items-center"
             style="background:transparent; border-color:#2a2d3a; font-size:.75rem">
          <span class="text-muted">
            {% if s.bot.last_seen_at %}
              Last seen {{ s.bot.last_seen_at|timesince }} ago
            {% else %}
              Never seen
            {% endif %}
          </span>
          <div class="d-flex align-items-center gap-2">
            {% if s.client_version %}
              <span class="text-muted">v{{ s.client_version }}</span>
              {% if s.needs_update %}
                <span class="badge bg-warning text-dark" style="font-size:.65rem">Update needed</span>
              {% endif %}
            {% endif %}
            <a href="/dashboard/bots/{{ s.bot.id }}/" class="btn btn-outline-secondary btn-sm py-0">
              Detail <i class="bi bi-arrow-right"></i>
            </a>
          </div>
        </div>
      </div>
    </div>
    {% endfor %}
  </div>

  {# ── List view ── #}
  <div id="bot-list" style="display:none">
    <table class="table table-dark table-hover align-middle mb-0" style="font-size:.85rem">
      <thead style="color:#8b949e; font-size:.75rem; text-transform:uppercase; letter-spacing:.05em">
        <tr>
          <th style="width:1rem"></th>
          <th>Name</th>
          <th>Version</th>
          <th class="text-end">req/hr</th>
          <th class="text-end">avg ms</th>
          <th class="text-end">errors</th>
          <th>Last seen</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {% for s in bot_stats %}
        <tr>
          <td>
            {% if s.bot.is_online %}
              <span class="badge badge-online">●</span>
            {% else %}
              <span class="badge badge-offline">●</span>
            {% endif %}
          </td>
          <td>
            <a href="/dashboard/bots/{{ s.bot.id }}/" class="text-decoration-none text-light fw-semibold">
              {{ s.bot.name }}
            </a>
          </td>
          <td>
            {% if s.client_version %}
              <span class="text-muted">v{{ s.client_version }}</span>
              {% if s.needs_update %}
                <span class="badge bg-warning text-dark ms-1" style="font-size:.65rem">Update needed</span>
              {% endif %}
            {% else %}
              <span class="text-muted">—</span>
            {% endif %}
          </td>
          <td class="text-end text-info">{{ s.req_per_hour }}</td>
          <td class="text-end text-warning">{{ s.avg_ms }}ms</td>
          <td class="text-end {% if s.errors_1h > 0 %}text-danger{% else %}text-success{% endif %}">
            {{ s.errors_1h }}
          </td>
          <td class="text-muted">
            {% if s.bot.last_seen_at %}{{ s.bot.last_seen_at|timesince }} ago{% else %}Never{% endif %}
          </td>
          <td>
            <a href="/dashboard/bots/{{ s.bot.id }}/" class="btn btn-outline-secondary btn-sm py-0">
              Detail <i class="bi bi-arrow-right"></i>
            </a>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

{% endif %}
{% endblock %}

{% block extra_js %}
<script>
  function updateRefreshTime() {
    document.getElementById('last-refresh').textContent =
      'Refreshed at ' + new Date().toLocaleTimeString();
  }
  updateRefreshTime();
  setInterval(() => window.location.reload(), 30000);

  function setView(v) {
    const isGrid = v === 'grid';
    const cards = document.getElementById('bot-cards');
    const list  = document.getElementById('bot-list');
    const btnGrid = document.getElementById('btn-grid');
    const btnList = document.getElementById('btn-list');
    if (!cards || !list) return;

    cards.style.display = isGrid ? '' : 'none';
    list.style.display  = isGrid ? 'none' : '';

    btnGrid.classList.toggle('active', isGrid);
    btnList.classList.toggle('active', !isGrid);

    localStorage.setItem('metricon_view', v);
  }

  // Restore saved preference on load
  const savedView = localStorage.getItem('metricon_view') || 'grid';
  setView(savedView);
</script>
{% endblock %}
```

**Step 1: Replace the file**

Open `templates/dashboard/overview.html` and replace the entire content with the code above.

**Step 2: Visual check**

Start dev server:
```bash
source .venv/Scripts/activate
python manage.py runserver
```

Open http://localhost:8000/dashboard/ and verify:
- Grid/List toggle buttons appear in header (only when bots exist)
- Clicking List switches to table view; clicking Grid switches back
- After reload, the last chosen view is restored
- If a bot has `client_version` set, it shows `v1.1.0` in card footer and table row
- If `needs_update` is True, yellow "Update needed" badge appears

**Step 3: Commit**

```bash
git add templates/dashboard/overview.html
git commit -m "feat: add grid/list toggle and client version badges to overview"
```

---

### Task 5: Deploy and verify on Railway

**Step 1: Push to Railway**

```bash
git push origin master
```

**Step 2: Verify on production**

1. Go to https://web-production-37313.up.railway.app/dashboard/
2. If any bot has sent a heartbeat with `client_version`, confirm version appears on card
3. Test toggle: click List, reload — should stay in List view
4. Click "Push Update" on API Keys page, then check overview — bots running old version should show "Update needed" badge

**Step 3: Clean up test bot (if created in Task 2)**

```bash
curl -s -X POST https://web-production-37313.up.railway.app/dashboard/api-keys/<id>/delete/
```
