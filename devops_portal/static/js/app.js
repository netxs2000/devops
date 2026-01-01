/**
 * @file app.js
 * @description 应用全局控制器，负责视图切换、用户初始化和实时通知。
 */

/**
 * 切换主视图区域
 * @param {string} view 视图标识符
 */
function switchView(view) {
    const navItems = [
        'nav-dashboard', 'nav-tests', 'nav-defects', 'nav-reqs',
        'nav-matrix', 'nav-reports', 'nav-support', 'nav-sd-submit', 'nav-sd-my', 'nav-decision-hub'
    ];

    const viewItems = [
        'results', 'statsGrid', 'bugView', 'matrixView',
        'requirementsView', 'reportsView', 'view-servicedesk',
        'sdSubmitView', 'sdMyView', 'decisionHubView'
    ];

    // Reset all nav and views
    navItems.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.remove('active');
    });

    // 特殊处理 Dashboard 链接（没有 ID 的那个）
    const dashboardLink = document.querySelector('.nav-link:not([id])');
    if (dashboardLink) dashboardLink.classList.remove('active');

    viewItems.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });

    // 激活选定项
    const activeNav = document.getElementById(`nav-${view.replace('_', '-')}`);
    if (activeNav) activeNav.classList.add('active');
    if (view === 'dashboard' && dashboardLink) dashboardLink.classList.add('active');

    // 显示对应视图
    if (view === 'tests' || view === 'test-cases') {
        document.getElementById('results').style.display = 'flex';
        document.getElementById('statsGrid').style.display = 'grid';
    } else if (view === 'defects') {
        document.getElementById('bugView').style.display = 'block';
        if (typeof loadBugs === 'function') loadBugs();
    } else if (view === 'requirements') {
        document.getElementById('requirementsView').style.display = 'block';
        if (typeof loadRequirements === 'function') loadRequirements();
    } else if (view === 'support' || view === 'servicedesk') {
        document.getElementById('view-servicedesk').style.display = 'block';
        if (typeof loadServiceDeskTickets === 'function') loadServiceDeskTickets();
    } else if (view === 'matrix') {
        document.getElementById('matrixView').style.display = 'block';
        if (typeof loadMatrix === 'function') loadMatrix();
    } else if (view === 'reports') {
        document.getElementById('reportsView').style.display = 'block';
        if (typeof renderReportDashboard === 'function') renderReportDashboard();
    } else if (view === 'sd_submit') {
        document.getElementById('sdSubmitView').style.display = 'block';
        document.getElementById('sdFrame').src = 'service_desk.html';
    } else if (view === 'sd_my') {
        document.getElementById('sdMyView').style.display = 'block';
        document.getElementById('sdMyFrame').src = 'service_desk_my_tickets.html';
    } else if (view === 'decision_hub') {
        document.getElementById('decisionHubView').style.display = 'block';
        // 生产环境建议通过反向代理，开发环境先直连 Streamlit 默认端口
        document.getElementById('decisionHubFrame').src = 'http://localhost:8501/?embed=true';
    }
}

/**
 * 初始化实时通知 (SSE)
 */
function initPulse() {
    try {
        const token = Auth.getToken();
        if (!token) return;

        const es = new EventSource(`/notifications/stream?token=${token}`);

        es.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'refresh_dashboard') {
                UI.showToast(data.message, 'success');
                refreshActiveView();
            } else if (data.message && data.message !== 'System Connected') {
                UI.showToast(data.message, data.type || 'info');
            }
        };

        es.onerror = () => {
            es.close();
            setTimeout(initPulse, 5000); // 自动重连
        };
    } catch (e) {
        console.error("Pulse initialization failed", e);
    }
}

/**
 * 根据当前激活的视图触发增量刷新
 */
function refreshActiveView() {
    const views = [
        { id: 'results', refresh: () => typeof loadTestCases === 'function' && loadTestCases(true) },
        { id: 'requirementsView', refresh: () => typeof loadRequirements === 'function' && loadRequirements() },
        { id: 'bugView', refresh: () => typeof loadBugs === 'function' && loadBugs() },
        { id: 'view-servicedesk', refresh: () => typeof loadServiceDeskTickets === 'function' && loadServiceDeskTickets() }
    ];

    for (let view of views) {
        const el = document.getElementById(view.id);
        if (el && el.style.display !== 'none') {
            view.refresh();
            break;
        }
    }
}

/**
 * 页面加载初始化
 */
window.addEventListener('DOMContentLoaded', async () => {
    try {
        const user = await Auth.getCurrentUser();
        if (user) {
            initUserProfile(user);
            initPulse();
            // 默认显示首页，如果已经在某个视图则不自动切回
            if (window.location.hash) {
                switchView(window.location.hash.substring(1));
            }
        }
    } catch (e) {
        console.error("Initialization failed", e);
    }
});

/**
 * 渲染用户身份信息
 * @param {Object} user 用户对象
 */
function initUserProfile(user) {
    const nameEl = document.getElementById('user-display-name');
    const avatarEl = document.getElementById('user-avatar');
    const deptEl = document.getElementById('user-display-dept');

    if (nameEl) nameEl.innerText = user.full_name;
    if (avatarEl) avatarEl.innerText = user.full_name.charAt(0).toUpperCase();

    const dept = user.department?.org_name || user.department_code || 'No Dept';
    const loc = user.location?.location_name || 'Global';
    if (deptEl) deptEl.innerText = `${dept} • ${loc}`;

    // 数据权限徽章
    const badgeV2 = document.getElementById('data-scope-badge-v2');
    const scopeValueV2 = document.getElementById('scope-value-v2');
    const scopeIconV2 = document.getElementById('scope-icon-v2');

    if (badgeV2 && scopeValueV2) {
        scopeValueV2.innerText = loc;
        if (loc === 'Global') {
            badgeV2.style.background = 'rgba(16, 185, 129, 0.1)';
            badgeV2.style.borderColor = 'rgba(16, 185, 129, 0.2)';
            if (scopeIconV2) scopeIconV2.innerText = '🌐';
        }
        badgeV2.style.display = 'inline-flex';
    }

    window.currentUser = user;
}
