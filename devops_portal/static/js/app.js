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
        'nav-dashboard', 'nav-tests', 'nav-test-execution', 'nav-defects', 'nav-reqs',
        'nav-matrix', 'nav-reports', 'nav-governance', 'nav-pulse', 'nav-support', 'nav-sd-submit', 'nav-sd-my', 'nav-decision-hub', 'nav-admin-approvals', 'nav-admin-products', 'nav-admin-projects', 'nav-admin-users'
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

    // 控制主 Header 的显隐 (Test Repository Header)
    // 仅在测试管理相关视图显示：dashboard, test-cases, defects, requirements, matrix, reports
    const headerEl = document.getElementById('main-header');
    const headerViews = ['dashboard', 'tests', 'test-cases', 'defects', 'requirements', 'matrix', 'reports'];

    if (headerEl) {
        if (headerViews.includes(view) || !view) { // !view implies default dashboard
            headerEl.style.display = 'flex';
        } else {
            headerEl.style.display = 'none';
        }
    }

    // 显示对应视图
    if (view === 'tests' || view === 'test-cases' || view === 'dashboard') {
        if (view === 'dashboard' && dashboardLink) dashboardLink.classList.add('active'); // Re-add active just in case
        document.getElementById('results').style.display = 'flex';
        document.getElementById('statsGrid').style.display = 'grid';
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
    } else if (view === 'sd_my') {
        document.getElementById('sdMyView').style.display = 'block';
        document.getElementById('sdMyFrame').src = 'service_desk_my_tickets.html';
    } else if (view === 'decision_hub') {
        document.getElementById('decisionHubView').style.display = 'block';
        // 生产环境建议通过反向代理，开发环境先直连 Streamlit 默认端口
        document.getElementById('decisionHubFrame').src = 'http://localhost:8501/?embed=true';
    } else if (view === 'governance') {
        const govView = document.getElementById('governanceView');
        const govFrame = document.getElementById('governanceFrame');
        govView.style.display = 'block';

        // Use a placeholder or check service
        govFrame.src = 'about:blank'; // Clear previous failed load

        // Elegant service check
        fetch('http://localhost:9002/', { mode: 'no-cors', cache: 'no-cache' })
            .then(() => {
                govFrame.src = 'http://localhost:9002/';
            })
            .catch(() => {
                govView.innerHTML = `
                    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; color:var(--text-main); background:#0e1117; padding:40px; text-align:center;">
                        <div style="font-size:60px; margin-bottom:20px;">🛡️</div>
                        <h2 style="color:var(--primary);">DataHub 治理服务未就绪</h2>
                        <p style="color:var(--text-dim); max-width:500px; margin:15px 0;">
                            元数据中心 (DataHub) 通常作为独立的基础设施运行。目前系统检测到端口 9002 尚未开启，请联系管理员启动元数据技术栈。
                        </p>
                        <div style="background:rgba(255,255,255,0.03); padding:20px; border-radius:12px; border:1px solid rgba(255,255,255,0.1); margin-top:20px;">
                            <code style="color:var(--accent);">docker-compose -f docker-compose-datahub.yml up -d</code>
                        </div>
                    </div>
                `;
            });
    } else if (view === 'pulse') {
        document.getElementById('pulseView').style.display = 'block';
        document.getElementById('pulseFrame').src = 'devex_pulse.html';
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
 * 监听 URL hash 变化，支持浏览器后退/前进
 */
window.addEventListener('hashchange', () => {
    if (window.location.hash) {
        switchView(window.location.hash.substring(1));
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

    // 管理员及权限菜单显示逻辑
    const isAdmin = Auth.isAdmin();
    const hasUserManage = Auth.hasPermission('USER:MANAGE');
    const adminElements = document.querySelectorAll('.admin-only');

    if (isAdmin || hasUserManage) {
        adminElements.forEach(el => {
            // 使用 hidden 属性比 style.display 更可靠
            el.removeAttribute('hidden');
        });
    }

    // 细粒度控制 (如果后续需要)
    if (!Auth.hasPermission('USER:MANAGE')) {
        const approvalLink = document.getElementById('nav-admin-approvals');
        if (approvalLink) approvalLink.style.display = 'none';
    }

    window.currentUser = user;
}

// --- Admin: Two-Layer Project Assignment ---

async function loadAdminProjects() {
    try {
        const mdmTbody = document.getElementById('mdmProjectsTableBody');
        const unlinkedTbody = document.getElementById('unlinkedReposTableBody');
        mdmTbody.innerHTML = '<tr><td colspan="5">加载中...</td></tr>';
        unlinkedTbody.innerHTML = '<tr><td colspan="2">加载中...</td></tr>';

        // 1. 获取主项目、未关联仓库、组织列表
        const mdmProjects = await Api.request('/admin/mdm-projects');
        const unlinkedRepos = await Api.request('/admin/unlinked-repos');
        const orgs = await Api.request('/admin/organizations');

        // 2. 渲染主项目表格
        mdmTbody.innerHTML = '';
        mdmProjects.forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <div style="font-weight:bold;">${p.project_name}</div>
                    <code style="font-size:10px; opacity:0.7;">${p.project_id}</code>
                </td>
                <td><span style="font-size:11px;">${p.project_type}</span></td>
                <td><span class="badge ${p.status === 'RELEASED' ? 'badge-active' : ''}">${p.status}</span></td>
                <td>
                    <span class="badge ${p.lead_repo_id ? 'badge-passed' : 'badge-warning'}">
                        ${p.lead_repo_id ? '✅ 已配置 (ID:' + p.lead_repo_id + ')' : '⚠️ 需配置'}
                    </span>
                    <div style="font-size:10px; color:var(--text-dim); margin-top:4px;">部门: ${p.org_name}</div>
                </td>
                <td style="text-align:center;">${p.repo_count}</td>
            `;
            mdmTbody.appendChild(tr);
        });

        // 3. 渲染待关联仓库
        unlinkedTbody.innerHTML = '';
        if (unlinkedRepos.length === 0) {
            unlinkedTbody.innerHTML = '<tr><td colspan="2" style="color:var(--text-dim); text-align:center;">暂无待关联仓库</td></tr>';
        }
        unlinkedRepos.forEach(r => {
            const tr = document.createElement('tr');

            // 构建主项目下拉选择框 + 是否作为受理中心的勾选
            let selectHtml = `<div style="display:flex; align-items:center; gap:8px;">
                <select id="link-select-${r.id}" style="width:100px;">
                    <option value="">-- 选择 --</option>`;
            mdmProjects.forEach(p => {
                selectHtml += `<option value="${p.project_id}">${p.project_name}</option>`;
            });
            selectHtml += `</select>
                <label style="font-size:10px; display:flex; align-items:center; cursor:pointer;">
                    <input type="checkbox" id="is-lead-${r.id}"> 主
                </label>
                <button class="btn btn-sm" onclick="doLink(${r.id})">OK</button>
            </div>`;

            tr.innerHTML = `
                <td><div style="font-size:11px; font-weight:bold;">${r.name}</div><code style="font-size:9px; opacity:0.6;">${r.path}</code></td>
                <td>${selectHtml}</td>
            `;
            unlinkedTbody.appendChild(tr);
        });

        // 4. 填充 Modal 下拉框
        const orgSelect = document.getElementById('newProjOrg');
        orgSelect.innerHTML = '<option value="">-- 选择归属部门 --</option>';
        orgs.forEach(o => {
            const opt = document.createElement('option');
            opt.value = o.org_id;
            opt.textContent = o.org_name;
            orgSelect.appendChild(opt);
        });

    } catch (e) {
        UI.showToast('加载失败: ' + e.message, 'error');
    }
}

function openCreateProjectModal() {
    document.getElementById('createProjectModal').style.display = 'flex';
}

function closeCreateProjectModal() {
    document.getElementById('createProjectModal').style.display = 'none';
}

async function submitCreateProject() {
    const payload = {
        project_id: document.getElementById('newProjId').value,
        project_name: document.getElementById('newProjName').value,
        org_id: document.getElementById('newProjOrg').value,
        project_type: document.getElementById('newProjType').value,
        plan_start_date: document.getElementById('newProjPlanStart').value || null,
        plan_end_date: document.getElementById('newProjPlanEnd').value || null,
        budget_code: document.getElementById('newProjBudgetCode').value,
        budget_type: document.getElementById('newProjBudgetType').value,
        description: document.getElementById('newProjDesc').value
    };

    if (!payload.project_id || !payload.project_name || !payload.org_id) {
        UI.showToast('请完整填写项目 ID、名称及部门', 'warning');
        return;
    }

    try {
        await Api.request('/admin/mdm-projects', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        UI.showToast('主项目创建成功', 'success');
        closeCreateProjectModal();
        loadAdminProjects();
    } catch (e) {
        UI.showToast('创建失败: ' + e.message, 'error');
    }
}

async function doLink(repoId) {
    const mdmId = document.getElementById(`link-select-${repoId}`).value;
    const isLead = document.getElementById(`is-lead-${repoId}`).checked;
    if (!mdmId) {
        UI.showToast('请选择业务项目', 'warning');
        return;
    }
    await linkRepo(repoId, mdmId, isLead);
}

async function linkRepo(repoId, mdmId, isLead = false) {
    try {
        await Api.request('/admin/link-repo', {
            method: 'POST',
            body: JSON.stringify({
                gitlab_project_id: repoId,
                mdm_project_id: mdmId,
                is_lead: isLead
            })
        });
        UI.showToast('关联成功', 'success');
        loadAdminProjects();
    } catch (e) {
        UI.showToast('关联失败: ' + e.message, 'error');
    }
}

// --- Service Desk: Department Logic ---

async function loadServiceDeskProjects() {
    try {
        const select = document.getElementById('sd-project-select');
        if (!select) return;

        // 修改为拉取业务主项目列表
        const projects = await Api.request('/service-desk/business-projects');
        select.innerHTML = '<option value="">-- 请选择受影响的业务系统 --</option>';
        projects.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id; // MDM Project ID
            opt.textContent = p.name;
            select.appendChild(opt);
        });
    } catch (e) {
        console.error('Failed to load business projects:', e);
    }
}

// --- Admin: Identity Mapping Center ---

async function loadAdminUsers() {
    try {
        const tbody = document.getElementById('userMappingsTableBody');
        tbody.innerHTML = '<tr><td colspan="6">加载中...</td></tr>';

        // 1. 获取所有映射和用户列表
        const mappings = await Api.request('/admin/identity-mappings');
        const users = await Api.request('/admin/users');

        // 2. 渲染表格
        tbody.innerHTML = '';
        if (mappings.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--text-dim);">暂无身份绑定数据</td></tr>';
        }

        mappings.forEach(m => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <div style="font-weight:bold;">${m.user_name}</div>
                    <code style="font-size:10px; opacity:0.6;">${m.global_user_id}</code>
                </td>
                <td><span class="badge">${m.source_system}</span></td>
                <td><code style="color:var(--primary);">${m.external_user_id}</code></td>
                <td>${m.external_username || '-'}</td>
                <td>${m.external_email || '-'}</td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="deleteMapping(${m.id})" style="background:rgba(239, 68, 68, 0.1); color:var(--failed); border:1px solid rgba(239, 68, 68, 0.2);">删除</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        // 3. 填充 Modal 下拉框
        const userSelect = document.getElementById('mapGlobalUser');
        userSelect.innerHTML = '<option value="">-- 选择员工 --</option>';
        users.sort((a, b) => a.full_name.localeCompare(b.full_name)).forEach(u => {
            const opt = document.createElement('option');
            opt.value = u.user_id;
            opt.textContent = `${u.full_name} (${u.email})`;
            userSelect.appendChild(opt);
        });

    } catch (e) {
        UI.showToast('加载失败: ' + e.message, 'error');
    }
}

function openCreateMappingModal() {
    document.getElementById('createMappingModal').style.display = 'flex';
}

function closeCreateMappingModal() {
    document.getElementById('createMappingModal').style.display = 'none';
}

async function submitCreateMapping() {
    const payload = {
        global_user_id: document.getElementById('mapGlobalUser').value,
        source_system: document.getElementById('mapSourceSystem').value,
        external_user_id: document.getElementById('mapExternalId').value,
        external_username: document.getElementById('mapExternalUsername').value || null,
        external_email: document.getElementById('mapExternalEmail').value || null
    };

    if (!payload.global_user_id || !payload.external_user_id) {
        UI.showToast('请选择员工并填写外部 UID', 'warning');
        return;
    }

    try {
        await Api.request('/admin/identity-mappings', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        UI.showToast('身份绑定添加成功', 'success');
        closeCreateMappingModal();
        loadAdminUsers();
    } catch (e) {
        UI.showToast('添加失败: ' + e.message, 'error');
    }
}

async function deleteMapping(id) {
    if (!confirm('确定要删除这条身份映射吗？这可能会影响该员工在活动流中的识别。')) return;
    try {
        await Api.request(`/admin/identity-mappings/${id}`, {
            method: 'DELETE'
        });
        UI.showToast('删除成功', 'success');
        loadAdminUsers();
    } catch (e) {
        UI.showToast('删除失败: ' + e.message, 'error');
    }
}

// --- Admin: Product Architecture Management ---

async function loadAdminProducts() {
    try {
        const productTbody = document.getElementById('productsTableBody');
        const relationTbody = document.getElementById('productProjectTableBody');
        const productSelect = document.getElementById('linkProductSelect');
        const projectSelect = document.getElementById('linkProjectSelect');

        productTbody.innerHTML = '<tr><td colspan="5">加载中...</td></tr>';

        // 1. 并行获取产品、项目和所有关联
        const [products, projects] = await Promise.all([
            Api.request('/admin/products'),
            Api.request('/admin/mdm-projects')
        ]);

        // 2. 渲染产品列表
        productTbody.innerHTML = '';
        productSelect.innerHTML = '<option value="">-- 选择产品 --</option>';
        products.forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <div style="font-weight:bold;">${p.product_name}</div>
                    <code style="font-size:10px; opacity:0.7;">${p.product_code}</code>
                </td>
                <td><span class="badge">${p.category || '通用'}</span></td>
                <td><span class="badge badge-passed">${p.lifecycle_status}</span></td>
                <td>${p.owner_team_id || '-'}</td>
                <td>
                    <button class="btn btn-sm" onclick="alert('编辑功能开发中')">编辑</button>
                </td>
            `;
            productTbody.appendChild(tr);

            const opt = document.createElement('option');
            opt.value = p.product_id;
            opt.textContent = p.product_name;
            productSelect.appendChild(opt);
        });

        // 3. 填充项目下拉框
        projectSelect.innerHTML = '<option value="">-- 选择关联项目 --</option>';
        projects.forEach(proj => {
            const opt = document.createElement('option');
            opt.value = proj.project_id;
            opt.textContent = proj.project_name;
            projectSelect.appendChild(opt);
        });

        // 4. 加载关联关系 (此处假设关联信息需要额外逻辑或已通过项目信息带回)
        // 实际开发中可以通过专门接口：/admin/product-project-relations
        // 这里暂时通过已加载的项目数据解析（如果后端支持的话），或者简单留空。
        relationTbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--text-dim);">请建立新的产品-项目关联</td></tr>';

    } catch (e) {
        UI.showToast('产品数据加载失败: ' + e.message, 'error');
    }
}

async function submitProductProjectLink() {
    const productId = document.getElementById('linkProductSelect').value;
    const projectId = document.getElementById('linkProjectSelect').value;

    if (!productId || !projectId) {
        UI.showToast('请选择产品和项目', 'warning');
        return;
    }

    try {
        await Api.request('/admin/link-product', {
            method: 'POST',
            body: JSON.stringify({
                product_id: productId,
                project_id: projectId,
                relation_type: 'PRIMARY',
                allocation_ratio: 1.0
            })
        });
        UI.showToast('产品与项目关联成功', 'success');
        loadAdminProducts();
    } catch (e) {
        UI.showToast('关联失败: ' + e.message, 'error');
    }
}

function openCreateProductModal() {
    // 简单实现：使用 prompt 或在 index.html 增加 Modal
    UI.showToast('产品新增请通过 SQL 导入或后续 Modal 开发', 'info');
}
