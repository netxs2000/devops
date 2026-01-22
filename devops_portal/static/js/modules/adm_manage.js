import { Api, UI } from './sys_core.js';

const AdmManageHandler = {
    /**
     * 初始化
     */
    init() {
        const adminViews = ['adm-projects-view', 'adm-products-view', 'adm-users-view'];
        adminViews.forEach(id => {
            const el = document.getElementById(id);
            if (el && !el.dataset.initialized) {
                el.addEventListener('click', (e) => {
                    const target = e.target;
                    // 绑定各视图内的全局动作
                    if (target.closest('.js-btn-create-project')) UI.showModal('createProjectModal');
                    if (target.closest('.js-btn-create-product')) UI.showModal('createProductModal');
                    if (target.closest('.js-btn-add-identity-mapping')) this.openMappingModal();
                    if (target.closest('.js-btn-link-product-project')) this.linkProductProject();
                });
                el.dataset.initialized = "true";
            }
        });

        // 统一处理模态框内的按钮
        document.addEventListener('click', (e) => {
            const target = e.target;
            if (target.closest('.js-btn-close-mapping-modal')) UI.hideModal('createMappingModal');
            if (target.closest('.js-btn-submit-mapping')) this.submitMapping();
            if (target.closest('.js-btn-close-project-modal')) UI.hideModal('createProjectModal');
            if (target.closest('.js-btn-submit-project')) this.submitProject();
        });
    },

    /**
     * 加载产品列表
     */
    async loadProducts() {
        this.init();
        try {
            const tbody = document.getElementById('productsTableBody');
            if (!tbody) return;

            const products = await Api.get('/admin/products');
            const template = document.getElementById('adm-product-row-tpl');

            tbody.innerHTML = '';
            products.forEach(p => {
                const clone = template.content.cloneNode(true);
                clone.querySelector('.js-prod-name').textContent = p.product_name;
                clone.querySelector('.js-prod-category').textContent = p.category;
                clone.querySelector('.js-prod-status').textContent = p.lifecycle_status;
                clone.querySelector('.js-prod-owner').textContent = p.owner_team_id;

                tbody.appendChild(clone);
            });
        } catch (e) {
            console.error("Failed to load products", e);
            UI.showToast("加载产品列表失败", "error");
        }
    },

    /**
     * 加载项目及仓库映射
     */
    async loadProjects() {
        this.init();
        try {
            const mdmTbody = document.getElementById('mdmProjectsTableBody');
            const unlinkedTbody = document.getElementById('unlinkedReposTableBody');
            if (!mdmTbody || !unlinkedTbody) return;

            const mdmProjects = await Api.get('/admin/mdm-projects');
            const unlinkedRepos = await Api.get('/admin/unlinked-repos');

            const projTpl = document.getElementById('adm-project-row-tpl');
            const repoTpl = document.getElementById('adm-unlinked-repo-row-tpl');

            mdmTbody.innerHTML = '';
            mdmProjects.forEach(p => {
                const clone = projTpl.content.cloneNode(true);
                clone.querySelector('.js-proj-name').textContent = p.project_name;
                clone.querySelector('.js-proj-id').textContent = p.project_id;
                clone.querySelector('.js-proj-type').textContent = p.project_type;

                const statusEl = clone.querySelector('.js-proj-status');
                statusEl.textContent = p.status;
                statusEl.className = `adm-badge ${p.status === 'RELEASED' ? 'adm-badge--active' : 'adm-badge--pending'}`;

                const bindEl = clone.querySelector('.js-proj-binding');
                if (p.lead_repo_id) {
                    bindEl.textContent = '✅ 已绑定';
                    bindEl.className = 'u-text-success u-weight-600';
                } else {
                    bindEl.textContent = '⚠️ 未绑定';
                    bindEl.className = 'u-text-warning u-weight-600';
                }

                clone.querySelector('.js-proj-repos').textContent = p.repo_count;
                mdmTbody.appendChild(clone);
            });

            unlinkedTbody.innerHTML = '';
            unlinkedRepos.forEach(r => {
                const clone = repoTpl.content.cloneNode(true);
                clone.querySelector('.js-repo-name').textContent = r.name;
                const linkBtn = clone.querySelector('.js-repo-link');
                linkBtn.addEventListener('click', () => this.doLink(r.id));

                unlinkedTbody.appendChild(clone);
            });
        } catch (e) {
            console.error("Failed to load projects", e);
            UI.showToast("加载项目关联失败", "error");
        }
    },

    /**
     * 加载用户身份映射
     */
    async loadUsers() {
        this.init();
        try {
            const tbody = document.getElementById('userMappingsTableBody');
            if (!tbody) return;

            const mappings = await Api.get('/admin/identity-mappings');
            const template = document.getElementById('adm-user-mapping-row-tpl');

            tbody.innerHTML = '';
            mappings.forEach(m => {
                const clone = template.content.cloneNode(true);
                clone.querySelector('.js-user-name').textContent = m.user_name;
                clone.querySelector('.js-user-source').textContent = m.source_system;
                clone.querySelector('.js-user-ext-id').textContent = m.external_user_id;
                clone.querySelector('.js-user-ext-name').textContent = m.external_username || '-';
                clone.querySelector('.js-user-ext-email').textContent = m.external_email || '-';

                const delBtn = clone.querySelector('.js-user-delete');
                delBtn.addEventListener('click', () => this.deleteMapping(m.id));

                tbody.appendChild(clone);
            });
        } catch (e) {
            console.error("Failed to load users", e);
            UI.showToast("加载用户映射失败", "error");
        }
    },

    async openMappingModal() {
        UI.showToast("Mapping modal initialized", "info");
        UI.showModal('createMappingModal');
    },

    async submitMapping() {
        UI.showToast("Mapping saved (Simulated)", "success");
        UI.hideModal('createMappingModal');
    },

    async submitProject() {
        UI.showToast("Project created (Simulated)", "success");
        UI.hideModal('createProjectModal');
    },

    async linkProductProject() {
        UI.showToast("Product association linked (Simulated)", "success");
    },

    async doLink(id) {
        UI.showToast(`正在申请关联仓库 ID: ${id} ...`, "info");
    },

    async deleteMapping(id) {
        if (confirm("确定要删除此身份映射吗？")) {
            UI.showToast(`删除映射 ID: ${id}`, "warning");
        }
    }
};

export default AdmManageHandler;
