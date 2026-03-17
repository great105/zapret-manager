import './style.css';
import { GetServices, StartBypass, StopBypass, IsActive, CheckUpdate } from '../wailsjs/go/main/App';
import { EventsOn } from '../wailsjs/runtime/runtime';

let active = false;

// ── Init ─────────────────────────────────────────────────────────────

async function init() {
    // Load services list
    const services = await GetServices();
    const list = document.getElementById('services-list');
    list.innerHTML = services.map(s => `
        <div class="svc-row" id="svc-${s.id}">
            <div class="svc-dot" id="dot-${s.id}"></div>
            <span class="svc-name">${s.name}</span>
            <span class="svc-status" id="st-${s.id}"></span>
        </div>
    `).join('');

    // Listen to events from Go
    EventsOn('progress', onProgress);
    EventsOn('serviceStatus', onServiceStatus);
    EventsOn('isp', onISP);

    // Check if already active
    active = await IsActive();
    if (active) setActiveUI();

    // Check updates in background
    try {
        const upd = await CheckUpdate();
        if (upd && upd.app_update) {
            document.getElementById('update-banner').classList.remove('hidden');
            document.getElementById('update-text').textContent =
                `Доступно обновление: v${upd.app_new_version}`;
        }
    } catch(e) {}
}

// ── Main button ──────────────────────────────────────────────────────

window.onMainClick = async function() {
    if (active) {
        StopBypass();
        active = false;
        setIdleUI();
        resetServices();
        return;
    }

    const btn = document.getElementById('main-btn');
    btn.disabled = true;
    btn.textContent = 'Подключение...';
    showProgress(true);
    setStatus('Настройка...', 'yellow');
    markAllServices('check');

    try {
        await StartBypass();
        active = true;
        setActiveUI();
    } catch(err) {
        showError(err);
        setIdleUI();
    }

    showProgress(false);
};

// ── Events from Go ───────────────────────────────────────────────────

function onProgress(data) {
    const fill = document.getElementById('progress-fill');
    const text = document.getElementById('progress-text');
    fill.style.width = (data.pct || 0) + '%';
    text.textContent = data.text || '';
}

function onServiceStatus(data) {
    const dot = document.getElementById('dot-' + data.id);
    const st = document.getElementById('st-' + data.id);
    if (!dot || !st) return;

    dot.className = 'svc-dot';
    st.className = 'svc-status';

    switch(data.status) {
        case 'ok':
            dot.classList.add('green');
            st.classList.add('green');
            st.textContent = 'Доступен';
            break;
        case 'blocked':
            dot.classList.add('red');
            st.classList.add('red');
            st.textContent = 'Заблокирован';
            break;
        case 'bypass':
            dot.classList.add('green');
            st.classList.add('green');
            st.textContent = 'Обход активен';
            break;
        case 'check':
            dot.classList.add('yellow');
            st.classList.add('yellow');
            st.textContent = 'Проверка...';
            break;
        default:
            st.textContent = '';
    }
}

function onISP(data) {
    document.getElementById('isp-name').textContent = data.name || '';
}

// ── UI helpers ───────────────────────────────────────────────────────

function setStatus(text, color) {
    document.getElementById('status-text').textContent = text;
    document.getElementById('status-text').style.color = `var(--${color || 'dim'})`;
    const dot = document.getElementById('status-dot');
    dot.className = 'dot';
    if (color) dot.classList.add(color);
}

function setActiveUI() {
    const btn = document.getElementById('main-btn');
    btn.disabled = false;
    btn.textContent = 'Остановить';
    btn.classList.add('stop');
    setStatus('Обход активен', 'green');
}

function setIdleUI() {
    const btn = document.getElementById('main-btn');
    btn.disabled = false;
    btn.textContent = 'Обойти блокировки';
    btn.classList.remove('stop');
    setStatus('Готов к работе', '');
}

function showProgress(show) {
    document.getElementById('progress-area').classList.toggle('hidden', !show);
}

function markAllServices(status) {
    document.querySelectorAll('.svc-row').forEach(row => {
        const id = row.id.replace('svc-', '');
        onServiceStatus({ id, status });
    });
}

function resetServices() {
    document.querySelectorAll('.svc-dot').forEach(d => d.className = 'svc-dot');
    document.querySelectorAll('.svc-status').forEach(s => { s.className = 'svc-status'; s.textContent = ''; });
}

function showError(err) {
    const msg = typeof err === 'string' ? err : (err.message || err.toString());
    document.getElementById('error-text').textContent = msg;
    document.getElementById('error-modal').classList.remove('hidden');
}

window.closeError = function() {
    document.getElementById('error-modal').classList.add('hidden');
};

// ── Start ────────────────────────────────────────────────────────────
init();
