/* ─────────────────────────────────────────────────────
   FinSight — Frontend Application Logic
   Handles: upload, dashboard rendering, chat, anomalies
   ───────────────────────────────────────────────────── */

// ─── STATE ────────────────────────────────────────────────────────────────────
const state = {
  dataLoaded: false,
  summary: null,
  anomalies: null,
  chartData: null,
  charts: {},
};

// Chart.js palette — fintech dark
const PALETTE = [
  '#00ff88', '#f5c542', '#ff4d6d', '#4d9fff',
  '#c77dff', '#ff914d', '#00d4ff', '#9eff6b',
  '#ff6bce', '#ffd700',
];

// ─── VIEW SWITCHING ──────────────────────────────────────────────────────────

function switchView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

  const viewEl = document.getElementById(`view-${name}`);
  const navBtn = document.querySelector(`[data-view="${name}"]`);

  if (viewEl) viewEl.classList.add('active');
  if (navBtn) navBtn.classList.add('active');
}

// ─── UPLOAD HANDLERS ──────────────────────────────────────────────────────────

function handleDragOver(e) {
  e.preventDefault();
  const zone = document.getElementById('uploadZone');
  if (zone) zone.classList.add('drag-over');
}

function handleDragLeave() {
  const zone = document.getElementById('uploadZone');
  if (zone) zone.classList.remove('drag-over');
}

function handleDrop(e) {
  e.preventDefault();
  const zone = document.getElementById('uploadZone');
  if (zone) zone.classList.remove('drag-over');

  const files = e.dataTransfer.files;
  if (files.length > 0) processFile(files[0]);
}

function handleFileSelect(e) {
  if (e.target.files.length > 0) processFile(e.target.files[0]);
}

async function loadSampleData() {
  showLoading();
  try {
    const res = await fetch('/api/sample-csv');
    const blob = await res.blob();
    const file = new File([blob], 'sample_bank_statement.csv', { type: 'text/csv' });
    await uploadFile(file);
  } catch (err) {
    hideLoading();
    alert('Error loading sample data: ' + err.message);
  }
}

async function processFile(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['csv', 'pdf'].includes(ext)) {
    alert('Please upload a CSV or PDF file.');
    return;
  }
  showLoading();
  await uploadFile(file);
}

async function uploadFile(file) {
  const steps = document.querySelectorAll('.loading-step');
  let stepIdx = 0;

  const stepInterval = setInterval(() => {
    if (stepIdx < steps.length) {
      steps.forEach(s => s.classList.remove('active'));
      for (let i = 0; i < stepIdx; i++) steps[i].classList.add('done');
      steps[stepIdx].classList.add('active');
      stepIdx++;
    }
  }, 800);

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
      credentials: 'include',
    });
    const data = await res.json();

    clearInterval(stepInterval);

    if (!data.success) {
      hideLoading();
      alert('Upload failed: ' + data.error);
      return;
    }

    // Store state
    state.dataLoaded = true;
    state.summary = data.summary;
    state.anomalies = data.anomalies;
    state.chartData = data.chart_data;

    // Render all views
    renderDashboard(data);
    renderAnomalies(data.anomalies);

    if (data.initial_analysis) {
      showInitialAnalysis(data.initial_analysis);
    }

    updateHeaderStatus(data.summary);
    hideLoading();

    // Show nav only after successful dataset load
    showNav();

    showApp();

  } catch (err) {
    clearInterval(stepInterval);
    hideLoading();
    alert('Upload error: ' + err.message);
  }
}

// ─── DASHBOARD RENDERING ──────────────────────────────────────────────────────

function renderDashboard(data) {
  const { summary, chart_data, anomalies } = data;
  renderStats(summary);
  renderDonut(chart_data.categoryBreakdown);
  renderTrend(chart_data.monthlyTrend);
  renderMoM(chart_data.momChanges);
  renderAlerts(anomalies);

  const chartMonth = document.getElementById('chartMonth');
  const donutTotal = document.getElementById('donutTotal');

  if (chartMonth) chartMonth.textContent = summary.latest_month || '';
  if (donutTotal) donutTotal.textContent = formatRupee(summary.total_spend);
}

