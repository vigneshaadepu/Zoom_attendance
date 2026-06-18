/**
 * EduTrack — Dashboard Controller
 * Handles: live polling, chart init, dynamic data loading, match confirmations
 */

let trendChart = null;
let pieChart   = null;
let barChart   = null;

// ─── Init on DOM ready ───────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    await initCharts();
    initLivePolling();
    await loadCourseFilter();
});

// ─── Chart Initialization ─────────────────────────────────────────
async function initCharts() {
    const data = window.DASHBOARD_DATA || {};

    // Trend line chart
    trendChart = renderTrendChart('trendChart', data.chartLabels || [], data.chartRates || []);

    // Pie chart — load from last session
    await loadPieChart();

    // Bar chart — per-student rates
    await loadBarChart();

    // Heatmap
    renderHeatmap('heatmapContainer');
}

async function loadPieChart() {
    try {
        const resp = await fetch('/api/attendance/trend?days=7');
        const data = await resp.json();

        if (!data.session_ids || data.session_ids.length === 0) {
            renderPieChart('pieChart', 0, 0, 0);
            return;
        }

        // Get last session stats
        const lastSessionId = data.session_ids[data.session_ids.length - 1];
        const sessResp = await fetch(`/api/session/${lastSessionId}/live`);

        // Fallback: use last rate to estimate
        const lastRate = data.rates[data.rates.length - 1] || 0;
        renderPieChart('pieChart', Math.round(lastRate), Math.round(100 - lastRate), 0);
    } catch (e) {
        renderPieChart('pieChart', 0, 0, 0);
    }
}

async function loadBarChart() {
    try {
        const resp = await fetch('/api/students/risk');
        const data = await resp.json();
        const allStudentsResp = await fetch('/api/attendance/trend?days=90');
        const allData = await allStudentsResp.json();

        // Build per-course bar
        const labels = allData.labels || [];
        const rates  = allData.rates  || [];

        if (labels.length > 0) {
            barChart = renderBarChart('barChart', labels, rates);
        }
    } catch (e) {
        console.warn('Bar chart load failed:', e);
    }
}

// ─── Course filter ────────────────────────────────────────────────
async function loadCourseFilter() {
    try {
        const resp = await fetch('/api/courses');
        const courses = await resp.json();
        const select = document.getElementById('courseTrendFilter');
        if (select && courses.length > 0) {
            courses.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c; opt.textContent = c;
                select.appendChild(opt);
            });
        }
    } catch(e) {}

    document.getElementById('courseTrendFilter')?.addEventListener('change', reloadTrend);
    document.getElementById('daysTrendFilter')?.addEventListener('change', reloadTrend);
}

async function reloadTrend() {
    const course = document.getElementById('courseTrendFilter')?.value || '';
    const days   = document.getElementById('daysTrendFilter')?.value || '30';
    try {
        const resp = await fetch(`/api/attendance/trend?course=${encodeURIComponent(course)}&days=${days}`);
        const data = await resp.json();
        if (trendChart) {
            trendChart.data.labels = data.labels;
            trendChart.data.datasets[0].data = data.rates;
            trendChart.update('active');
        }
    } catch (e) {}
}

// ─── Live Session Polling ─────────────────────────────────────────
function initLivePolling() {
    const sessionId = window.DASHBOARD_DATA?.liveSessionId;
    if (!sessionId) return;

    // Show topbar live indicator
    const indicator = document.getElementById('liveIndicator');
    if (indicator) indicator.style.display = 'flex';

    pollLiveSession(sessionId);
    setInterval(() => pollLiveSession(sessionId), 30000);
}

async function pollLiveSession(sessionId) {
    try {
        const resp = await fetch(`/api/session/${sessionId}/live`);
        const data = await resp.json();

        if (!data.is_live) return;

        // Update participant count
        const partEl = document.getElementById('liveParticipants');
        if (partEl) partEl.textContent = data.participant_count ?? '—';

        // Update duration
        const durEl = document.getElementById('liveDuration');
        if (durEl) {
            const mins = Math.floor((data.duration_seconds || 0) / 60);
            const hrs  = Math.floor(mins / 60);
            const rem  = mins % 60;
            durEl.textContent = hrs > 0 ? `${hrs}h ${rem}m` : `${mins}m`;
        }
    } catch (e) {
        console.warn('Live poll failed:', e);
    }
}

// ─── Match Confirmation (Review Queue) ────────────────────────────
async function confirmMatch(recordId, studentId, zoomName, zoomEmail, confirmed) {
    const row = document.getElementById(`reviewRow${recordId}`);

    try {
        const resp = await fetch(`/students/${studentId}/link`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                zoom_name: zoomName,
                zoom_email: zoomEmail,
                record_id: recordId,
                confirmed: confirmed,
            }),
        });
        const data = await resp.json();

        if (data.success && row) {
            row.style.transition = 'opacity 0.4s, transform 0.4s';
            row.style.opacity = '0';
            row.style.transform = 'translateX(20px)';
            setTimeout(() => row.remove(), 400);

            Swal.fire({
                toast: true,
                position: 'bottom-end',
                icon: confirmed ? 'success' : 'info',
                title: confirmed ? 'Match confirmed' : 'Match rejected',
                showConfirmButton: false,
                timer: 3000,
                background: '#17203b',
                color: '#f8fafc',
                iconColor: confirmed ? '#10b981' : '#ef4444'
            });
        }
    } catch (e) {
        Swal.fire({
            toast: true,
            position: 'bottom-end',
            icon: 'error',
            title: 'Failed to save confirmation',
            showConfirmButton: false,
            timer: 3000,
            background: '#17203b',
            color: '#f8fafc'
        });
    }
}

// ─── Toast Helper ─────────────────────────────────────────────────
function showToast(message, type = 'success') {
    Swal.fire({
        toast: true,
        position: 'bottom-end',
        icon: type === 'danger' ? 'error' : (type === 'warning' ? 'warning' : 'success'),
        title: message,
        showConfirmButton: false,
        timer: 3500,
        background: '#17203b',
        color: '#f8fafc'
    });
}
