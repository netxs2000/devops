/**
 * @file reports.js
 * @description 质量报告看板、Chart.js 图表渲染及全网预警。
 */

let radarChart = null;
let priorityChart = null;
let typeChart = null;

/**
 * 渲染质量报告大屏
 */
async function renderReportDashboard() {
    UI.toggleLoading("数据同步中...", true);

    try {
        const data = await Api.get('/dashboard/summary');

        // 1. 更新统计数字
        const statsMap = {
            'stat-total': data.summary.total,
            'stat-bugs': data.summary.opened,
            'stat-passed': data.summary.closed
        };
        for (let id in statsMap) {
            const el = document.getElementById(id);
            if (el) el.innerText = statsMap[id];
        }

        const rate = data.summary.total > 0 ? Math.round((data.summary.closed / data.summary.total) * 100) : 0;
        const rateEl = document.getElementById('stat-rate');
        if (rateEl) rateEl.innerText = `${rate}%`;

        // 2. 绘制图表
        renderDashboardCharts(data.by_type, data.by_priority);

        // 3. 更新证言文本
        const user = window.currentUser || {};
        const userDept = user.department?.org_name || '全量数据';
        const testimony = `📜 **版本质量证言 (${userDept})**\n` +
            `──────────────────\n` +
            `● 存量待处理工单: **${data.summary.opened}** 项\n` +
            `● 累计已解决工单: **${data.summary.closed}** 项\n` +
            `● 核心风险分布: Bug(${data.by_type.bug || 0}), Requirement(${data.by_type.requirement || 0})\n\n` +
            `AI 质量判定：当前状态${data.summary.opened > 10 ? '受控但需关注' : '稳定'}。`;

        const tContent = document.getElementById('testimony-content');
        if (tContent) tContent.innerText = testimony;

        // 4. 加载实时动态
        loadDashboardRecentIssues();
        refreshGlobalAlerts();
    } catch (e) {
        console.error("Dashboard Sync Failed", e);
    } finally {
        UI.toggleLoading("", false);
    }
}

/**
 * 渲染 Chart.js 图表
 */
function renderDashboardCharts(typeData, priorityData) {
    const clearChart = (id) => {
        const chartInstance = Chart.getChart(id);
        if (chartInstance) chartInstance.destroy();
    };

    clearChart('priorityChart');
    const pCtx = document.getElementById('priorityChart');
    if (pCtx) {
        priorityChart = new Chart(pCtx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(priorityData),
                datasets: [{
                    data: Object.values(priorityData),
                    backgroundColor: ['#ef4444', '#f59e0b', '#3b82f6', '#10b981', '#6366f1']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom', labels: { color: '#fff' } } }
            }
        });
    }

    clearChart('typeChart');
    const tCtx = document.getElementById('typeChart');
    if (tCtx) {
        typeChart = new Chart(tCtx, {
            type: 'polarArea',
            data: {
                labels: Object.keys(typeData),
                datasets: [{
                    data: Object.values(typeData),
                    backgroundColor: ['rgba(99, 102, 241, 0.5)', 'rgba(139, 92, 246, 0.5)', 'rgba(16, 185, 129, 0.5)']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom', labels: { color: '#fff' } } }
            }
        });
    }
}

/**
 * 加载最近工单动态
 */
async function loadDashboardRecentIssues() {
    try {
        const issues = await Api.get('/dashboard/recent-issues');
        const container = document.getElementById('bench-body');
        if (!container) return;

        if (issues.length === 0) {
            container.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color:var(--text-dim);">暂无最近更新工单</td></tr>';
            return;
        }

        container.innerHTML = issues.map((issue, index) => {
            const date = new Date(issue.updated_at).toLocaleDateString();
            return `
                <tr>
                    <td>${index + 1}</td>
                    <td><span class="req-id-pill">#${issue.iid}</span> ${issue.title}</td>
                    <td>${issue.dept_name || 'N/A'}</td>
                    <td><span style="color:${issue.state === 'opened' ? 'var(--failed)' : 'var(--passed)'}">${issue.state.toUpperCase()}</span></td>
                    <td>${date}</td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        console.error("Failed to load recent issues", e);
    }
}

/**
 * 全网同步预警
 */
async function refreshGlobalAlerts() {
    const listDiv = document.getElementById('globalAlertsList');
    const panel = document.getElementById('globalAlertsPanel');
    if (!listDiv) return;

    try {
        const alerts = await Api.get('/global/alerts');
        if (alerts.length === 0) {
            if (panel) panel.style.display = 'none';
            return;
        }

        if (panel) panel.style.display = 'block';
        listDiv.innerHTML = alerts.map(a => `
            <div class="alert-item">
                <div class="alert-pulse"></div>
                <span class="alert-province">${a.province}</span>
                <span style="flex:1; color:var(--text-main);">${a.level === 'critical' ? '🔥' : '⚠️'} ${a.title}</span>
                <span style="color:var(--text-dim); font-size:12px;">${a.time}</span>
            </div>
        `).join('');
    } catch (e) {
        console.error('Failed to load global alerts:', e);
    }
}
