import { Api, UI, Auth } from './sys_core.js';

const RptOverviewHandler = {
    radarChart: null,
    priorityChart: null,
    typeChart: null,

    /**
     * 渲染质量报告大屏
     */
    async render() {
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
                if (el) el.textContent = statsMap[id];
            }

            const rate = data.summary.total > 0 ? Math.round((data.summary.closed / data.summary.total) * 100) : 0;
            const rateEl = document.getElementById('stat-rate');
            if (rateEl) rateEl.textContent = `${rate}%`;

            // 2. 绘制图表
            this.renderCharts(data.by_type, data.by_priority);

            // 3. 更新证言文本 (安全处理)
            const user = Auth.getPayload() || {};
            const userDept = user.department?.org_name || '全量数据';

            const testimonyContent = document.getElementById('testimony-content');
            if (testimonyContent) {
                testimonyContent.innerHTML = '';
                const title = document.createElement('div');
                title.className = 'u-weight-700 u-mb-10';
                title.textContent = `📜 版本质量证言 (${userDept})`;

                const details = document.createElement('div');
                details.className = 'u-pre-wrap';
                details.textContent =
                    `──────────────────\n` +
                    `● 存量待处理工单: ${data.summary.opened} 项\n` +
                    `● 累计已解决工单: ${data.summary.closed} 项\n` +
                    `● 核心风险分布: Bug(${data.by_type.bug || 0}), Requirement(${data.by_type.requirement || 0})\n\n` +
                    `AI 质量判定：当前状态${data.summary.opened > 10 ? '受控但需关注' : '稳定'}。`;

                testimonyContent.appendChild(title);
                testimonyContent.appendChild(details);
            }

            // 4. 加载实时动态
            this.loadRecentIssues();
            this.refreshGlobalAlerts();
        } catch (e) {
            console.error("Dashboard Sync Failed", e);
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 渲染 Chart.js 图表
     */
    renderCharts(typeData, priorityData) {
        if (typeof Chart === 'undefined') return;

        const clearChart = (id) => {
            const chartInstance = Chart.getChart(id);
            if (chartInstance) chartInstance.destroy();
        };

        // 设计令牌对应的颜色
        const colors = {
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6',
            success: '#10b981',
            accent: '#6366f1'
        };

        clearChart('priorityChart');
        const pCtx = document.getElementById('priorityChart');
        if (pCtx) {
            this.priorityChart = new Chart(pCtx, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(priorityData),
                    datasets: [{
                        data: Object.values(priorityData),
                        backgroundColor: [colors.error, colors.warning, colors.info, colors.success, colors.accent]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { color: '#888' } } }
                }
            });
        }

        clearChart('typeChart');
        const tCtx = document.getElementById('typeChart');
        if (tCtx) {
            this.typeChart = new Chart(tCtx, {
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
                    plugins: { legend: { position: 'bottom', labels: { color: '#888' } } }
                }
            });
        }
    },

    /**
     * 加载最近工单动态
     */
    async loadRecentIssues() {
        try {
            const issues = await Api.get('/dashboard/recent-issues');
            const container = document.getElementById('bench-body');
            if (!container) return;

            container.innerHTML = '';

            if (issues.length === 0) {
                const tr = document.createElement('tr');
                const td = document.createElement('td');
                td.colSpan = 5;
                td.className = 'u-text-center u-p-20 u-color-secondary';
                td.textContent = '暂无最近更新工单';
                tr.appendChild(td);
                container.appendChild(tr);
                return;
            }

            const template = document.getElementById('rpt-recent-issue-row-tpl');
            const fragment = document.createDocumentFragment();

            issues.forEach((issue, index) => {
                const clone = template.content.cloneNode(true);
                const date = new Date(issue.updated_at).toLocaleDateString();

                clone.querySelector('.js-issue-index').textContent = index + 1;
                clone.querySelector('.js-issue-iid').textContent = `#${issue.iid}`;
                clone.querySelector('.js-issue-title').textContent = issue.title;
                clone.querySelector('.js-issue-dept').textContent = issue.dept_name || 'N/A';

                const stateEl = clone.querySelector('.js-issue-state');
                stateEl.textContent = issue.state.toUpperCase();
                stateEl.className = `js-issue-state ${issue.state === 'opened' ? 'u-color-error' : 'u-color-success'}`;

                clone.querySelector('.js-issue-date').textContent = date;

                fragment.appendChild(clone);
            });

            container.appendChild(fragment);
        } catch (e) {
            console.error("Failed to load recent issues", e);
        }
    },

    /**
     * 全网同步预警
     */
    async refreshGlobalAlerts() {
        const listDiv = document.getElementById('globalAlertsList');
        const panel = document.getElementById('globalAlertsPanel');
        if (!listDiv) return;

        try {
            const alerts = await Api.get('/global/alerts');
            if (alerts.length === 0) {
                if (panel) panel.classList.add('u-hide');
                return;
            }

            if (panel) panel.classList.remove('u-hide');
            listDiv.innerHTML = '';

            const template = document.getElementById('rpt-alert-tpl');
            const fragment = document.createDocumentFragment();

            alerts.forEach(a => {
                const clone = template.content.cloneNode(true);
                clone.querySelector('.js-alert-province').textContent = a.province;

                const titleEl = clone.querySelector('.js-alert-title');
                titleEl.textContent = `${a.level === 'critical' ? '🔥' : '⚠️'} ${a.title}`;

                clone.querySelector('.js-alert-time').textContent = a.time;
                fragment.appendChild(clone);
            });

            listDiv.appendChild(fragment);
        } catch (e) {
            console.error('Failed to load global alerts:', e);
        }
    }
};

export default RptOverviewHandler;
