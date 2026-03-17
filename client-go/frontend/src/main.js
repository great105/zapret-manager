import './style.css';
import { GetServices, StartBypass, StopBypass, IsActive, CheckUpdate } from '../wailsjs/go/main/App';
import { EventsOn } from '../wailsjs/runtime/runtime';

let active = false;
let allServices = [];

// ── Init ─────────────────────────────────────────────────────────────

async function init() {
    allServices = await GetServices();
    renderServices();

    EventsOn('progress', onProgress);
    EventsOn('serviceStatus', onServiceStatus);
    EventsOn('isp', onISP);

    active = await IsActive();
    if (active) setActiveUI();

    try {
        const upd = await CheckUpdate();
        if (upd && upd.app_update) {
            document.getElementById('update-banner').classList.remove('hidden');
            document.getElementById('update-text').textContent =
                `Доступно обновление: v${upd.app_new_version}`;
        }
    } catch(e) {}
}

function renderServices() {
    const list = document.getElementById('services-list');
    const dpi = allServices.filter(s => s.bypass_method === 'dpi' || s.bypass_method === 'mixed');
    const ip = allServices.filter(s => s.bypass_method === 'ip');

    let html = '';
    if (dpi.length) {
        html += '<div class="svc-group-label">Обход через zapret2</div>';
        html += dpi.map(s => svcRow(s, true)).join('');
    }
    if (ip.length) {
        html += '<div class="svc-group-label dim">Нужен VPN (IP-блокировка)</div>';
        html += ip.map(s => svcRow(s, false)).join('');
    }
    list.innerHTML = html;
}

function svcRow(s, canBypass) {
    const tag = !canBypass ? '<span class="svc-tag">VPN</span>' : '';
    return `
        <label class="svc-row ${!canBypass ? 'svc-ip' : ''}" id="svc-${s.id}">
            <input type="checkbox" class="svc-check" data-id="${s.id}" ${canBypass ? 'checked' : ''}>
            <div class="svc-dot" id="dot-${s.id}"></div>
            <span class="svc-name">${s.name}${tag}</span>
            <span class="svc-status" id="st-${s.id}"></span>
        </label>`;
}

// ── Select all / none ────────────────────────────────────────────────

window.selectAll = function() {
    document.querySelectorAll('.svc-check').forEach(cb => cb.checked = true);
};
window.selectNone = function() {
    document.querySelectorAll('.svc-check').forEach(cb => cb.checked = false);
};

function getSelectedIds() {
    const ids = [];
    document.querySelectorAll('.svc-check:checked').forEach(cb => ids.push(cb.dataset.id));
    return ids;
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

    const selected = getSelectedIds();
    if (selected.length === 0) {
        showError('Выберите хотя бы один сервис');
        return;
    }

    const btn = document.getElementById('main-btn');
    btn.disabled = true;
    btn.textContent = 'Подключение...';
    showProgress(true);
    setStatus('Настройка...', 'yellow');

    // Mark only selected as checking
    selected.forEach(id => onServiceStatus({ id, status: 'check' }));

    try {
        await StartBypass(selected);
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
    document.getElementById('progress-fill').style.width = (data.pct || 0) + '%';
    document.getElementById('progress-text').textContent = data.text || '';
}

function onServiceStatus(data) {
    const dot = document.getElementById('dot-' + data.id);
    const st = document.getElementById('st-' + data.id);
    if (!dot || !st) return;

    dot.className = 'svc-dot';
    st.className = 'svc-status';

    const map = {
        'ok':      ['green', 'Доступен'],
        'blocked': ['red', 'Заблокирован'],
        'bypass':  ['green', 'Обход активен'],
        'check':   ['yellow', 'Проверка...'],
    };
    const [color, text] = map[data.status] || ['', ''];
    if (color) { dot.classList.add(color); st.classList.add(color); }
    st.textContent = text;
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
    // Disable checkboxes while active
    document.querySelectorAll('.svc-check').forEach(cb => cb.disabled = true);
}

function setIdleUI() {
    const btn = document.getElementById('main-btn');
    btn.disabled = false;
    btn.textContent = 'Обойти блокировки';
    btn.classList.remove('stop');
    setStatus('Готов к работе', '');
    document.querySelectorAll('.svc-check').forEach(cb => cb.disabled = false);
}

function showProgress(show) {
    document.getElementById('progress-area').classList.toggle('hidden', !show);
}

function resetServices() {
    document.querySelectorAll('.svc-dot').forEach(d => d.className = 'svc-dot');
    document.querySelectorAll('.svc-status').forEach(s => { s.className = 'svc-status'; s.textContent = ''; });
}

function showError(err) {
    const msg = typeof err === 'string' ? err : (err.message || err.toString());
    document.getElementById('error-text').value = msg;
    document.getElementById('error-modal').classList.remove('hidden');
}

window.copyError = function() {
    const ta = document.getElementById('error-text');
    ta.select();
    navigator.clipboard.writeText(ta.value).then(() => {
        const btn = document.querySelector('.btn-copy');
        btn.textContent = 'Скопировано';
        setTimeout(() => btn.textContent = 'Копировать', 1500);
    });
};

window.closeError = function() {
    document.getElementById('error-modal').classList.add('hidden');
};

init();
