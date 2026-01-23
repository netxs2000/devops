/**
 * @file sd-portal.js
 * @description Service Desk Portal 业务层 (Visitor Facing)
 * @author Antigravity
 */

import { Auth, Api, NotificationSystem } from './sys_core.js';

const SDPortalHandler = {
    /**
     * 初始化页面的通用逻辑
     */
    async init() {
        console.log("SD Portal Initialized.");
        this.updateNavigation();

        // 根据页面特有元素触发逻辑
        if (document.getElementById('totalTickets')) {
            this.loadStats();
        }

        if (document.getElementById('bugForm')) {
            this.initBugForm();
        }

        if (document.getElementById('requirementForm')) {
            this.initRequirementForm();
        }

        if (document.getElementById('searchForm')) {
            this.initTrackForm();
        }

        if (document.getElementById('myTicketsList')) {
            this.loadMyTickets();
        }
    },

    /**
     * 更新导航栏状态
     */
    updateNavigation() {
        const nav = document.querySelector('.nav-links');
        if (!nav) return;

        const isLoggedIn = Auth.isLoggedIn();

        // 清空现有导航并重新构建 (安全方式)
        while (nav.firstChild) nav.removeChild(nav.firstChild);

        const createLink = (text, href, onClick) => {
            const a = document.createElement('a');
            a.className = 'sd-nav-link';
            a.textContent = text;
            a.href = href;
            if (onClick) {
                a.addEventListener('click', (e) => {
                    e.preventDefault();
                    onClick(e);
                });
            }
            return a;
        };

        nav.appendChild(createLink('返回主页', '/'));

        if (isLoggedIn) {
            nav.appendChild(createLink('我的工单', 'service_desk_my_tickets.html'));
            nav.appendChild(createLink('退出', '#', (e) => {
                Auth.logout();
                localStorage.removeItem('sd_token');
                localStorage.removeItem('sd_email');
                localStorage.removeItem('sd_user');
                window.location.reload();
            }));
        } else {
            nav.appendChild(createLink('登录', 'service_desk_login.html'));
            nav.appendChild(createLink('注册', 'service_desk_register.html'));
        }
    },

    /**
     * 加载统计数据 (Landing Page)
     */
    async loadStats() {
        try {
            const tickets = await Api.get('/service-desk/tickets');

            const totalEl = document.getElementById('totalTickets');
            const pendingEl = document.getElementById('pendingTickets');
            const completedEl = document.getElementById('completedTickets');

            if (totalEl) totalEl.textContent = tickets.length;
            if (pendingEl) {
                const pending = tickets.filter(t => t.status === 'pending' || t.status === 'in-progress').length;
                pendingEl.textContent = pending;
            }
            if (completedEl) {
                const completed = tickets.filter(t => t.status === 'completed').length;
                completedEl.textContent = completed;
            }
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    },

    /**
     * 初始化缺陷提交表单
     */
    async initBugForm() {
        const form = document.getElementById('bugForm');
        if (!form) return;

        // 加载用户信息
        const user = await Auth.getCurrentUser();
        if (user) {
            const reporterSection = document.getElementById('reporterSection');
            const reporterName = document.getElementById('reporterName');
            const reporterAvatar = document.getElementById('reporterAvatar');

            if (reporterSection) {
                reporterSection.classList.remove('u-hide');
                reporterSection.classList.add('u-flex');
            }
            if (reporterName) reporterName.textContent = `${user.full_name || user.username} (${user.organization_name || 'Individual'})`;
            if (reporterAvatar) reporterAvatar.textContent = (user.full_name || user.username).charAt(0).toUpperCase();
        }

        // 加载项目列表
        await this.loadBusinessProjects('mdmId');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            this.handleSubmission(form, 'bug');
        });

        // 文件上传处理
        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        }

        const uploadArea = document.getElementById('uploadArea');
        if (uploadArea) {
            uploadArea.addEventListener('click', () => fileInput.click());
        }
    },

    /**
     * 初始化需求提交表单
     */
    async initRequirementForm() {
        const form = document.getElementById('requirementForm');
        if (!form) return;

        const user = await Auth.getCurrentUser();
        if (user) {
            const reporterSection = document.getElementById('reporterSection');
            if (reporterSection) {
                reporterSection.classList.remove('u-hide');
                reporterSection.classList.add('u-flex');
            }
            const reporterName = document.getElementById('reporterName');
            if (reporterName) reporterName.textContent = `${user.full_name || user.username} (${user.organization_name || 'Individual'})`;
            const reporterAvatar = document.getElementById('reporterAvatar');
            if (reporterAvatar) reporterAvatar.textContent = (user.full_name || user.username).charAt(0).toUpperCase();
        }

        await this.loadBusinessProjects('mdmId');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            this.handleSubmission(form, 'requirement');
        });

        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        }

        const uploadArea = document.getElementById('uploadArea');
        if (uploadArea) {
            uploadArea.addEventListener('click', () => fileInput.click());
        }
    },

    /**
     * 加载业务项目列表
     */
    async loadBusinessProjects(selectId) {
        const select = document.getElementById(selectId);
        if (!select) return;

        try {
            const projects = await Api.get('/service-desk/business-projects');
            while (select.firstChild) select.removeChild(select.firstChild);

            const defOpt = document.createElement('option');
            defOpt.value = '';
            defOpt.textContent = '-- 请选择业务系统 --';
            select.appendChild(defOpt);

            projects.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = p.name;
                select.appendChild(opt);
            });
        } catch (e) {
            select.innerHTML = '';
            const opt = document.createElement('option');
            opt.value = "";
            opt.textContent = "加载失败，请刷新";
            select.appendChild(opt);
        }
    },

    /**
     * 处理文件上传
     */
    uploadedAttachments: [],
    async handleFileUpload(event) {
        const files = event.target.files;
        const mdmId = document.getElementById('mdmId').value;
        const preview = document.getElementById('filePreview');

        if (!mdmId) {
            alert('请先选择业务系统，以便我们将附件归档。');
            return;
        }

        for (const file of files) {
            const previewItem = document.createElement('div');
            previewItem.className = 'upload-preview-item';

            const loading = document.createElement('div');
            loading.className = 'loading u-mx-auto u-mt-10 u-mb-10 u-square-16';

            const fileName = document.createElement('div');
            fileName.className = 'u-text-caption u-truncate';
            fileName.textContent = file.name;

            previewItem.appendChild(loading);
            previewItem.appendChild(fileName);
            preview.appendChild(previewItem);

            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch(`/service-desk/upload?mdm_id=${mdmId}`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${Auth.getToken()}` },
                    body: formData
                });
                const result = await response.json();

                if (result.markdown) {
                    this.uploadedAttachments.push(result.markdown);
                    previewItem.textContent = '';

                    const icon = document.createElement('div');
                    icon.className = 'u-text-h1';
                    icon.textContent = 'F';

                    const status = document.createElement('div');
                    status.className = 'u-text-success u-text-caption';
                    status.textContent = '已准备';

                    previewItem.appendChild(icon);
                    previewItem.appendChild(fileName.cloneNode(true));
                    previewItem.appendChild(status);
                }
            } catch (error) {
                previewItem.innerHTML = '';
                const errMark = document.createElement('div');
                errMark.className = 'u-text-error';
                errMark.textContent = 'x';
                const errLabel = document.createElement('div');
                errLabel.className = 'u-text-caption';
                errLabel.textContent = '失败';
                previewItem.appendChild(errMark);
                previewItem.appendChild(errLabel);
            }
        }
    },

    /**
     * 通用提交逻辑
     */
    async handleSubmission(form, type) {
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        const mdmId = document.getElementById('mdmId').value;

        submitBtn.disabled = true;
        submitBtn.textContent = '提交中...';

        const formData = {
            title: document.getElementById('title').value.trim(),
            attachments: this.uploadedAttachments
        };

        if (type === 'bug') {
            Object.assign(formData, {
                severity: document.getElementById('severity').value,
                priority: document.getElementById('priority').value,
                province: document.getElementById('province').value.trim(),
                environment: document.getElementById('environment').value,
                steps_to_repro: document.getElementById('stepsToRepro').value.trim(),
                actual_result: document.getElementById('actualResult').value.trim(),
                expected_result: document.getElementById('expectedResult').value.trim(),
            });
        } else {
            Object.assign(formData, {
                description: document.getElementById('description').value.trim(),
                req_type: document.getElementById('reqType').value,
                priority: document.getElementById('priority').value,
                province: document.getElementById('province').value?.trim() || 'nationwide',
                expected_delivery: document.getElementById('expectedDelivery')?.value || null,
            });
        }

        try {
            const url = type === 'bug' ? `/service-desk/submit-bug?mdm_id=${mdmId}` : `/service-desk/submit-requirement?mdm_id=${mdmId}`;
            const result = await Api.post(url, formData);

            NotificationSystem.show(`提交成功: ${result.message}`, 'success');

            setTimeout(() => {
                alert(`追踪码：${result.tracking_code}\n\n请保存。`);
                window.location.href = `service_desk_track.html?code=${result.tracking_code}`;
            }, 1000);
        } catch (error) {
            NotificationSystem.show(`提交失败：${error.message || '网络错误'}`, 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    },

    /**
     * 初始化追踪表单
     */
    initTrackForm() {
        const urlParams = new URLSearchParams(window.location.search);
        const codeParam = urlParams.get('code');
        if (codeParam) {
            const codeInput = document.getElementById('trackingCode');
            if (codeInput) codeInput.value = codeParam;
            this.trackTicket(codeParam);
        }

        const form = document.getElementById('searchForm');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                const code = document.getElementById('trackingCode').value.trim();
                this.trackTicket(code);
            });
        }
    },

    /**
     * 查询工单进度
     */
    async trackTicket(code) {
        if (!code) return;

        const searchBtn = document.getElementById('searchBtn');
        const ticketCard = document.getElementById('ticketCard');
        const emptyState = document.getElementById('emptyState');
        const errorAlert = document.getElementById('errorAlert');

        if (searchBtn) {
            searchBtn.disabled = true;
            searchBtn.textContent = '查询中...';
        }

        try {
            const ticket = await Api.get(`/service-desk/track/${encodeURIComponent(code)}`);

            if (emptyState) emptyState.classList.add('u-hide');
            if (errorAlert) errorAlert.classList.add('u-hide');
            if (ticketCard) ticketCard.classList.remove('u-hide');

            const setText = (id, text) => {
                const el = document.getElementById(id);
                if (el) el.textContent = text || '-';
            };

            setText('ticketTitle', ticket.title);
            setText('displayTrackingCode', ticket.tracking_code);

            const typeMap = { 'bug': '缺陷报告', 'requirement': '需求提交' };
            setText('ticketType', typeMap[ticket.ticket_type] || ticket.ticket_type);

            const statusBadge = document.getElementById('ticketStatus');
            if (statusBadge) {
                const statusMap = {
                    'pending': { text: '待处理', class: 'sd-badge--pending' },
                    'in-progress': { text: '处理中', class: 'sd-badge--in-progress' },
                    'completed': { text: '已完成', class: 'sd-badge--completed' },
                    'rejected': { text: '已拒绝', class: 'sd-badge--rejected' }
                };
                const info = statusMap[ticket.status] || { text: ticket.status, class: 'sd-badge--pending' };
                statusBadge.textContent = info.text;
                statusBadge.className = `sd-badge ${info.class}`;
            }

            setText('requesterName', ticket.requester_name);
            setText('requesterEmail', ticket.requester_email);
            setText('createdAt', new Date(ticket.created_at).toLocaleString());
            setText('updatedAt', new Date(ticket.updated_at).toLocaleString());

            const gitlabLink = document.getElementById('gitlabLink');
            if (gitlabLink) {
                if (ticket.gitlab_issue_url) {
                    gitlabLink.href = ticket.gitlab_issue_url;
                    gitlabLink.classList.remove('u-hide');
                } else {
                    gitlabLink.classList.add('u-hide');
                }
            }
        } catch (error) {
            if (errorAlert) {
                errorAlert.textContent = `查询失败：${error.message || '追踪码无效'}`;
                errorAlert.classList.remove('u-hide');
            }
            if (ticketCard) ticketCard.classList.add('u-hide');
            if (emptyState) emptyState.classList.remove('u-hide');
        } finally {
            if (searchBtn) {
                searchBtn.disabled = false;
                searchBtn.textContent = '查询工单';
            }
        }
    },

    /**
     * 加载我的工单
     */
    async loadMyTickets(filter = 'all') {
        const list = document.getElementById('myTicketsList');
        if (!list) return;

        // 设置欢迎词
        const user = await Auth.getCurrentUser();
        const welcomeEl = document.getElementById('welcome-text');
        if (welcomeEl && user) {
            welcomeEl.textContent = `Welcome back, ${user.full_name || user.username || 'User'}. Viewing your latest updates.`;
        }

        list.innerHTML = '';
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'u-p-40 u-text-center';
        loadingDiv.textContent = '加载中...';
        list.appendChild(loadingDiv);

        try {
            const result = await Api.get('/service-desk/my-tickets');

            // 后端返回格式可能包含 stats 和 tickets
            const tickets = Array.isArray(result) ? result : (result.tickets || []);
            const stats = result.stats || {};

            // 更新统计
            if (stats) {
                const updateStat = (id, val) => {
                    const el = document.getElementById(id);
                    if (el) el.textContent = val || 0;
                };
                updateStat('statTotal', stats.total);
                updateStat('statPending', stats.pending);
                updateStat('statInProgress', stats.in_progress);
                updateStat('statCompleted', stats.completed);
            }

            const filtered = filter === 'all' ? tickets : tickets.filter(t => t.status === filter);
            list.innerHTML = '';

            if (filtered.length === 0) {
                const emptyDiv = document.createElement('div');
                emptyDiv.className = 'u-p-40 u-text-center u-text-dim';
                emptyDiv.textContent = '无匹配记录';
                list.appendChild(emptyDiv);
                return;
            }

            const template = document.getElementById('sd-ticket-row-tpl');
            const fragment = document.createDocumentFragment();

            filtered.forEach(t => {
                const clone = template.content.cloneNode(true);

                const card = clone.querySelector('.sd-card') || clone.querySelector('.js-ticket-row');
                if (card) {
                    card.addEventListener('click', () => {
                        window.location.href = `service_desk_track.html?code=${t.tracking_code}`;
                    });
                }

                const setTitle = (selector, txt) => {
                    const el = clone.querySelector(selector);
                    if (el) el.textContent = txt || '';
                };

                setTitle('.js-tk-title', t.title);
                setTitle('.js-tk-code', t.tracking_code);
                setTitle('.js-tk-date', new Date(t.created_at).toLocaleDateString());

                const statusBadge = clone.querySelector('.js-tk-status') || clone.querySelector('.sd-badge');
                if (statusBadge) {
                    statusBadge.textContent = t.status.toUpperCase();
                    statusBadge.className = `sd-badge sd-badge--${t.status}`;
                }

                const typeIcon = clone.querySelector('.js-tk-type-icon');
                if (typeIcon) {
                    typeIcon.textContent = t.ticket_type === 'bug' ? 'Bug' : 'Req';
                }

                fragment.appendChild(clone);
            });

            list.appendChild(fragment);

            // 初始化 Tabs
            const tabs = document.querySelectorAll('.sd-tab');
            tabs.forEach(tab => {
                if (!tab.hasAttribute('data-handler-bound')) {
                    tab.setAttribute('data-handler-bound', 'true');
                    tab.addEventListener('click', () => {
                        tabs.forEach(t => t.classList.remove('is-active'));
                        tab.classList.add('is-active');
                        this.loadMyTickets(tab.dataset.filter);
                    });
                }
            });

        } catch (error) {
            list.innerHTML = '';
            const errDiv = document.createElement('div');
            errDiv.className = 'u-p-40 u-text-center u-text-error';
            errDiv.textContent = `加载失败: ${error.message}`;
            list.appendChild(errDiv);
        }
    }
};

// ES6 Module Export
export default SDPortalHandler;

// 全局暴露以支持 DOM 加载触发 (向后兼容)
document.addEventListener('DOMContentLoaded', () => SDPortalHandler.init());