function renderStats(summary) {
  const row = document.getElementById('statsRow');
  if (!row) return;

  const savingsColor = summary.savings >= 0 ? 'green' : 'red';
  const rateColor = summary.savings_rate >= 20 ? 'green' : summary.savings_rate >= 10 ? 'gold' : 'red';

  row.innerHTML = `
    <div class="stat-card income">
      <div class="stat-label">MONTHLY INCOME</div>
      <div class="stat-value green">${formatRupee(summary.total_income)}</div>
      <div class="stat-sub">credited this month</div>
    </div>
    <div class="stat-card spend">
      <div class="stat-label">TOTAL SPEND</div>
      <div class="stat-value red">${formatRupee(summary.total_spend)}</div>
      <div class="stat-sub">${summary.transaction_count} transactions</div>
    </div>
    <div class="stat-card savings">
      <div class="stat-label">NET SAVINGS</div>
      <div class="stat-value ${savingsColor}">${formatRupee(Math.abs(summary.savings))}${summary.savings < 0 ? ' deficit' : ''}</div>
      <div class="stat-sub">this month</div>
    </div>
    <div class="stat-card rate">
      <div class="stat-label">SAVINGS RATE</div>
      <div class="stat-value ${rateColor}">${summary.savings_rate}%</div>
      <div class="stat-sub">target: ≥20%</div>
    </div>
  `;
}

function renderDonut(categories) {
  const canvas = document.getElementById('donutChart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  if (state.charts.donut) state.charts.donut.destroy();

  state.charts.donut = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: categories.map(c => c.name),
      datasets: [{
        data: categories.map(c => c.value),
        backgroundColor: PALETTE.slice(0, categories.length),
        borderWidth: 0,
        hoverOffset: 8,
      }]
    },
    options: {
      cutout: '68%',
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${formatRupee(ctx.parsed)} (${categories[ctx.dataIndex].pct}%)`
          }
        }
      },
      animation: { animateRotate: true, duration: 800 }
    }
  });

  // Legend
  const legend = document.getElementById('categoryLegend');
  if (!legend) return;

  legend.innerHTML = categories.map((c, i) => `
    <div class="legend-item">
      <div class="legend-dot" style="background:${PALETTE[i]}"></div>
      <span class="legend-name">${c.name}</span>
      <span class="legend-amt">${formatRupee(c.value)}</span>
      <span class="legend-pct">${c.pct}%</span>
    </div>
  `).join('');
}

function renderTrend(monthly) {
  const canvas = document.getElementById('trendChart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  if (state.charts.trend) state.charts.trend.destroy();

  state.charts.trend = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: monthly.map(m => m.month),
      datasets: [
        {
          label: 'Income',
          data: monthly.map(m => m.income),
          backgroundColor: 'rgba(0,255,136,0.2)',
          borderColor: '#00ff88',
          borderWidth: 1,
          borderRadius: 3,
        },
        {
          label: 'Spend',
          data: monthly.map(m => m.spend),
          backgroundColor: 'rgba(255,77,109,0.2)',
          borderColor: '#ff4d6d',
          borderWidth: 1,
          borderRadius: 3,
        }
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          labels: { color: '#8fa3c0', font: { family: 'Space Mono', size: 10 } }
        },
        tooltip: {
          callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${formatRupee(ctx.parsed.y)}` }
        }
      },
      scales: {
        x: {
          ticks: { color: '#4a6080', font: { family: 'Space Mono', size: 10 } },
          grid: { color: 'rgba(255,255,255,0.04)' }
        },
        y: {
          ticks: {
            color: '#4a6080',
            font: { family: 'Space Mono', size: 10 },
            callback: v => '₹' + (v / 1000).toFixed(0) + 'k'
          },
          grid: { color: 'rgba(255,255,255,0.04)' }
        }
      }
    }
  });
}

function renderMoM(changes) {
  const list = document.getElementById('momList');
  if (!list) return;

  if (!changes || changes.length === 0) {
    list.innerHTML = '<div class="empty-state"><span>📊</span>Only one month of data</div>';
    return;
  }

  const max = Math.max(...changes.map(c => Math.abs(c.change)));
  list.innerHTML = changes.map(c => {
    const isUp = c.change > 0;
    const width = max > 0 ? (Math.abs(c.change) / max * 100).toFixed(0) : 0;
    const sign = isUp ? '+' : '';
    return `
      <div class="mom-item">
        <div class="mom-cat">${c.category}</div>
        <div class="mom-bar-wrap">
          <div class="mom-bar ${isUp ? 'up' : 'down'}" style="width:${width}%"></div>
        </div>
        <div class="mom-pct ${isUp ? 'up' : 'down'}">${sign}${c.change}%</div>
      </div>
    `;
  }).join('');
}

