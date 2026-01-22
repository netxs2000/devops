import { Api, UI } from './sys_core.js';
import QaDefectHandler from './qa_defects.js';
import PmRequirementHandler from './pm_requirements.js';


/**
 * Service Desk UI 处理器
 */
const SdServiceDeskHandler = {
    /**
     * 初始化事件监听 (事件委派)
     */
    init() {
        const list = document.getElementById('servicedesk-list');
        if (!list || list.dataset.initialized) return;

        list.addEventListener('click', (e) => {
            const btn = e.target.closest('button');
            if (!btn) return;

            const row = btn.closest('.js-ticket-row');
            if (!row) return;

            const ticketId = row.dataset.iid;
            const projectId = row.dataset.projectId;
            const title = row.dataset.title;

            if (btn.classList.contains('js-action-defect')) {
                this.convertToProfessionalBug(ticketId, title);
            } else if (btn.classList.contains('js-action-req')) {
                this.convertToProfessionalReq(ticketId, title);
            } else if (btn.classList.contains('js-action-reject')) {
                this.rejectTicket(ticketId, projectId);
            } else if (btn.classList.contains('js-action-ai-rca')) {
                this.openRCAAssistant(ticketId, projectId);
            }
        });

        list.dataset.initialized = "true";
    },

    /**
     * 加载并渲染工单列表
     */
    async loadTickets() {
        const list = document.getElementById('servicedesk-list');
        if (!list) return;

        // 初始化委派
        this.init();

        // Loading 状态渲染 (安全方式)
        list.innerHTML = '';
        const loader = document.createElement('div');
        loader.className = 'u-p-20 u-text-primary';
        loader.textContent = 'Synchronizing with business portal...';
        list.appendChild(loader);

        try {
            const tickets = await Api.get(`/service-desk/tickets`);
            list.innerHTML = '';

            if (tickets.length === 0) {
                const empty = document.createElement('div');
                empty.className = 'u-p-40 u-text-center u-opacity-60';
                empty.textContent = 'No pending business feedback.';
                list.appendChild(empty);
                return;
            }

            const template = document.getElementById('sd-ticket-tpl');
            const fragment = document.createDocumentFragment();

            tickets.forEach(t => {
                const clone = template.content.cloneNode(true);
                const row = clone.querySelector('.js-ticket-row');

                // 存储元数据以供事件委派使用
                row.dataset.iid = t.iid;
                row.dataset.projectId = t.project_id;
                row.dataset.title = t.title;

                // 安全填充内容
                clone.querySelector('.js-ticket-iid').textContent = `#${t.iid}`;
                clone.querySelector('.js-ticket-title').textContent = t.title;

                const reporter = t.requester_email ? t.requester_email.split('@')[0] : 'Unknown';
                clone.querySelector('.js-ticket-meta').textContent = `From: ${reporter} | Created: ${t.created_at}`;

                fragment.appendChild(clone);
            });

            list.appendChild(fragment);

        } catch (e) {
            list.innerHTML = '';
            const errorDiv = document.createElement('div');
            errorDiv.className = 'u-p-20 u-text-error';
            errorDiv.textContent = `Error: ${e.message}`;
            list.appendChild(errorDiv);
        }
    },

    /**
     * 驳回工单
     */
    async rejectTicket(iid, projectId) {
        const reason = prompt("Select reason for rejection:\n1. Invalid Data\n2. Works as Intended\n3. Out of Scope\n\nOr type custom reason:");
        if (!reason) return;

        UI.toggleLoading("Closing feedback...", true);

        try {
            await Api.post(`/service-desk/tickets/${iid}/reject`, { project_id: projectId, reason: reason });
            UI.showToast(`Ticket #${iid} has been dismissed.`, "success");
            this.loadTickets();
        } catch (e) {
            alert(e.message);
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 转入缺陷
     */
    convertToProfessionalBug(iid, title) {
        QaDefectHandler.initCreateForm(iid);

        const titleInput = document.getElementById('quick-bug-title');
        const stepsInput = document.getElementById('bug_steps');

        // 覆盖为工单特定内容
        if (titleInput) titleInput.value = `[Bug Transferred] ${title}`;
        if (stepsInput) stepsInput.value = `Reference Ticket: #${iid}\n\n---\nSteps:`;

        if (window.sys_switchView) window.sys_switchView('test-cases');
    },

    /**
     * 转入需求
     */
    convertToProfessionalReq(iid, title) {
        PmRequirementHandler.openModal();

        const reqTitle = document.getElementById('req_title');
        const reqValue = document.getElementById('req_value');

        if (reqTitle) reqTitle.value = `[Req Transferred] ${title}`;
        if (reqValue) reqValue.value = `Origin User Request: #${iid}\n\nPlease refine business goals here.`;

        if (window.sys_switchView) window.sys_switchView('requirements');
    },

    /**
     * AI RCA 助手
     */
    async openRCAAssistant(iid, projectId) {
        QaDefectHandler.openRCA(iid, projectId);
    }
};

export default SdServiceDeskHandler;
