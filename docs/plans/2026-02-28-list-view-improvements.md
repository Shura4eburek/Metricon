# List View Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Add CPU (with mini progress bar + color coding), RAM, and Uptime columns to the overview list view, and make the Detail button visually prominent on the right edge.

**Architecture:** Two-file change — add `uptime_seconds` to `bot_stats` in the Django view, then rebuild the `#bot-list` table in the template with new columns and JS formatting helpers.

**Tech Stack:** Django template, Bootstrap 5, vanilla JS

---

### Task 1: Add uptime_seconds to OverviewView context

**Files:**
- Modify: `apps/dashboard/views.py` (lines 38–47, the `bot_stats.append({...})` dict)

**Step 1: Add uptime_seconds to bot_stats dict**

Current `bot_stats.append({...})` in `apps/dashboard/views.py`:
```python
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
```

Add one line after `'memory_mb'`:
```python
                'uptime_seconds': last_hb.uptime_seconds if last_hb else None,
```

Full updated dict:
```python
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
```

**Step 2: Commit**

```bash
cd C:/Users/Mamoru/PycharmProjects/Metricon && git add apps/dashboard/views.py && git commit -m "feat: add uptime_seconds to overview bot_stats context

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Rebuild #bot-list table in overview template

**Files:**
- Modify: `templates/dashboard/overview.html` (lines 108–165, the `#bot-list` div and its table)

**Step 1: Replace the entire `#bot-list` div**

Find and replace the entire `{# ── List view ── #}` section (from `<div id="bot-list"` to the closing `</div>`) with the new version below.

Also add the JS helper functions `fmtUptime` and `fmtRam` to the `<script>` block (after `setView` function, before the closing `</script>` tag).

**New `#bot-list` div content** (replaces lines 108–165):

```html
  {# ── List view ── #}
  <div id="bot-list" style="display:none">
    <table class="table table-dark table-hover align-middle mb-0" style="font-size:.82rem; border-collapse:separate; border-spacing:0">
      <thead>
        <tr style="color:#8b949e; font-size:.7rem; text-transform:uppercase; letter-spacing:.06em; border-bottom:1px solid #2a2d3a">
          <th class="ps-3" style="width:1.2rem"></th>
          <th>Name</th>
          <th>Version</th>
          <th style="width:9rem">CPU</th>
          <th class="text-end" style="width:5rem">RAM</th>
          <th class="text-end" style="width:5rem">Uptime</th>
          <th class="text-end" style="width:4.5rem">req/hr</th>
          <th class="text-end" style="width:4.5rem">avg ms</th>
          <th class="text-end" style="width:4rem">errors</th>
          <th style="width:6rem">Last seen</th>
          <th style="width:6rem; border-left:1px solid #2a2d3a"></th>
        </tr>
      </thead>
      <tbody>
        {% for s in bot_stats %}
        <tr style="border-bottom:1px solid #1e2230">
          <td class="ps-3">
            {% if s.bot.is_online %}
              <span style="color:#2ea043; font-size:.65rem">●</span>
            {% else %}
              <span style="color:#6e7681; font-size:.65rem">●</span>
            {% endif %}
          </td>
          <td class="py-2">
            <a href="/dashboard/bots/{{ s.bot.id }}/" class="text-decoration-none text-light fw-semibold">
              {{ s.bot.name }}
            </a>
            {% if s.bot.description %}
              <div class="text-muted" style="font-size:.7rem; line-height:1.2">{{ s.bot.description|truncatechars:40 }}</div>
            {% endif %}
          </td>
          <td class="py-2">
            {% if s.client_version %}
              <span class="text-muted" style="font-family:monospace">v{{ s.client_version }}</span>
              {% if s.needs_update %}
                <span class="badge bg-warning text-dark d-block mt-1" style="font-size:.6rem; width:fit-content">⚠ Update</span>
              {% endif %}
            {% else %}
              <span class="text-muted">—</span>
            {% endif %}
          </td>
          <td class="py-2">
            {% if s.cpu_percent is not None %}
              {% if s.cpu_percent >= 80 %}
                <div class="fw-semibold text-danger" style="font-family:monospace; font-size:.8rem">{{ s.cpu_percent|floatformat:1 }}%</div>
                <div class="progress mt-1" style="height:3px; background:#1e2230">
                  <div class="progress-bar bg-danger" style="width:{{ s.cpu_percent }}%"></div>
                </div>
              {% elif s.cpu_percent >= 50 %}
                <div class="fw-semibold text-warning" style="font-family:monospace; font-size:.8rem">{{ s.cpu_percent|floatformat:1 }}%</div>
                <div class="progress mt-1" style="height:3px; background:#1e2230">
                  <div class="progress-bar bg-warning" style="width:{{ s.cpu_percent }}%"></div>
                </div>
              {% else %}
                <div class="fw-semibold text-success" style="font-family:monospace; font-size:.8rem">{{ s.cpu_percent|floatformat:1 }}%</div>
                <div class="progress mt-1" style="height:3px; background:#1e2230">
                  <div class="progress-bar bg-success" style="width:{{ s.cpu_percent }}%"></div>
                </div>
              {% endif %}
            {% else %}
              <span class="text-muted">—</span>
            {% endif %}
          </td>
          <td class="text-end py-2" style="font-family:monospace; color:#8b949e">
            {% if s.memory_mb is not None %}
              {% if s.memory_mb >= 1024 %}
                {{ s.memory_mb|floatformat:0 }}
                <span style="font-size:.7rem; color:#6e7681"> MB</span>
              {% else %}
                {{ s.memory_mb|floatformat:0 }}<span style="font-size:.7rem; color:#6e7681"> MB</span>
              {% endif %}
            {% else %}—{% endif %}
          </td>
          <td class="text-end py-2" style="font-family:monospace; color:#8b949e">
            {% if s.uptime_seconds is not None %}
              <span class="uptime-fmt" data-seconds="{{ s.uptime_seconds }}">{{ s.uptime_seconds }}s</span>
            {% else %}—{% endif %}
          </td>
          <td class="text-end py-2 text-info" style="font-family:monospace">{{ s.req_per_hour }}</td>
          <td class="text-end py-2 text-warning" style="font-family:monospace">{{ s.avg_ms }}ms</td>
          <td class="text-end py-2 {% if s.errors_1h > 0 %}text-danger{% else %}text-success{% endif %}" style="font-family:monospace">
            {{ s.errors_1h }}
          </td>
          <td class="py-2 text-muted" style="font-size:.75rem">
            {% if s.bot.last_seen_at %}{{ s.bot.last_seen_at|timesince }} ago{% else %}Never{% endif %}
          </td>
          <td class="py-2 text-end" style="border-left:1px solid #2a2d3a">
            <a href="/dashboard/bots/{{ s.bot.id }}/" class="btn btn-sm btn-primary px-3">
              Detail <i class="bi bi-arrow-right"></i>
            </a>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
```