function renderAlerts(anomalies) {
  const list = document.getElementById('alertList');
  const badge = document.getElementById('alertBadge');
  if (!list || !badge) return;

  if (!anomalies || anomalies.all_alerts.length === 0) {
    badge.textContent = 'CLEAR';
    badge.className = 'alert-badge ok';
    list.innerHTML = '<div class="empty-state"><span>✓</span>No anomalies detected</div>';
    return;
  }

  const count = anomalies.alert_count;
  badge.textContent = count + (anomalies.has_critical ? ' CRITICAL' : ' WARNINGS');
  badge.className = 'alert-badge ' + (anomalies.has_critical ? 'critical' : 'warning');

  list.innerHTML = anomalies.all_alerts.slice(0, 4).map(a => `
    <div class="alert-item ${a.severity || 'medium'}">
      ${a.message}
    </div>
  `).join('');
}

function renderAnomalies(anomalies) {
  if (!anomalies) return;

  // Budget alerts
  const budgetDiv = document.getElementById('budgetAlerts');
  if (budgetDiv) {
    if (anomalies.all_alerts.filter(a => a.type === 'budget_exceeded').length === 0) {
      budgetDiv.innerHTML = '<div class="empty-state"><span>✓</span>All categories within budget</div>';
    } else {
      budgetDiv.innerHTML = anomalies.all_alerts
        .filter(a => a.type === 'budget_exceeded')
        .map(a => `
          <div class="anomaly-row ${a.severity}">
            <div class="anomaly-row-title">${a.category}</div>
            <div class="anomaly-row-detail">${a.message}</div>
            <div class="anomaly-row-meta">
              <span class="anomaly-tag ${a.severity}">${a.severity.toUpperCase()}</span>
            </div>
          </div>
        `).join('');
    }
  }

  // Category spikes
  const spikesDiv = document.getElementById('categorySpikes');
  if (spikesDiv) {
    if (anomalies.all_alerts.filter(a => a.type === 'category_spike').length === 0) {
      spikesDiv.innerHTML = '<div class="empty-state"><span>✓</span>No unusual spikes detected</div>';
    } else {
      spikesDiv.innerHTML = anomalies.all_alerts
        .filter(a => a.type === 'category_spike')
        .map(a => `
          <div class="anomaly-row ${a.severity}">
            <div class="anomaly-row-title">${a.category} ↑${a.change_pct}%</div>
            <div class="anomaly-row-detail">${a.message}</div>
            <div class="anomaly-row-meta">
              <span class="anomaly-tag ${a.severity}">SPIKE</span>
            </div>
          </div>
        `).join('');
    }
  }

  // Transaction anomalies
  const txnDiv = document.getElementById('txnAnomalies');
  if (txnDiv) {
    if (!anomalies.transaction_anomalies || anomalies.transaction_anomalies.length === 0) {
      txnDiv.innerHTML = '<div class="empty-state"><span>✓</span>No outlier transactions found</div>';
    } else {
      txnDiv.innerHTML = anomalies.transaction_anomalies.map(t => `
        <div class="txn-anomaly-row">
          <div class="txn-date">${t.date}</div>
          <div class="txn-desc" title="${t.description}">
            ${t.description.substring(0, 40)}${t.description.length > 40 ? '…' : ''}
          </div>
          <div class="txn-amt">${formatRupee(t.amount)}</div>
          <div class="txn-z">z=${t.z_score}</div>
        </div>
      `).join('');
    }
  }
}

function showInitialAnalysis(text) {
  const card = document.getElementById('initialAnalysisCard');
  const body = document.getElementById('initialAnalysisBody');
  if (!card || !body) return;

  body.innerHTML = formatMarkdown(text);
  card.style.display = 'block';
}

// ─── CHAT ─────────────────────────────────────────────────────────────────────

