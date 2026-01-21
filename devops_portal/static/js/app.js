/**
 * @file app.js
 * @description 应用全局控制器，负责视图切换、用户初始化和实时通知。
 */

/**
 * 侧边栏导航配置
 */
const sidebarConfig = [
    {
        title: "项目执行",
        expanded: true,
        items: [
            { id: "nav-iterations", label: "迭代计划", href: "iteration_plan.html", icon: "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" },
            { id: "nav-reqs", label: "需求管理", href: "#requirements", onclick: "switchView('requirements')", icon: "M9 11l3 3L22 4; M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" },
            { id: "nav-support", label: "工单管理", href: "#support", onclick: "switchView('support')", icon: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z; M8 9h8; M8 13h6" }
        ]
    },
    {
        title: "质量保障",
        expanded: true,
        items: [
            { id: "nav-dashboard", label: "质量看板", href: "#dashboard", onclick: "switchView('dashboard')", icon: "rect x=3 y=3 width=7 height=7; rect x=14 y=3 width=7 height=7; rect x=14 y=14 width=7 height=7; rect x=3 y=14 width=7 height=7", active: true },
            { id: "nav-tests", label: "用例库", href: "#test-cases", onclick: "switchView('test-cases')", icon: "M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" },
            { id: "nav-test-execution", label: "测试执行", href: "#test-execution", onclick: "switchView('test-execution')", icon: "M13 2L3 14h9l-1 8 10-12h-9l1-8z" },
            { id: "nav-defects", label: "缺陷管理", href: "#defects", onclick: "switchView('defects')", icon: "circle cx=12 cy=12 r=10; line x1=12 y1=8 x2=12 y2=12; line x1=12 y1=16 x2=12.01 y2=16", badgeId: "badge-defects" },
            { id: "nav-matrix", label: "追溯矩阵", href: "#matrix", onclick: "switchView('matrix')", icon: "M12 2v20M2 12h20; M17 7l-5 5-5-5" }
        ]
    },
    {
        title: "洞察与治理",
        expanded: true,
        items: [
            { id: "nav-reports", label: "质量洞察", href: "#reports", onclick: "switchView('reports')", icon: "M21.21 15.89A10 10 0 1 1 8 2.83; M22 12A10 10 0 0 0 12 2v10z" },
            { id: "nav-governance", label: "元数据治理 (DataHub)", href: "http://localhost:9002/", target: "_blank", style: "color:var(--text-main);", icon: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" },
            { id: "nav-decision-hub", label: "决策中心 (Decision hub)", href: "http://localhost:8501/", target: "_blank", style: "color:var(--primary); font-weight:600;", icon: "circle cx=12 cy=12 r=10; polyline points=12 6 12 12 16 14" }
        ]
    },
    {
        title: "平台管理",
        adminOnly: true,
        expanded: true,
        items: [
            { id: "nav-admin-approvals", label: "用户注册审批", href: "#admin_approvals", onclick: "switchView('admin_approvals')", icon: "M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2; circle cx=8.5 cy=7 r=4; polyline points=17 11 19 13 23 9" },
            { id: "nav-admin-products", label: "产品体系管理", href: "#admin_products", onclick: "switchView('admin_products')", icon: "rect x=2 y=3 width=20 height=14 rx=2 ry=2; line x1=8 y1=21 x2=16 y2=21; line x1=12 y1=17 x2=12 y2=21" },
            { id: "nav-admin-projects", label: "项目映射配置", href: "#admin_projects", onclick: "switchView('admin_projects')", icon: "polyline points=4 7 4 4 20 4 20 7; line x1=9 y1=20 x2=15 y2=20; line x1=12 y1=4 x2=12 y2=20" },
            { id: "nav-admin-users", label: "员工身份目录", href: "#admin_users", onclick: "switchView('admin_users')", icon: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2; circle cx=9 cy=7 r=4; path d=M23 21v-2a4 4 0 0 0-3-3.87; path d=M16 3.13a4 4 0 0 1 0 7.75" }
        ]
    },
    {
        title: "支持与战略",
        expanded: true,
        items: [
            { id: "nav-sd-submit", label: "工单反馈", href: "#sd_submit", onclick: "switchView('sd_submit')", icon: "M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7; M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" },
            { id: "nav-sd-my", label: "我的工单", href: "#sd_my", onclick: "switchView('sd_my')", icon: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z; M8 9h8; M8 13h6" },
            { id: "nav-pulse", label: "心情指数打卡", href: "#pulse", onclick: "switchView('pulse')", icon: "circle cx=12 cy=12 r=10; path d=M8 14s1.5 2 4 2 4-2 4-2; line x1=9 y1=9 x2=9.01 y2=9; line x1=15 y1=9 x2=15.01 y2=9" }
        ]
    }
];

/**
 * 切换主视图区域
 */
function switchView(view) {
    const navItems = [
        'nav-dashboard', 'nav-tests', 'nav-test-execution', 'nav-defects', 'nav-reqs',
        'nav-matrix', 'nav-reports', 'nav-governance', 'nav-pulse', 'nav-support',
        'nav-sd-submit', 'nav-sd-my', 'nav-decision-hub', 'nav-admin-approvals',
        'nav-admin-products', 'nav-admin-projects', 'nav-admin-users'
    ];

    const viewItems = [
        'results', 'statsGrid', 'testExecutionView', 'bugView', 'matrixView',
        'requirementsView', 'reportsView', 'view-servicedesk',
        'sdSubmitView', 'sdMyView', 'decisionHubView', 'governanceView', 'pulseView',
        'adminApprovalsView', 'adminProductsView', 'adminProjectsView', 'adminUsersView'
    ];

    // Reset all nav and views
    navItems.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.remove('active');
    });

    const dashboardLink = document.querySelector('.nav-link:not([id])');
    if (dashboardLink) dashboardLink.classList.remove('active');

    viewItems.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });

    // 激活选定项
    const activeNav = document.getElementById(`nav-${view.replace('_', '-')}`);
    if (activeNav) {
        activeNav.classList.add('active');
        const parentGroup = activeNav.closest('.nav-group');
        if (parentGroup && !parentGroup.classList.contains('expanded')) {
            parentGroup.classList.add('expanded');
        }
    }

    if (view === 'dashboard' && dashboardLink) {
        dashboardLink.classList.add('active');
        const parentGroup = dashboardLink.closest('.nav-group');
        if (parentGroup && !parentGroup.classList.contains('expanded')) {
            parentGroup.classList.add('expanded');
        }
    }

    // 控制主 Header 的显隐
    const headerEl = document.getElementById('main-header');
    const headerViews = ['dashboard', 'tests', 'test-cases', 'defects', 'requirements', 'matrix', 'reports'];

    if (headerEl) {
        headerEl.style.display = (headerViews.includes(view) || !view) ? 'flex' : 'none';
    }

    // 显示对应视图
    if (view === 'tests' || view === 'test-cases' || view === 'dashboard') {
        document.getElementById('results').style.display = 'flex';
        document.getElementById('statsGrid').style.display = 'grid';
    } else if (view === 'test-execution') {
        document.getElementById('testExecutionView').style.display = 'block';
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
        UI.toggleLoading('', false);
    } else if (view === 'sd_my') {
        document.getElementById('sdMyView').style.display = 'block';
        document.getElementById('sdMyFrame').src = 'service_desk_my_tickets.html';
        UI.toggleLoading('', false);
    } else if (view === 'pulse') {
        document.getElementById('pulseView').style.display = 'block';
        document.getElementById('pulseFrame').src = 'devex_pulse.html';
        UI.toggleLoading('', false);
    } else if (view === 'admin_approvals') {
        document.getElementById('adminApprovalsView').style.display = 'block';
    } else if (view === 'admin_products') {
        document.getElementById('adminProductsView').style.display = 'block';
        loadAdminProducts();
    } else if (view === 'admin_projects') {
        document.getElementById('adminProjectsView').style.display = 'block';
        loadAdminProjects();
    } else if (view === 'admin_users') {
        document.getElementById('adminUsersView').style.display = 'block';
        loadAdminUsers();
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
            setTimeout(initPulse, 5000);
        };
    } catch (e) {
        console.error("Pulse initialization failed", e);
    }
}

