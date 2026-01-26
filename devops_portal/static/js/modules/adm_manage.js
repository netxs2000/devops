import { Api, UI } from './sys_core.js';
import { AdmService } from './adm_service.js';

/**
 * @file adm_manage.js
 * @description 管理后台核心逻辑 (Administration Domain) - Apple Style Edition
 */
const AdmManageHandler = {
    /**
     * 内部状态
     */
    state: {
        products: [],
        projects: [],
        mappings: [],
        registrations: [],
        currentRegTab: 'pending',
        initialized: false
    },

    /**
     * 初始化事件监听
     */
    init() {
        if (this.state.initialized) return;

        // 全局委托处理所有 admin 动作
        document.addEventListener('click', (e) => {
            const target = e.target;

            // 1. 打开模态框
            if (target.closest('.js-btn-create-product')) UI.showModal('createProductModal');
            if (target.closest('.js-btn-create-project')) UI.showModal('createProjectModal');
            if (target.closest('.js-btn-add-identity-mapping')) this.openMappingModal();

            // 2. 关闭模态框
            if (target.closest('.js-btn-close-product-modal')) UI.hideModal('createProductModal');
            if (target.closest('.js-btn-close-project-modal')) UI.hideModal('createProjectModal');
            if (target.closest('.js-btn-close-mapping-modal')) UI.hideModal('createMappingModal');
            if (target.closest('.js-btn-close-reject-modal')) UI.hideModal('rejectModal');
            if (target.closest('.js-btn-close-approve-modal')) UI.hideModal('approveModal');

            // 3. 提交动作
            if (target.closest('.js-btn-submit-product')) this.submitProduct();
            if (target.closest('.js-btn-submit-project')) this.submitProject();
            if (target.closest('.js-btn-submit-mapping')) this.submitMapping();
            if (target.closest('.js-btn-link-product-project')) this.linkProductProject();
            if (target.closest('.js-btn-submit-reject')) this.submitReject();
            if (target.closest('.js-btn-submit-approve')) this.submitApprove();

            // 4. 列表项删除
            if (target.closest('.js-user-delete')) {
                const mappingId = target.closest('[data-mapping-id]')?.dataset.mappingId;
                if (mappingId) this.deleteMapping(mappingId);
            }

            // 5. 审批页选项卡
            const tab = target.closest('.js-adm-reg-tab');
            if (tab) {
                document.querySelectorAll('.js-adm-reg-tab').forEach(t => t.classList.remove('is-active'));
                tab.classList.add('is-active');
                this.state.currentRegTab = tab.dataset.status;
                this.loadApprovals();
            }
        });

        // 监听组件事件 (CustomEvent Bubbling)
        document.addEventListener('action', (e) => {
            if (e.detail.action === 'approve') this.openApproveModal(e.detail.email);
            if (e.detail.action === 'reject') this.openRejectModal(e.detail.email);
        });

        this.state.initialized = true;
        console.log("AdmManageHandler: Standardized for Apple Style.");
    },

    /**
     * 【子视图 01】产品体系
     */
    async loadProducts() {
        this.init();
        UI.toggleLoading("同步产品架构...", true);
        try {
            const [prods, projs] = await Promise.all([AdmService.getProducts(), AdmService.getMdmProjects()]);
            this.state.products = prods;
            this.state.projects = projs;
            this.renderProductsGrid();
            this.renderProductProjectTable();
            this.populateLinkingDropdowns();
        } catch (e) {
            UI.showToast("架构同步失败", "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 【子视图 02】项目映射
     */
    async loadProjects() {
        this.init();
        UI.toggleLoading("加载项目拓扑...", true);
        try {
            const [mdmProjects, unlinkedRepos] = await Promise.all([
                AdmService.getMdmProjects(),
                AdmService.getUnlinkedRepos()
            ]);
            this.renderMdmProjectsGrid(mdmProjects);
            this.renderUnlinkedReposTable(unlinkedRepos);
        } catch (e) {
            UI.showToast("拓扑同步失败", "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 【子视图 03】身份目录
     */
    async loadUsers() {
        this.init();
        UI.toggleLoading("同步身份目录...", true);
        try {
            this.state.mappings = await AdmService.getIdentityMappings();
            this.renderUsersTable();
        } catch (e) {
            UI.showToast("目录同步失败", "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 【子视图 04】注册审批 (NEW Native View)
     */
    async loadApprovals() {
        this.init();
        UI.toggleLoading("同步审批中心...", true);
        try {
            const result = await AdmService.getRegistrationUsers(this.state.currentRegTab);
            this.renderRegStats(result.stats);
            this.renderRegList(result.users);
        } catch (e) {
            UI.showToast("获取申请列表失败", "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    // --- 渲染逻辑 (Rendering) ---

    renderProductsGrid() {
        const container = document.querySelector('.js-products-grid');
        if (!container) return;
        container.innerHTML = '';
        this.state.products.forEach(p => {
            const card = document.createElement('adm-product-card');
            card.setAttribute('name', p.product_name);
            card.setAttribute('category', p.category || '核心业务');
            card.setAttribute('status', p.lifecycle_status);
            card.setAttribute('id', p.product_id);
            container.appendChild(card);
        });
    },

    renderMdmProjectsGrid(projects) {
        const container = document.querySelector('.js-mdm-projects-grid');
        if (!container) return;
        container.innerHTML = '';
        projects.forEach(p => {
            const card = document.createElement('adm-project-card');
            card.setAttribute('name', p.project_name);
            card.setAttribute('id', p.project_id);
            card.setAttribute('type', p.project_type);
            card.setAttribute('status', p.status);
            card.setAttribute('binding', !!p.lead_repo_id);
            card.setAttribute('repos', p.repo_count);
            container.appendChild(card);
        });
    },

    renderUnlinkedReposTable(repos) {
        const tbody = document.querySelector('.js-unlinked-repos-tbody');
        if (!tbody) return;
        tbody.innerHTML = repos.map(r => `
            <tr>
                <td class="u-p-12">${r.name}</td>
                <td><button class="btn-primary btn--small" onclick="UI.showToast('Preparing link...', 'info')">指派</button></td>
            </tr>
        `).join('') || '<tr><td colspan="2" class="u-p-20 u-text-dim u-text-center">所有仓库均已关联完毕</td></tr>';
    },

    renderUsersTable() {
        const tbody = document.querySelector('.js-user-mappings-tbody');
        if (!tbody) return;
        tbody.innerHTML = this.state.mappings.map(m => `
            <tr data-mapping-id="${m.id}">
                <td><span class="u-weight-600 u-text-primary">${m.user_name || 'Sys User'}</span></td>
                <td><span class="adm-badge sys-tag--admin">${m.source_system}</span></td>
                <td><code>${m.external_user_id}</code></td>
                <td>${m.external_username || '-'}</td>
                <td>${m.external_email || '-'}</td>
                <td><button class="btn-ghost btn--small u-text-error js-user-delete">解除</button></td>
            </tr>
        `).join('') || '<tr><td colspan="6" class="u-p-40 u-text-center u-text-dim">暂无身份关联记录</td></tr>';
    },

    renderProductProjectTable() {
        const tbody = document.querySelector('.js-product-project-tbody');
        if (!tbody) return;
        let html = '';
        this.state.projects.forEach(proj => {
            if (proj.products) proj.products.forEach(rel => {
                html += `
                    <tr>
                        <td class="u-p-12"><div class="u-flex-column"><span class="u-weight-600">${proj.project_name}</span><span class="u-text-tiny u-text-dim">${proj.project_id}</span></div></td>
                        <td class="u-p-12 u-text-primary">${rel.product_name}</td>
                        <td class="u-p-12"><span class="adm-badge">${rel.relation_type}</span></td>
                        <td class="u-p-12">100%</td>
                    </tr>`;
            });
        });
        tbody.innerHTML = html || '<tr><td colspan="4" class="u-p-20 u-text-center u-text-dim">暂无关联映射</td></tr>';
    },

    renderRegStats(stats) {
        const container = document.querySelector('.js-adm-reg-stats');
        if (!container) return;
        container.innerHTML = `
            <div class="g-card u-text-center"><span class="u-block u-text-dim u-text-tiny">待处理</span><div class="u-text-h2 u-text-warning">${stats.pending}</div></div>
            <div class="g-card u-text-center"><span class="u-block u-text-dim u-text-tiny">正式用户</span><div class="u-text-h2 u-text-success">${stats.approved}</div></div>
            <div class="g-card u-text-center"><span class="u-block u-text-dim u-text-tiny">已拒绝</span><div class="u-text-h2 u-text-error">${stats.rejected}</div></div>
            <div class="g-card u-text-center"><span class="u-block u-text-dim u-text-tiny">库内总量</span><div class="u-text-h2">${stats.total}</div></div>
        `;
    },

    renderRegList(users) {
        const container = document.querySelector('.js-adm-reg-list');
        if (!container) return;
        container.innerHTML = '';
        users.forEach(u => {
            const card = document.createElement('adm-registration-card');
            card.setAttribute('name', u.name);
            card.setAttribute('email', u.email);
            card.setAttribute('company', u.company);
            card.setAttribute('date', new Date(u.created_at).toLocaleDateString());
            card.setAttribute('status', u.status);
            if (u.gitlab_user_id) card.setAttribute('gitlab-id', u.gitlab_user_id);
            container.appendChild(card);
        });
    },

    // --- 业务操作逻辑 (Logic) ---

    async openMappingModal() {
        UI.showModal('createMappingModal');
        const select = document.querySelector('.js-mapping-user-select');
        if (!select) return;
        try {
            const users = await AdmService.getUsers();
            select.innerHTML = users.map(u => `<option value="${u.user_id}">${u.full_name} (${u.email})</option>`).join('');
        } catch (e) { UI.showToast("无法加载用户列表", "error"); }
    },

    async submitMapping() {
        const body = {
            global_user_id: document.querySelector('.js-mapping-user-select').value,
            source_system: document.querySelector('.js-mapping-source-system').value,
            external_user_id: document.querySelector('.js-mapping-ext-id').value
        };
        try {
            await AdmService.createIdentityMapping(body);
            UI.showToast("绑定成功", "success");
            UI.hideModal('createMappingModal');
            this.loadUsers();
        } catch (e) { UI.showToast("绑定异常", "error"); }
    },

    async deleteMapping(id) {
        if (!confirm("确定解除？")) return;
        try {
            await AdmService.deleteIdentityMapping(id);
            this.loadUsers();
        } catch (e) { UI.showToast("删除失败", "error"); }
    },

    openApproveModal(email) {
        document.getElementById('approveEmail').value = email;
        UI.showModal('approveModal');
    },

    openRejectModal(email) {
        document.getElementById('rejectEmail').value = email;
        UI.showModal('rejectModal');
    },

    async submitApprove() {
        const email = document.getElementById('approveEmail').value;
        const glId = document.getElementById('approveGitlabId').value;
        try {
            await AdmService.approveUser(email, true, '', glId);
            UI.showToast("权限已授出", "success");
            UI.hideModal('approveModal');
            this.loadApprovals();
        } catch (e) { UI.showToast("授权异常", "error"); }
    },

    async submitReject() {
        const email = document.getElementById('rejectEmail').value;
        const reason = document.getElementById('rejectReason').value;
        if (!reason) return UI.showToast("理由必填", "warning");
        try {
            await AdmService.approveUser(email, false, reason);
            UI.showToast("已拒绝申请", "success");
            UI.hideModal('rejectModal');
            this.loadApprovals();
        } catch (e) { UI.showToast("拒绝操作异常", "error"); }
    },

    populateLinkingDropdowns() {
        const prodS = document.querySelector('.js-link-product-select');
        const projS = document.querySelector('.js-link-project-select');
        if (prodS && projS) {
            prodS.innerHTML = this.state.products.map(p => `<option value="${p.product_id}">${p.product_name}</option>`).join('');
            projS.innerHTML = this.state.projects.map(p => `<option value="${p.project_id}">${p.project_name}</option>`).join('');
        }
    },

    async submitProduct() {
        const body = {
            product_id: document.querySelector('.js-prod-id-input').value,
            product_name: document.querySelector('.js-prod-name-input').value,
            category: document.querySelector('.js-prod-category-select').value,
            lifecycle_status: 'ACTIVE'
        };
        try {
            await AdmService.createProduct(body);
            UI.showToast("产品上线", "success");
            UI.hideModal('createProductModal');
            this.loadProducts();
        } catch (e) { UI.showToast("操作失败", "error"); }
    },

    async submitProject() {
        const body = {
            project_id: document.querySelector('.js-new-proj-id-input').value,
            project_name: document.querySelector('.js-new-proj-name-input').value,
            project_type: document.querySelector('.js-new-proj-type-select').value,
            org_id: 'GZ_CENTER'
        };
        try {
            await AdmService.createMdmProject(body);
            UI.showToast("项目注册成功", "success");
            UI.hideModal('createProjectModal');
            this.loadProjects();
        } catch (e) { UI.showToast("注册失败", "error"); }
    },

    async linkProductProject() {
        const body = {
            product_id: document.querySelector('.js-link-product-select').value,
            project_id: document.querySelector('.js-link-project-select').value
        };
        try {
            await AdmService.linkProductProject(body);
            UI.showToast("关联成功", "success");
            this.loadProducts();
        } catch (e) { UI.showToast("关联异常", "error"); }
    }
};

export default AdmManageHandler;
