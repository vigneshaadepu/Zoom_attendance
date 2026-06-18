/**
 * EduTrack — Chart.js Factory Functions
 */

// Global Chart.js defaults
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(255,255,255,0.08)';
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";

const COLORS = {
    accent:  '#3b82f6',
    purple:  '#8b5cf6',
    success: '#22c55e',
    warning: '#f59e0b',
    danger:  '#ef4444',
    info:    '#06b6d4',
    muted:   '#475569',
};

/**
 * Render the attendance trend line chart.
 */
function renderTrendChart(canvasId, labels, rates) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Attendance Rate (%)',
                data: rates,
                borderColor: COLORS.accent,
                backgroundColor: 'rgba(59,130,246,0.1)',
                borderWidth: 2.5,
                pointBackgroundColor: COLORS.accent,
                pointBorderColor: '#0a0f1e',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 7,
                fill: true,
                tension: 0.4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1a2237',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: ctx => ` ${ctx.parsed.y.toFixed(1)}% attendance`,
                    },
                },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { maxRotation: 45 },
                },
                y: {
                    min: 0, max: 100,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { callback: v => v + '%' },
                },
            },
            interaction: { intersect: false, mode: 'index' },
        },
    });
}

/**
 * Render the per-student bar chart.
 */
function renderBarChart(canvasId, labels, rates) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !labels.length) return null;

    // Color bars by rate
    const bgColors = rates.map(r =>
        r >= 75 ? 'rgba(34,197,94,0.6)'
               : r >= 50 ? 'rgba(245,158,11,0.6)'
                         : 'rgba(239,68,68,0.6)'
    );
    const borderColors = rates.map(r =>
        r >= 75 ? '#22c55e' : r >= 50 ? '#f59e0b' : '#ef4444'
    );

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Attendance Rate (%)',
                data: rates,
                backgroundColor: bgColors,
                borderColor: borderColors,
                borderWidth: 1.5,
                borderRadius: 4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1a2237',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    callbacks: {
                        label: ctx => ` ${ctx.parsed.y.toFixed(1)}%`,
                    },
                },
            },
            scales: {
                x: { grid: { display: false }, ticks: { maxRotation: 45, font: { size: 10 } } },
                y: {
                    min: 0, max: 100,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { callback: v => v + '%' },
                },
            },
        },
    });
}

/**
 * Render the present/absent/partial pie chart.
 */
function renderPieChart(canvasId, present, absent, partial) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Present', 'Absent', 'Partial'],
            datasets: [{
                data: [present, absent, partial],
                backgroundColor: [
                    'rgba(34,197,94,0.8)',
                    'rgba(239,68,68,0.8)',
                    'rgba(245,158,11,0.8)',
                ],
                borderColor: ['#22c55e', '#ef4444', '#f59e0b'],
                borderWidth: 2,
                hoverOffset: 8,
            }],
        },
        options: {
            responsive: true,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { padding: 16, usePointStyle: true, pointStyle: 'circle' },
                },
                tooltip: {
                    backgroundColor: '#1a2237',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    callbacks: {
                        label: ctx => {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                            return ` ${ctx.label}: ${ctx.parsed} (${pct}%)`;
                        },
                    },
                },
            },
        },
    });
}

/**
 * Render a student's individual attendance mini chart.
 */
function renderStudentMiniChart(canvasId, labels, statuses, durations) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Present (1) / Absent (0)',
                    data: statuses,
                    backgroundColor: statuses.map(s =>
                        s === 1 ? 'rgba(34,197,94,0.7)' : 'rgba(239,68,68,0.5)'
                    ),
                    borderColor: statuses.map(s =>
                        s === 1 ? '#22c55e' : '#ef4444'
                    ),
                    borderWidth: 1.5,
                    borderRadius: 4,
                    yAxisID: 'y',
                },
                {
                    label: 'Duration (min)',
                    data: durations,
                    type: 'line',
                    borderColor: COLORS.accent,
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    pointRadius: 3,
                    tension: 0.4,
                    yAxisID: 'y2',
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom', labels: { usePointStyle: true, font: { size: 10 } } },
            },
            scales: {
                y: {
                    min: 0, max: 1,
                    position: 'left',
                    ticks: { callback: v => v === 1 ? '✓' : '✗' },
                    grid: { color: 'rgba(255,255,255,0.05)' },
                },
                y2: {
                    position: 'right',
                    grid: { display: false },
                    ticks: { callback: v => v + 'm' },
                },
            },
        },
    });
}

/**
 * Render the attendance heatmap (student × session grid).
 */
async function renderHeatmap(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    try {
        const [trendResp, sessionsResp] = await Promise.all([
            fetch('/api/attendance/trend?days=90'),
            fetch('/api/attendance/trend?days=90'),
        ]);
        const trendData = await trendResp.json();

        if (!trendData.labels || trendData.labels.length === 0) {
            container.innerHTML = '<p class="text-muted text-center py-3">No session data available for heatmap.</p>';
            return;
        }

        // Simplified heatmap: show trend data as a horizontal bar-based grid
        let html = '<div style="overflow-x:auto;"><table class="heatmap-table" style="border-collapse:separate; border-spacing:4px;">';
        html += '<tr><th style="text-align:left; color:#64748b; font-size:11px; padding-right:8px;">Session</th>';
        html += '<th style="color:#64748b; font-size:11px; padding:4px;">Attendance</th></tr>';

        trendData.labels.forEach((label, i) => {
            const rate = trendData.rates[i];
            const color = rate >= 75 ? '#22c55e' : rate >= 50 ? '#f59e0b' : '#ef4444';
            html += `<tr>
                <td style="font-size:11px; color:#94a3b8; padding-right:8px; white-space:nowrap;">${label}</td>
                <td>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div style="width:200px; height:12px; background:#1a2237; border-radius:6px; overflow:hidden;">
                            <div style="width:${rate}%; height:100%; background:${color}; border-radius:6px; transition:width 0.6s;"></div>
                        </div>
                        <span style="font-size:12px; font-weight:600; color:${color};">${rate}%</span>
                    </div>
                </td>
            </tr>`;
        });

        html += '</table></div>';
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<p class="text-muted text-center py-3">Heatmap unavailable.</p>';
    }
}