/**
 * 刷新视图
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
    // 1. Setup Event Delegation for Sidebar Toggles
    const navContainer = document.getElementById('sidebar-nav-container');
    if (navContainer) {
        navContainer.addEventListener('click', (e) => {
            const title = e.target.closest('.nav-group-title');
            if (title) {
                console.log('Delegated Click on Title');
                UI.toggleNav(title);
            }
        });
    }

    // 2. Render Sidebar immediately
    try {
        renderSidebar();
    } catch (e) {
        console.error("Sidebar render failed", e);
    }

    // 3. Fetch User Profile
    try {
        const user = await Auth.getCurrentUser();
        if (user) {
            initUserProfile(user);
            initPulse();
            if (window.location.hash) {
                switchView(window.location.hash.substring(1));
            }
        }
    } catch (e) {
        console.error("Initialization failed", e);
    }
});

/**
 * 监听 hash 变化
 */
window.addEventListener('hashchange', () => {
    if (window.location.hash) {
        switchView(window.location.hash.substring(1));
    }
});

/**
 * 渲染用户身份信息
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

    renderSidebar(user);
    window.currentUser = user;
}

/**
 * 动态渲染侧边栏
 */
function renderSidebar(user) {
    const navContainer = document.getElementById('sidebar-nav-container');
    if (!navContainer) return;

    // Preserve existing expanded states
    const expandedGroups = new Set();
    navContainer.querySelectorAll('.nav-group.expanded').forEach(el => {
        if (el.dataset.groupTitle) expandedGroups.add(el.dataset.groupTitle);
    });

    const isAdmin = Auth.isAdmin();
    const hasUserManage = Auth.hasPermission('USER:MANAGE');

    navContainer.innerHTML = '';

    sidebarConfig.forEach(group => {
        if (group.adminOnly && !isAdmin && !hasUserManage) return;

        // Expanded logic: check config OR preserved state
        const isExpanded = expandedGroups.has(group.title) || (group.expanded && expandedGroups.size === 0);

        const groupDiv = document.createElement('div');
        groupDiv.className = `nav-group ${isExpanded ? 'expanded' : ''}`;
        groupDiv.dataset.groupTitle = group.title;

        const titleDiv = document.createElement('div');
        titleDiv.className = 'nav-group-title';
        titleDiv.innerHTML = `
            ${group.title}
            <svg class="nav-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
        `;
        groupDiv.appendChild(titleDiv);

        const itemsDiv = document.createElement('div');
        itemsDiv.className = 'nav-items';

        group.items.forEach(item => {
            const link = document.createElement('a');
            link.href = item.href;
            link.className = `nav-link ${item.active ? 'active' : ''}`;
            if (item.id) link.id = item.id;
            if (item.onclick) link.setAttribute('onclick', item.onclick);
            if (item.target) link.target = item.target;
            if (item.style) link.style.cssText = item.style;

            let iconSvgContent = '';
            const parseIcon = (iconStr) => {
                const parts = iconStr.split(';');
                parts.forEach(part => {
                    part = part.trim();
                    if (part.startsWith('M')) {
                        iconSvgContent += `<path d="${part}"></path>`;
                    } else if (part.includes('=')) {
                        const tagName = part.split(' ')[0];
                        iconSvgContent += `<${part}></${tagName}>`;
                    }
                });
            };
            parseIcon(item.icon);

            link.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    ${iconSvgContent}
                </svg>
                ${item.label}
                ${item.badgeId ? `<span class="nav-badge" id="${item.badgeId}" style="display:none;">0</span>` : ''}
            `;
            itemsDiv.appendChild(link);
        });

        groupDiv.appendChild(itemsDiv);
        navContainer.appendChild(groupDiv);
    });
}

// --- Admin Helper Functions (Restore) ---
async function loadAdminProjects() {
    try {
        const mdmTbody = document.getElementById('mdmProjectsTableBody');
        const unlinkedTbody = document.getElementById('unlinkedReposTableBody');
        const orgs = await Api.request('/admin/organizations');
        const mdmProjects = await Api.request('/admin/mdm-projects');
        const unlinkedRepos = await Api.request('/admin/unlinked-repos');

        mdmTbody.innerHTML = '';
        mdmProjects.forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><b>${p.project_name}</b><br><small>${p.project_id}</small></td>
                <td>${p.project_type}</td>
                <td><span class="badge ${p.status === 'RELEASED' ? 'badge-passed' : ''}">${p.status}</span></td>
                <td>${p.lead_repo_id ? '✅ 已绑定' : '⚠️ 未绑定'}</td>
                <td style="text-align:center;">${p.repo_count}</td>
            `;
            mdmTbody.appendChild(tr);
        });

        unlinkedTbody.innerHTML = '';
        unlinkedRepos.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${r.name}</td><td><button class="btn btn-sm" onclick="doLink(${r.id})">关联</button></td>`;
            unlinkedTbody.appendChild(tr);
        });
    } catch (e) { console.error(e); }
}

async function loadAdminUsers() {
    try {
        const tbody = document.getElementById('userMappingsTableBody');
        const mappings = await Api.request('/admin/identity-mappings');
        tbody.innerHTML = '';
        mappings.forEach(m => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><b>${m.user_name}</b></td>
                <td>${m.source_system}</td>
                <td><code>${m.external_user_id}</code></td>
                <td>${m.external_username || '-'}</td>
                <td>${m.external_email || '-'}</td>
                <td><button class="btn btn-sm btn-danger" onclick="deleteMapping(${m.id})">删除</button></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) { console.error(e); }
}

async function loadAdminProducts() {
    try {
        const productTbody = document.getElementById('productsTableBody');
        const products = await Api.request('/admin/products');
        productTbody.innerHTML = '';
        products.forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td><b>${p.product_name}</b></td><td>${p.category}</td><td>${p.lifecycle_status}</td><td>${p.owner_team_id}</td><td><button class="btn btn-sm">编辑</button></td>`;
            productTbody.appendChild(tr);
        });
    } catch (e) { console.error(e); }
}