**Step 2: Add JS helper functions for uptime formatting**

In the `{% block extra_js %}` script block, add these two functions right after the closing `}` of `setView(v)` and before `// Restore saved preference on load`:

```javascript
  function fmtUptime(s) {
    if (s == null) return '—';
    const d = Math.floor(s / 86400);
    const h = Math.floor((s % 86400) / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (d > 0) return d + 'д ' + h + 'ч';
    if (h > 0) return h + 'ч ' + m + 'м';
    if (m > 0) return m + 'м';
    return '< 1м';
  }

  // Format all uptime cells on load
  document.querySelectorAll('.uptime-fmt').forEach(el => {
    el.textContent = fmtUptime(parseInt(el.dataset.seconds, 10));
  });
```

**Step 3: Verify visually**

Start dev server:
```bash
source .venv/Scripts/activate && python manage.py runserver
```

Open http://localhost:8000/dashboard/ and switch to List view. Verify:
- 11 columns visible: dot, name (with optional description subtitle), version, CPU (bar+color), RAM, Uptime, req/hr, avg ms, errors, last seen, Detail
- CPU < 50% → green, 50–80% → yellow, > 80% → red
- Uptime shows formatted string (e.g. `2д 4ч`, `45м`, `< 1м`)
- Detail button is blue `btn-primary` with left border separator, right-aligned
- Numbers use monospace font

**Step 4: Commit**

```bash
cd C:/Users/Mamoru/PycharmProjects/Metricon && git add templates/dashboard/overview.html && git commit -m "feat: improve list view with CPU/RAM/Uptime columns and styled Detail button

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Deploy and verify on Railway

**Step 1: Push**

```bash
cd C:/Users/Mamoru/PycharmProjects/Metricon && git push origin master
```

**Step 2: Smoke test on production**

Open https://web-production-37313.up.railway.app/dashboard/, switch to List view and verify all new columns appear with real data from SN-Print bot.
