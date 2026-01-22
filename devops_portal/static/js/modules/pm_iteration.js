import { Api, UI, Auth } from './sys_core.js';

/**
 * @file pm_iteration.js
 * @description 迭代计划工作台 (PM Domain Handler)
 */
const PmIterationHandler = {
    state: {
        currentProjectId: null,
        currentMilestoneId: null,
        currentMilestoneTitle: null
    },

    /**
     * 初始化
     */
    async init() {
        console.log("PM Iteration: Orchestrating lifecycle...");
        this.bindEvents();
        await this.loadProjects();
        this.checkBindStatus();
        this.initCreateButton();
    },

    /**
     * 绑定静态事件
     */
    bindEvents() {
        // 使用更具描述性的选择器
        const projectSelect = document.getElementById('projectSelect');
        const milestoneSelect = document.getElementById('milestoneSelect');

        if (projectSelect) {
            projectSelect.addEventListener('change', (e) => this.handleProjectChange(e.target.value));
        }

        if (milestoneSelect) {
            milestoneSelect.addEventListener('change', (e) => this.handleMilestoneChange(e));
        }

        // 拖拽委派
        document.querySelectorAll('.js-pm-issue-list').forEach(list => {
            list.addEventListener('dragover', (e) => this.handleDragOver(e));
            list.addEventListener('dragleave', (e) => e.currentTarget.classList.remove('drag-over'));
            list.addEventListener('drop', (e) => this.handleDrop(e));
        });

        // 通用按钮通过 js- 钩子绑定
        const refreshBtn = document.querySelector('.js-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadData());
        }

        const releaseBtn = document.getElementById('releaseBtn');
        if (releaseBtn) {
            releaseBtn.addEventListener('click', () => this.showReleaseModal());
        }

        const confirmReleaseBtn = document.getElementById('confirmReleaseBtn');
        if (confirmReleaseBtn) {
            confirmReleaseBtn.addEventListener('click', () => this.executeRelease());
        }

        const rolloverBtn = document.querySelector('.js-confirm-rollover');
        if (rolloverBtn) {
            rolloverBtn.addEventListener('click', () => this.handleRollover());
        }

        const bindBtn = document.querySelector('.js-btn-bind-gitlab');
        if (bindBtn) {
            bindBtn.addEventListener('click', () => window.location.href = '/auth/gitlab/bind');
        }

        // 模态框关闭动作
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('js-close-pm-modal')) {
                this.closeModals();
            }
        });
    },

    /**
     * 初始化新建迭代按钮
     */
    initCreateButton() {
        const controlsDiv = document.querySelector('.controls');
        if (!controlsDiv) return;

        // 检查是否已存在按钮
        if (controlsDiv.querySelector('.js-create-sprint-btn')) return;

        const createBtn = document.createElement('button');
        createBtn.className = 'secondary u-ml-8 js-create-sprint-btn';
        createBtn.textContent = '+ 新建迭代';
        createBtn.addEventListener('click', () => {
            if (!this.state.currentProjectId) {
                return UI.showToast('请先选择项目', 'warning');
            }
            UI.showModal('createSprintModal');
        });
        controlsDiv.appendChild(createBtn);

        const executeCreateBtn = document.querySelector('.js-execute-create-sprint');
        if (executeCreateBtn) {
            executeCreateBtn.addEventListener('click', () => this.executeCreateSprint());
        }
    },

    /**
     * 加载项目列表
     */
    async loadProjects() {
        const select = document.getElementById('projectSelect');
        if (!select) return;

        try {
            const projects = await Api.get('/iteration-plan/projects');
            select.innerHTML = '<option value="" disabled selected>选择项目...</option>';

            projects.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = `${p.path} (ID: ${p.id})`;
                select.appendChild(opt);
            });
        } catch (e) {
            UI.showToast("项目加载失败: " + e.message, "error");
        }
    },

    /**
     * 处理项目变更
     */
    async handleProjectChange(projectId) {
        this.state.currentProjectId = projectId;
        UI.toggleLoading("切换项目数据...", true);
        try {
            await this.loadMilestones(projectId);

            const msSelect = document.getElementById('milestoneSelect');
            if (msSelect) msSelect.value = '';

            const clearList = (id) => {
                const el = document.getElementById(id);
                if (el) el.innerHTML = '';
            };
            clearList('backlogList');
            clearList('sprintList');

            const releaseBtn = document.getElementById('releaseBtn');
            if (releaseBtn) releaseBtn.disabled = true;
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 加载里程碑
     */
    async loadMilestones(projectId) {
        const msSelect = document.getElementById('milestoneSelect');
        if (!msSelect) return;

        msSelect.innerHTML = '<option value="" disabled selected>加载里程碑...</option>';

        try {
            const milestones = await Api.get(`/iteration-plan/projects/${projectId}/milestones`);
            msSelect.innerHTML = '<option value="" disabled selected>选择迭代...</option>';

            if (milestones.length === 0) {
                const opt = document.createElement('option');
                opt.disabled = true;
                opt.textContent = "无进行中的里程碑";
                msSelect.appendChild(opt);
            }

            milestones.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.id;
                opt.textContent = `${m.title} (Due: ${m.due_date ? m.due_date.split('T')[0] : 'N/A'})`;
                opt.dataset.title = m.title;
                msSelect.appendChild(opt);
            });
        } catch (e) {
            msSelect.innerHTML = '<option value="" disabled selected>加载失败</option>';
            UI.showToast("里程碑加载失败", "error");
        }
    },

    /**
     * 处理里程碑变更
     */
    handleMilestoneChange(e) {
        const selectedOption = e.target.selectedOptions[0];
        if (!selectedOption) return;

        this.state.currentMilestoneId = e.target.value;
        this.state.currentMilestoneTitle = selectedOption.dataset.title;

        const releaseBtn = document.getElementById('releaseBtn');
        if (releaseBtn) releaseBtn.disabled = false;

        this.loadData();
    },

    /**
     * 加载看板数据
     */
    async loadData() {
        const { currentProjectId, currentMilestoneTitle } = this.state;
        if (!currentProjectId || !currentMilestoneTitle) return;

        UI.toggleLoading("同步看板状态...", true);
        try {
            const [backlogIssues, sprintIssues] = await Promise.all([
                Api.get(`/iteration-plan/projects/${currentProjectId}/backlog`),
                Api.get(`/iteration-plan/projects/${currentProjectId}/sprint/${encodeURIComponent(currentMilestoneTitle)}`)
            ]);

            this.renderList('backlogList', backlogIssues, 'backlogCount');
            this.renderList('sprintList', sprintIssues, 'sprintCount');
            this.updateStats(sprintIssues);
        } catch (e) {
            UI.showToast("看板数据获取失败: " + e.message, "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 渲染列表 (显式安全性处理)
     */
    renderList(containerId, issues, countBadgeId) {
        const container = document.getElementById(containerId);
        const countBadge = document.getElementById(countBadgeId);
        if (!container) return;

        container.innerHTML = '';
        if (countBadge) countBadge.textContent = issues.length;

        const template = document.getElementById('pm-issue-card-tpl');
        const fragment = document.createDocumentFragment();

        issues.forEach(issue => {
            const clone = template.content.cloneNode(true);
            const card = clone.querySelector('.pm-issue-card');

            if (issue.state === 'closed') {
                card.classList.add('is-closed');
            }

            card.dataset.iid = issue.iid;
            card.dataset.id = issue.id;

            // 文本内容显式填充 (XSS 防御)
            clone.querySelector('.js-card-title').textContent = issue.title;
            clone.querySelector('.js-card-iid').textContent = `#${issue.iid}`;

            const labelContainer = clone.querySelector('.js-card-labels');
            if (labelContainer) {
                const label = document.createElement('span');
                const isBug = (issue.labels || []).includes('type::bug');
                label.className = `label ${isBug ? 'bug' : 'req'}`;
                label.textContent = isBug ? 'Bug' : 'Feature';
                labelContainer.appendChild(label);
            }

            clone.querySelector('.js-card-author').textContent = issue.author?.name || 'Unknown';
            const weightEl = clone.querySelector('.js-card-weight');
            if (weightEl && issue.weight) {
                weightEl.textContent = `${issue.weight} pts`;
                weightEl.classList.remove('u-hide');
            }

            card.addEventListener('dragstart', (e) => this.handleDragStart(e));
            fragment.appendChild(clone);
        });

        container.appendChild(fragment);
    },

    /**
     * 更新统计数据
     */
    updateStats(sprintIssues) {
        const totalWeight = sprintIssues.reduce((sum, i) => sum + (i.weight || 0), 0);
        const totalWeightEl = document.getElementById('totalWeight');
        if (totalWeightEl) totalWeightEl.textContent = totalWeight;

        const totalCount = sprintIssues.length;
        const closedCount = sprintIssues.filter(i => i.state === 'closed').length;
        const progress = totalCount > 0 ? Math.round((closedCount / totalCount) * 100) : 0;

        const updateTxt = (id, txt) => {
            const el = document.getElementById(id);
            if (el) el.textContent = txt;
        };

        updateTxt('totalSprintIssues', totalCount);
        updateTxt('closedCount', closedCount);
        updateTxt('progressText', `${progress}%`);

        const progressBar = document.getElementById('progressBar');
        if (progressBar) progressBar.style.width = `${progress}%`;
    },

    /**
     * 拖拽状态管理
     */
    handleDragStart(ev) {
        ev.dataTransfer.setData("iid", ev.currentTarget.dataset.iid);
        ev.dataTransfer.setData("source", ev.currentTarget.parentElement.id);
        ev.dataTransfer.effectAllowed = "move";
    },

    handleDragOver(ev) {
        ev.preventDefault();
        ev.currentTarget.classList.add('drag-over');
    },

    /**
     * 处理放置
     */
    async handleDrop(ev) {
        ev.preventDefault();
        const targetList = ev.currentTarget;
        targetList.classList.remove('drag-over');

        const iid = ev.dataTransfer.getData("iid");
        const sourceListId = ev.dataTransfer.getData("source");
        const targetListId = targetList.id;

        if (sourceListId === targetListId) return;

        const { currentProjectId, currentMilestoneId } = this.state;
        UI.toggleLoading("Move in progress...", true);

        try {
            if (targetListId === 'sprintList') {
                await Api.post(`/iteration-plan/projects/${currentProjectId}/plan`, {
                    issue_iid: parseInt(iid),
                    milestone_id: parseInt(currentMilestoneId)
                });
            } else {
                await Api.post(`/iteration-plan/projects/${currentProjectId}/remove`, {
                    issue_iid: parseInt(iid)
                });
            }
            UI.showToast("操作成功", "success");
            this.loadData();
        } catch (e) {
            UI.showToast("移动失败: " + e.message, "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 发布工作流
     */
    showReleaseModal() {
        const input = document.getElementById('releaseVersionInput');
        if (input) input.value = this.state.currentMilestoneTitle;
        UI.showModal('releaseModal');
    },

    async executeRelease() {
        const newTitle = document.getElementById('releaseVersionInput').value.trim();
        if (!newTitle) return UI.showToast('版本名称不能为空', 'warning');

        UI.toggleLoading("正在同步 GitLab 里程碑及 Tag...", true);
        try {
            await Api.post(`/iteration-plan/projects/${this.state.currentProjectId}/release`, {
                version: this.state.currentMilestoneTitle,
                new_title: newTitle,
                ref_branch: 'main'
            });

            UI.showToast('发布成功！里程碑已闭环。', 'success');
            this.closeModals();
            this.loadData();
        } catch (error) {
            if (error.status === 409) {
                const msgEl = document.getElementById('rolloverMsg');
                if (msgEl) msgEl.textContent = (error.message || "").split('|')[0];
                this.closeModals();
                UI.showModal('rolloverModal');
            } else if (error.status === 403) {
                UI.showModal('bindGitLabModal');
            } else {
                UI.showToast('发布失败: ' + error.message, 'error');
            }
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 处理结转
     */
    async handleRollover() {
        const newTitle = document.getElementById('releaseVersionInput').value.trim();
        UI.toggleLoading("正在迁移未完成任务...", true);

        try {
            await Api.post(`/iteration-plan/projects/${this.state.currentProjectId}/release`, {
                version: this.state.currentMilestoneTitle,
                new_title: newTitle,
                ref_branch: 'main',
                auto_rollover: true,
                target_milestone_id: null
            });

            UI.showToast('结转并发布成功！', 'success');
            this.closeModals();
            this.loadData();
        } catch (e) {
            UI.showToast('结转操作失败: ' + e.message, 'error');
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 新建迭代
     */
    async executeCreateSprint() {
        const val = (id) => document.getElementById(id).value.trim();
        const title = val('newSprintTitle');
        if (!title) return UI.showToast('请输入迭代名称', 'warning');

        UI.toggleLoading("创建里程碑中...", true);
        try {
            await Api.post(`/iteration-plan/projects/${this.state.currentProjectId}/milestones`, {
                title: title,
                start_date: val('newSprintStart') || null,
                due_date: val('newSprintDue') || null,
                description: val('newSprintDesc') || null
            });

            UI.showToast('迭代创建成功！', 'success');
            this.closeModals();
            await this.loadMilestones(this.state.currentProjectId);
        } catch (e) {
            UI.showToast('创建失败: ' + e.message, 'error');
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 辅助确认绑定状态
     */
    checkBindStatus() {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('bind_success')) {
            window.history.replaceState({}, document.title, window.location.pathname);
            UI.showToast('🎉 GitLab 账号绑定成功！', 'success');
        }
    },

    closeModals() {
        ['releaseModal', 'bindGitLabModal', 'createSprintModal', 'rolloverModal'].forEach(id => {
            UI.hideModal(id);
        });
    }
};

export default PmIterationHandler;

// 自动初始化
document.addEventListener('DOMContentLoaded', () => PmIterationHandler.init());
