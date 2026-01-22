import { Api, UI } from './sys_core.js';

/**
 * @file sd_admin.js
 * @description Service Desk 后台管理逻辑 (Service Desk Admin Domain)
 */
const SdAdminHandler = {
    state: {
        currentTab: 'pending'
    },

    init() {
        console.log("SD Admin Initialized.");
        this.bindEvents();
        this.load();

        const main = document.getElementById('adminMain');
        if (main) main.classList.remove('u-hide');
    },

    bindEvents() {
        // 选项卡切换
        document.querySelectorAll('.sd-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const target = e.target.closest('.sd-tab');
                if (!target) return;

                document.querySelectorAll('.sd-tab').forEach(t => t.classList.remove('is-active'));
                target.classList.add('is-active');

                const type = target.textContent.trim();
                const map = { '待审批': 'pending', '正式用户': 'approved', '已拒绝': 'rejected', '全部记录': 'all' };
                this.state.currentTab = map[type];
                this.load();
            });
        });

        // 通用按钮委派
        document.addEventListener('click', (e) => {
            const target = e.target;
            if (target.closest('.js-btn-close-reject-modal')) this.closeRejectModal();
            if (target.closest('.js-btn-submit-reject')) this.submitReject();
            if (target.closest('.js-btn-close-approve-modal')) this.closeApproveModal();
            if (target.closest('.js-btn-submit-approve')) this.submitApprove();
        });

        // 列表内按钮委派
        const tbody = document.getElementById('userTableBody');
        if (tbody) {
            tbody.addEventListener('click', (e) => {
                const approveBtn = e.target.closest('.js-action-approve');
                const rejectBtn = e.target.closest('.js-action-reject');
                const row = e.target.closest('tr');
                if (!row) return;
                const email = row.dataset.email;

                if (approveBtn) this.approveWithId(email);
                if (rejectBtn) this.openRejectModal(email);
            });
        }
    },

    async load() {
        const container = document.getElementById('userTableBody');
        if (!container) return;

        container.innerHTML = '';
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 5;
        td.className = 'u-p-40 u-text-center u-text-dim';
        td.textContent = '正在同步全网用户状态...';
        tr.appendChild(td);
        container.appendChild(tr);

        try {
            let url = `/service-desk/admin/all-users`;
            if (this.state.currentTab !== 'all') {
                url += `?status=${this.state.currentTab}`;
            }

            const result = await Api.get(url);
            this.renderStats(result.stats);
            this.renderUsers(result.users);

        } catch (err) {
            container.innerHTML = '';
            const trErr = document.createElement('tr');
            const tdErr = document.createElement('td');
            tdErr.colSpan = 5;
            tdErr.className = 'u-p-40 u-text-center u-text-error';
            tdErr.textContent = `同步失败: ${err.message}`;
            trErr.appendChild(tdErr);
            container.appendChild(trErr);
        }
    },

    renderStats(stats) {
        const row = document.getElementById('statsRow');
        const template = document.getElementById('sd-stat-item-tpl');
        if (!row || !template) return;

        row.innerHTML = '';
        const items = [
            { label: '待审批', value: stats.pending, color: 'u-text-warning' },
            { label: '正式用户', value: stats.approved, color: 'u-text-success' },
            { label: '已拒绝', value: stats.rejected, color: 'u-text-error' },
            { label: '用户总数', value: stats.total, color: '' }
        ];

        items.forEach(item => {
            const clone = template.content.cloneNode(true);
            clone.querySelector('.js-stat-label').textContent = item.label;
            const valEl = clone.querySelector('.js-stat-value');
            valEl.textContent = item.value;
            if (item.color) valEl.classList.add(item.color);
            row.appendChild(clone);
        });
    },

    renderUsers(users) {
        const container = document.getElementById('userTableBody');
        const template = document.getElementById('sd-user-row-tpl');
        if (!container || !template) return;

        container.innerHTML = '';
        if (!users || users.length === 0) {
            container.innerHTML = '<tr><td colspan="5" class="u-p-40 u-text-center u-text-dim">无匹配记录</td></tr>';
            return;
        }

        const fragment = document.createDocumentFragment();
        users.forEach(user => {
            const clone = template.content.cloneNode(true);
            const row = clone.querySelector('tr');
            row.dataset.email = user.email;

            clone.querySelector('.js-user-name').textContent = user.name;
            clone.querySelector('.js-user-email').textContent = user.email;
            clone.querySelector('.js-user-company').textContent = user.company;
            clone.querySelector('.js-user-date').textContent = new Date(user.created_at).toLocaleString();

            const statusBadge = clone.querySelector('.js-user-status-badge');
            const statusMap = { 'pending': '待处理', 'approved': '已通过', 'rejected': '已拒绝' };
            statusBadge.textContent = statusMap[user.status] || user.status;
            statusBadge.className = `sd-badge sd-badge--${user.status}`;

            const gitlabIdEl = clone.querySelector('.js-user-gitlab-id');
            if (user.gitlab_user_id) {
                gitlabIdEl.textContent = `GitLab ID: ${user.gitlab_user_id}`;
            }

            const pendingActions = clone.querySelector('.js-pending-actions');
            const processedInfo = clone.querySelector('.js-processed-info');

            if (user.status === 'pending') {
                pendingActions.classList.remove('u-hide');
            } else {
                processedInfo.classList.remove('u-hide');
                processedInfo.textContent = user.status === 'rejected' ? `理由: ${user.reject_reason || '无'}` : '已通过';
            }

            fragment.appendChild(clone);
        });
        container.appendChild(fragment);
    },

    approveWithId(email) {
        const emailInput = document.getElementById('approveEmail');
        const gitlabIdInput = document.getElementById('approveGitlabId');
        if (emailInput) emailInput.value = email;
        if (gitlabIdInput) gitlabIdInput.value = ''; // Reset
        UI.showModal('approveModal');
    },

    closeApproveModal() {
        UI.hideModal('approveModal');
    },

    async submitApprove() {
        const email = document.getElementById('approveEmail').value;
        const gitlabId = document.getElementById('approveGitlabId').value;

        await this.actionUser(email, true, '', gitlabId);
        this.closeApproveModal();
    },

    openRejectModal(email) {
        const emailInput = document.getElementById('rejectEmail');
        if (emailInput) emailInput.value = email;
        UI.showModal('rejectModal');
    },

    closeRejectModal() {
        UI.hideModal('rejectModal');
    },

    async submitReject() {
        const email = document.getElementById('rejectEmail').value;
        const reason = document.getElementById('rejectReason').value;
        if (!reason) return UI.showToast("请填写拒绝原因", "warning");

        await this.actionUser(email, false, reason);
        this.closeRejectModal();
    },

    async actionUser(email, approved, reason = '', gitlabId = '') {
        UI.toggleLoading("正在同步处理...", true);
        try {
            const params = { email, approved };
            if (reason) params.reject_reason = reason;
            if (gitlabId) params.gitlab_user_id = gitlabId;

            const queryStr = new URLSearchParams(params).toString();
            await Api.post(`/service-desk/admin/approve-user?${queryStr}`, {});
            UI.showToast(approved ? "身份授权完成" : "申请已被驳回", "success");
            this.load();
        } catch (err) {
            UI.showToast(`操作失败: ${err.message}`, "error");
        } finally {
            UI.toggleLoading("", false);
        }
    }
};

export default SdAdminHandler;

document.addEventListener('DOMContentLoaded', () => SdAdminHandler.init());