async function sendMessage() {
  const input = document.getElementById('chatInput');
  const msg = input?.value?.trim();
  if (!msg || !state.dataLoaded) return;

  input.value = '';
  appendMessage('user', msg);
  const thinkingId = showThinking();
  setSendDisabled(true);

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ message: msg }),
    });
    const data = await res.json();
    removeThinking(thinkingId);

    if (data.success) {
      appendMessage('assistant', data.response);
      if (data.sources && data.sources.length > 0) {
        showSources(data.sources);
      }
    } else {
      appendMessage('assistant', `⚠️ Error: ${data.error}`);
    }
  } catch (err) {
    removeThinking(thinkingId);
    appendMessage('assistant', `⚠️ Network error: ${err.message}`);
  }

  setSendDisabled(false);
  input.focus();
}

function askQuick(question) {
  const input = document.getElementById('chatInput');
  if (input) input.value = question;
  sendMessage();
}

function appendMessage(role, text) {
  const container = document.getElementById('chatMessages');
  if (!container) return;

  const div = document.createElement('div');
  div.className = `message ${role}`;
  const time = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

  div.innerHTML = `
    <div class="message-bubble">${role === 'assistant' ? formatMarkdown(text) : escapeHtml(text)}</div>
    <div class="message-meta">${role === 'user' ? 'You' : 'FinSight'} · ${time}</div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function showThinking() {
  const container = document.getElementById('chatMessages');
  if (!container) return null;

  const id = 'thinking-' + Date.now();
  const div = document.createElement('div');
  div.id = id;
  div.className = 'message assistant';
  div.innerHTML = `
    <div class="thinking-bubble">
      <div class="thinking-dots"><span></span><span></span><span></span></div>
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeThinking(id) {
  if (!id) return;
  const el = document.getElementById(id);
  if (el) el.remove();
}

function showSources(sources) {
  const panel = document.getElementById('sourcesPanel');
  const list = document.getElementById('sourcesList');
  if (!panel || !list) return;

  panel.style.display = 'block';
  list.innerHTML = sources.map(s => `
    <div class="source-item">
      <span>${s.title}</span>
      <span class="source-score">${(s.score * 100).toFixed(0)}%</span>
    </div>
  `).join('');
}

function setSendDisabled(disabled) {
  const btn = document.getElementById('sendBtn');
  if (btn) btn.disabled = disabled;
}

// ─── UI HELPERS ───────────────────────────────────────────────────────────────

function showLoading() {
  const overlay = document.getElementById('loadingOverlay');
  if (overlay) overlay.style.display = 'flex';
}

function hideLoading() {
  const overlay = document.getElementById('loadingOverlay');
  if (overlay) overlay.style.display = 'none';
}

function showNav() {
  const nav = document.querySelector('.header-nav');
  if (!nav) return;
  nav.style.display = 'flex';
}

function hideNav() {
  const nav = document.querySelector('.header-nav');
  if (!nav) return;
  nav.style.display = 'none';
}

function showApp() {
  const uploadSection = document.getElementById('uploadSection');
  const appMain = document.getElementById('appMain');

  if (uploadSection) uploadSection.style.display = 'none';
  if (appMain) appMain.style.display = 'block';

  switchView('dashboard');
}

function updateHeaderStatus(summary) {
  const status = document.getElementById('headerStatus');
  if (!status) return;

  status.innerHTML = `
    <span class="status-dot active"></span>
    <span style="font-family:var(--mono);font-size:11px;color:var(--green)">
      ${summary.latest_month} · ₹${(summary.total_income / 1000).toFixed(0)}k income · ${summary.transaction_count} txns
    </span>
  `;
}

function formatRupee(amount) {
  if (amount === null || amount === undefined) return '₹0';
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
  if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}k`;
  return `₹${Math.round(amount)}`;
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function formatMarkdown(text) {
  // Very lightweight markdown → HTML
  return String(text)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/^### (.+)$/gm, '<div style="color:var(--text-1);font-weight:700;margin-top:10px;margin-bottom:4px">$1</div>')
    .replace(/^## (.+)$/gm, '<div style="color:var(--primary);font-weight:700;font-size:13px;margin-top:12px;margin-bottom:6px">$1</div>')
    .replace(/^- (.+)$/gm, '<div style="padding-left:12px;margin-top:2px">• $1</div>')
    .replace(/\n/g, '<br>');
}

// ─── INIT ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Keep nav hidden until the user uploads data or loads sample data
  hideNav();

  // Check if API is configured
  fetch('/api/health')
    .then(r => r.json())
    .then(data => {
      if (!data.api_key_set) {
        console.warn('ANTHROPIC_API_KEY not set — AI advice will not work');
      }
    });
});