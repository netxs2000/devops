import { Api, UI } from './sys_core.js';

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
        initialized: false
    },

    /**
     * 初始化事件监听 (单例注册，确保全局唯一)
     */
    init() {
        if (this.state.initialized) return;

        // 全局委托处理 admin 所有动作
        document.addEventListener('click', (e) => {
            const target = e.target;

            // 1. 打开模态框动作
            if (target.closest('.js-btn-create-product')) {
                UI.showModal('createProductModal');
            }
            if (target.closest('.js-btn-create-project')) {
                UI.showModal('createProjectModal');
            }
            if (target.closest('.js-btn-add-identity-mapping')) {
                this.openMappingModal();
            }

            // 2. 模态框内的取消/关闭动作
            if (target.closest('.js-btn-close-product-modal')) {
                UI.hideModal('createProductModal');
            }
            if (target.closest('.js-btn-close-project-modal')) {
                UI.hideModal('createProjectModal');
            }
            if (target.closest('.js-btn-close-mapping-modal')) {
                UI.hideModal('createMappingModal');
            }

            // 3. 业务提交动作
            if (target.closest('.js-btn-submit-product')) {
                this.submitProduct();
            }
            if (target.closest('.js-btn-submit-project')) {
                this.submitProject();
            }
            if (target.closest('.js-btn-submit-mapping')) {
                this.submitMapping();
            }
            if (target.closest('.js-btn-link-product-project')) {
                this.linkProductProject();
            }
        });

        this.state.initialized = true;
        console.log("AdmManageHandler: Global events bound.");
    },

    /**
     * 【子视图 01】加载产品架构面板
     */
    async loadProducts() {
        this.init();
        UI.toggleLoading("正在同步产品架构...", true);
        try {
            await Promise.all([this.fetchProducts(), this.fetchProjects()]);
            this.renderProductsTable();
            this.renderProductProjectTable();
            this.populateLinkingDropdowns();
        } catch (e) {
            console.error("Failed to load products view", e);
            UI.showToast("架构数据同步失败", "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 【子视图 02】加载项目映射面板
     */
    async loadProjects() {
        this.init();
        UI.toggleLoading("加载项目拓扑...", true);
        try {
            const [mdmProjects, unlinkedRepos] = await Promise.all([
                Api.get('/admin/mdm-projects'),
                Api.get('/admin/unlinked-repos')
            ]);

            // 渲染项目表
            const mdmTbody = document.getElementById('mdmProjectsTableBody');
            const projTpl = document.getElementById('adm-project-row-tpl');
            if (mdmTbody && projTpl) {
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
                    bindEl.innerHTML = p.lead_repo_id ? '<span class="u-text-success">✅ 已绑定</span>' : '<span class="u-text-warning">⚠️ 未绑定</span>';
                    clone.querySelector('.js-proj-repos').textContent = p.repo_count;
                    mdmTbody.appendChild(clone);
                });
            }

            // 渲染未关联仓库
            const unlinkedTbody = document.getElementById('unlinkedReposTableBody');
            const repoTpl = document.getElementById('adm-unlinked-repo-row-tpl');
            if (unlinkedTbody && repoTpl) {
                unlinkedTbody.innerHTML = '';
                unlinkedRepos.forEach(r => {
                    const clone = repoTpl.content.cloneNode(true);
                    clone.querySelector('.js-repo-name').textContent = r.name;
                    const btn = clone.querySelector('.js-repo-link');
                    btn.onclick = () => UI.showToast(`正在准备与主项目关联: ${r.name}`, "info");
                    unlinkedTbody.appendChild(clone);
                });
            }
        } catch (e) {
            UI.showToast("项目数据同步失败", "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 【子视图 03】加载员工身份面板
     */
    async loadUsers() {
        this.init();
        UI.toggleLoading("同步员工身份目录...", true);
        try {
            this.state.mappings = await Api.get('/admin/identity-mappings');
            this.renderUsersTable();
        } catch (e) {
            console.error("Failed to load mappings", e);
            UI.showToast("身份目录同步失败", "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    // --- 数据获取与渲染辅助函数 ---

    async fetchProducts() {
        this.state.products = await Api.get('/admin/products');
    },

    async fetchProjects() {
        this.state.projects = await Api.get('/admin/mdm-projects');
    },

    renderProductsTable() {
        const tbody = document.getElementById('productsTableBody');
        const template = document.getElementById('adm-product-row-tpl');
        if (!tbody || !template) return;
        tbody.innerHTML = '';
        this.state.products.forEach(p => {
            const clone = template.content.cloneNode(true);
            clone.querySelector('.js-prod-name').textContent = p.product_name;
            clone.querySelector('.js-prod-category').textContent = p.category;
            const statusEl = clone.querySelector('.js-prod-status');
            statusEl.textContent = p.lifecycle_status;
            statusEl.className = `adm-badge ${p.lifecycle_status === 'ACTIVE' ? 'adm-badge--active' : 'adm-badge--pending'}`;
            clone.querySelector('.js-prod-owner').textContent = 'Platform Core';
            tbody.appendChild(clone);
        });
    },

    renderProductProjectTable() {
        const tbody = document.getElementById('productProjectTableBody');
        if (!tbody) return;
        tbody.innerHTML = '';
        this.state.projects.forEach(proj => {
            if (proj.products && proj.products.length > 0) {
                proj.products.forEach(rel => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td class="u-p-12">
                            <div class="u-flex-column">
                                <span class="u-weight-600">${proj.project_name}</span>
                                <span class="u-text-tiny u-text-dim">${proj.project_id}</span>
                            </div>
                        </td>
                        <td class="u-p-12 u-text-primary u-weight-500">${rel.product_name}</td>
                        <td class="u-p-12"><span class="adm-badge">${rel.relation_type}</span></td>
                        <td class="u-p-12">100%</td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        });
    },

    renderUsersTable() {
        const tbody = document.getElementById('userMappingsTableBody');
        const template = document.getElementById('adm-user-mapping-row-tpl');
        if (!tbody || !template) return;
        tbody.innerHTML = '';

        if (this.state.mappings.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="u-p-40 u-text-center u-text-dim">暂无身份关联记录</td></tr>';
            return;
        }

        this.state.mappings.forEach(m => {
            const clone = template.content.cloneNode(true);
            clone.querySelector('.js-user-name').textContent = m.user_name || 'System User';
            clone.querySelector('.js-user-source').textContent = m.source_system;
            clone.querySelector('.js-user-ext-id').textContent = m.external_user_id;
            clone.querySelector('.js-user-ext-name').textContent = m.external_username || '-';
            clone.querySelector('.js-user-ext-email').textContent = m.external_email || '-';

            const delBtn = clone.querySelector('.js-user-delete');
            delBtn.onclick = () => this.deleteMapping(m.id);

            tbody.appendChild(clone);
        });
    },

    populateLinkingDropdowns() {
        const prodSelect = document.getElementById('linkProductSelect');
        const projSelect = document.getElementById('linkProjectSelect');
        if (!prodSelect || !projSelect) return;
        prodSelect.innerHTML = '<option value="">选择产品...</option>';
        this.state.products.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.product_id; opt.textContent = p.product_name;
            prodSelect.appendChild(opt);
        });
        projSelect.innerHTML = '<option value="">选择项目...</option>';
        this.state.projects.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.project_id; opt.textContent = p.project_name;
            projSelect.appendChild(opt);
        });
    },

    // --- 业务操作逻辑 ---

    async openMappingModal() {
        UI.showModal('createMappingModal');
        const select = document.getElementById('mappingUserSelect');
        if (!select) return;

        try {
            const users = await Api.get('/admin/users');
            select.innerHTML = '<option value="">请选择内部员工...</option>';
            users.forEach(u => {
                const opt = document.createElement('option');
                opt.value = u.user_id;
                opt.textContent = `${u.full_name} (${u.email})`;
                select.appendChild(opt);
            });
        } catch (e) {
            UI.showToast("员工列表加载失败", "error");
        }
    },

    async submitMapping() {
        const globalUserId = document.getElementById('mappingUserSelect').value;
        const sourceSystem = document.getElementById('mappingSourceSystem').value;
        const externalUserId = document.getElementById('mappingExtId').value;

        if (!globalUserId || !externalUserId) return UI.showToast("请填写完整映射信息", "warning");

        try {
            await Api.post('/admin/identity-mappings', {
                global_user_id: globalUserId,
                source_system: sourceSystem,
                external_user_id: externalUserId
            });
            UI.showToast("身份映射已建立", "success");
            UI.hideModal('createMappingModal');
            this.loadUsers();
        } catch (e) {
            UI.showToast(`绑定失败: ${e.message}`, "error");
        }
    },

    async deleteMapping(id) {
        if (!confirm("确定要解除此身份绑定吗？")) return;
        try {
            await Api.request(`/admin/identity-mappings/${id}`, { method: 'DELETE' });
            UI.showToast("绑定已解除", "success");
            this.loadUsers();
        } catch (e) {
            UI.showToast("操作失败", "error");
        }
    },

    async submitProduct() {
        const pName = document.getElementById('prodName').value;
        const pId = document.getElementById('prodId').value;
        const pCat = document.getElementById('prodCategory').value;
        if (!pName || !pId) return UI.showToast("请填写完整信息", "warning");

        try {
            await Api.post('/admin/products', {
                product_id: pId, product_code: pId, product_name: pName,
                product_description: 'Architecture Definition', category: pCat, lifecycle_status: 'ACTIVE'
            });
            UI.showToast("产品已上线", "success");
            UI.hideModal('createProductModal');
            this.loadProducts();
        } catch (e) {
            UI.showToast("同步失败", "error");
        }
    },

    async submitProject() {
        const pName = document.getElementById('newProjName').value;
        const pId = document.getElementById('newProjId').value;
        if (!pName || !pId) return UI.showToast("信息不全", "warning");

        try {
            await Api.post('/admin/mdm-projects', {
                project_id: pId, project_name: pName, org_id: 'GZ_CENTER',
                project_type: document.getElementById('newProjType').value
            });
            UI.showToast("项目已注册", "success");
            UI.hideModal('createProjectModal');
            this.loadProjects();
        } catch (e) {
            UI.showToast("注册失败", "error");
        }
    },

    async linkProductProject() {
        const prodId = document.getElementById('linkProductSelect').value;
        const projId = document.getElementById('linkProjectSelect').value;
        if (!prodId || !projId) return UI.showToast("请选择目标", "warning");

        try {
            await Api.post('/admin/link-product', { product_id: prodId, project_id: projId });
            UI.showToast("关联已建立", "success");
            this.loadProducts();
        } catch (e) {
            UI.showToast("关联失败", "error");
        }
    }
};

export default AdmManageHandler;
