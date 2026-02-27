/**
 * Metricon — Bot Detail Charts
 * Depends on: Chart.js (loaded in base.html), BOT_ID and CUSTOM_KEYS globals
 */

const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 300 },
  plugins: {
    legend: { labels: { color: '#aaa', boxWidth: 12, font: { size: 11 } } },
    tooltip: { mode: 'index', intersect: false },
  },
  scales: {
    x: {
      ticks: { color: '#666', maxTicksLimit: 8, font: { size: 10 } },
      grid: { color: '#1e2535' },
    },
    y: {
      ticks: { color: '#666', font: { size: 10 } },
      grid: { color: '#1e2535' },
      beginAtZero: true,
    },
  },
};

let activeWindow = '1h';
const charts = {};

// ---- helpers ---------------------------------------------------------------

function fmtTime(isoStr) {
  const d = new Date(isoStr);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

async function fetchTimeseries(metric, window) {
  const url = `/api/v1/dashboard/bots/${BOT_ID}/timeseries/?metric=${metric}&window=${window}`;
  const res = await fetch(url);
  if (!res.ok) return [];
  const json = await res.json();
  return json.data || [];
}

async function fetchSummary() {
  const res = await fetch(`/api/v1/dashboard/bots/${BOT_ID}/summary/`);
  if (!res.ok) return null;
  return res.json();
}

function makeLineChart(canvasId, label, color, data) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  const labels = data.map(d => fmtTime(d.t));
  const values = data.map(d => d.v);
  return new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label,
        data: values,
        borderColor: color,
        backgroundColor: color + '22',
        borderWidth: 2,
        pointRadius: data.length > 60 ? 0 : 2,
        tension: 0.3,
        fill: true,
      }],
    },
    options: JSON.parse(JSON.stringify(CHART_DEFAULTS)),
  });
}

function updateLineChart(chart, data) {
  if (!chart) return;
  chart.data.labels = data.map(d => fmtTime(d.t));
  chart.data.datasets[0].data = data.map(d => d.v);
  chart.update('none');
}

// ---- init charts -----------------------------------------------------------

async function initCharts(window) {
  // Requests
  const reqData = await fetchTimeseries('requests', window);
  if (!charts.requests) {
    charts.requests = makeLineChart('chart-requests', 'Requests', '#17a2b8', reqData);
  } else {
    updateLineChart(charts.requests, reqData);
  }

  // Response time
  const rtData = await fetchTimeseries('response_time', window);
  if (!charts.responseTime) {
    charts.responseTime = makeLineChart('chart-response-time', 'Avg ms', '#ffc107', rtData);
  } else {
    updateLineChart(charts.responseTime, rtData);
  }

  // CPU + Memory dual-axis
  const cpuData = await fetchTimeseries('cpu', window);
  const memData = await fetchTimeseries('memory', window);
  if (!charts.resources) {
    const ctx = document.getElementById('chart-resources');
    if (ctx) {
      const opts = JSON.parse(JSON.stringify(CHART_DEFAULTS));
      opts.scales.y1 = {
        ...opts.scales.y,
        position: 'right',
        grid: { drawOnChartArea: false, color: '#1e2535' },
      };
      charts.resources = new Chart(ctx, {
        type: 'line',
        data: {
          labels: cpuData.map(d => fmtTime(d.t)),
          datasets: [
            {
              label: 'CPU %',
              data: cpuData.map(d => d.v),
              borderColor: '#e83e8c',
              backgroundColor: '#e83e8c22',
              borderWidth: 2,
              pointRadius: 0,
              tension: 0.3,
              fill: true,
              yAxisID: 'y',
            },
            {
              label: 'Memory MB',
              data: memData.map(d => d.v),
              borderColor: '#6f42c1',
              backgroundColor: '#6f42c122',
              borderWidth: 2,
              pointRadius: 0,
              tension: 0.3,
              fill: true,
              yAxisID: 'y1',
            },
          ],
        },
        options: opts,
      });
    }
  } else {
    charts.resources.data.labels = cpuData.map(d => fmtTime(d.t));
    charts.resources.data.datasets[0].data = cpuData.map(d => d.v);
    charts.resources.data.datasets[1].data = memData.map(d => d.v);
    charts.resources.update('none');
  }

  // Doughnut — top commands (always 24h)
  if (!charts.commands) {
    const summary = await fetchSummary();
    const ctx = document.getElementById('chart-commands');
    if (ctx && summary && summary.top_commands.length) {
      const COLORS = ['#17a2b8', '#ffc107', '#28a745', '#e83e8c', '#6f42c1'];
      charts.commands = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: summary.top_commands.map(c => c.command),
          datasets: [{
            data: summary.top_commands.map(c => c.count),
            backgroundColor: COLORS,
            borderWidth: 0,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'right',
              labels: { color: '#aaa', boxWidth: 10, font: { size: 10 } },
            },
          },
        },
      });
    }
  }

  // Custom metric sparklines
  for (const key of CUSTOM_KEYS) {
    const canvasId = 'sparkline-' + key.replace(/[^a-z0-9]/gi, '-').toLowerCase();
    const data = await fetchTimeseries('custom:' + key, window);
    if (!charts['custom_' + key]) {
      const ctx = document.getElementById(canvasId);
      if (ctx) {
        const opts = {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 200 },
          plugins: { legend: { display: false } },
          scales: {
            x: { display: false },
            y: { ticks: { color: '#666', font: { size: 9 }, maxTicksLimit: 3 }, grid: { color: '#1e2535' } },
          },
        };
        charts['custom_' + key] = new Chart(ctx, {
          type: 'line',
          data: {
            labels: data.map(d => fmtTime(d.t)),
            datasets: [{
              data: data.map(d => d.v),
              borderColor: '#20c997',
              backgroundColor: '#20c99722',
              borderWidth: 1.5,
              pointRadius: 0,
              tension: 0.4,
              fill: true,
            }],
          },
          options: opts,
        });
      }
    } else {
      const c = charts['custom_' + key];
      c.data.labels = data.map(d => fmtTime(d.t));
      c.data.datasets[0].data = data.map(d => d.v);
      c.update('none');
    }
  }
}

// ---- window selector -------------------------------------------------------

document.querySelectorAll('#window-btns button').forEach(btn => {
  btn.addEventListener('click', async () => {
    document.querySelectorAll('#window-btns button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeWindow = btn.dataset.window;
    await initCharts(activeWindow);
  });
});

// ---- polling ---------------------------------------------------------------

initCharts(activeWindow);
setInterval(() => initCharts(activeWindow), 30000);
