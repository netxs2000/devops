import { Api, UI, Auth } from './sys_core.js';
import { PMIterationService } from './pm_iteration_service.js';

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

        // 预防 iframe 嵌套
        if (window !== window.top) {
            document.querySelectorAll('a[href="/"], a[href="index.html"]').forEach(link => {
                link.target = '_top';
            });
        }
    },

    /**
     * 绑定静态事件
     */
    bindEvents() {
        const projectSelect = document.querySelector('.js-project-select');
        const milestoneSelect = document.querySelector('.js-milestone-select');

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

        const releaseBtn = document.querySelector('.js-release-btn');
        if (releaseBtn) {
            releaseBtn.addEventListener('click', () => this.showReleaseModal());
        }

        const confirmReleaseBtn = document.querySelector('.js-confirm-release-btn');
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
        const controlsDiv = document.querySelector('.js-pm-controls');
        if (!controlsDiv) return;

        if (controlsDiv.querySelector('.js-create-sprint-btn')) return;

        const createBtn = document.createElement('button');
        createBtn.className = 'btn-ghost u-ml-12 js-create-sprint-btn';
        createBtn.innerHTML = '<span>+ 新建迭代</span>';
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
        const select = document.querySelector('.js-project-select');
        if (!select) return;

        try {
            const projects = await PMIterationService.getProjects();
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

            const msSelect = document.querySelector('.js-milestone-select');
            if (msSelect) msSelect.value = '';

            const clearList = (selector) => {
                const el = document.querySelector(selector);
                if (el) el.innerHTML = '';
            };
            clearList('.js-backlog-list');
            clearList('.js-sprint-list');

            const releaseBtn = document.querySelector('.js-release-btn');
            if (releaseBtn) releaseBtn.disabled = true;
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 加载里程碑
     */
    async loadMilestones(projectId) {
        const msSelect = document.querySelector('.js-milestone-select');
        if (!msSelect) return;

        msSelect.innerHTML = '<option value="" disabled selected>加载里程碑...</option>';

        try {
            const milestones = await PMIterationService.getMilestones(projectId);
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

        const releaseBtn = document.querySelector('.js-release-btn');
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
                PMIterationService.getBacklog(currentProjectId),
                PMIterationService.getSprint(currentProjectId, currentMilestoneTitle)
            ]);

            this.renderList('.js-backlog-list', backlogIssues, '.js-backlog-count');
            this.renderList('.js-sprint-list', sprintIssues, '.js-sprint-count');
            this.updateStats(sprintIssues);
        } catch (e) {
            UI.showToast("看板数据获取失败: " + e.message, "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 渲染列表 (使用 Web Components)
     */
    renderList(containerSelector, issues, countBadgeSelector) {
        const container = document.querySelector(containerSelector);
        const countBadge = document.querySelector(countBadgeSelector);
        if (!container) return;

        container.innerHTML = '';
        if (countBadge) countBadge.textContent = issues.length;

        const fragment = document.createDocumentFragment();

        issues.forEach(issue => {
            const card = document.createElement('pm-issue-card');

            // 设置属性，触发影子 DOM 渲染
            card.setAttribute('title', issue.title);
            card.setAttribute('iid', issue.iid);
            card.setAttribute('status', issue.state);
            card.setAttribute('author', issue.author?.name || 'Unknown');
            if (issue.weight) card.setAttribute('weight', issue.weight);

            const isBug = (issue.labels || []).includes('type::bug');
            card.setAttribute('type', isBug ? 'bug' : 'feature');

            card.dataset.iid = issue.iid;
            card.setAttribute('draggable', 'true');
            card.addEventListener('dragstart', (e) => this.handleDragStart(e));

            fragment.appendChild(card);
        });

        container.appendChild(fragment);
    },

    /**
     * 更新统计数据
     */
    updateStats(sprintIssues) {
        const totalWeight = sprintIssues.reduce((sum, i) => sum + (i.weight || 0), 0);
        const totalWeightEl = document.querySelector('.js-total-weight');
        if (totalWeightEl) totalWeightEl.textContent = totalWeight;

        const totalCount = sprintIssues.length;
        const closedCount = sprintIssues.filter(i => i.state === 'closed').length;
        const progress = totalCount > 0 ? Math.round((closedCount / totalCount) * 100) : 0;

        const updateTxt = (selector, txt) => {
            const el = document.querySelector(selector);
            if (el) el.textContent = txt;
        };

        updateTxt('.js-total-sprint-issues', totalCount);
        updateTxt('.js-closed-count', closedCount);
        updateTxt('.js-progress-text', `${progress}%`);

        const progressBar = document.querySelector('.js-progress-bar');
        if (progressBar) progressBar.style.width = `${progress}%`;
    },

    /**
     * 拖拽状态管理
     */
    handleDragStart(ev) {
        ev.dataTransfer.setData("iid", ev.currentTarget.dataset.iid);
        ev.dataTransfer.setData("source", ev.currentTarget.parentElement.classList.contains('js-backlog-list') ? 'backlogList' : 'sprintList');
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
        const isTargetSprint = targetList.classList.contains('js-sprint-list');
        const targetListId = isTargetSprint ? 'sprintList' : 'backlogList';

        if (sourceListId === targetListId) return;

        const { currentProjectId, currentMilestoneId } = this.state;
        UI.toggleLoading("Move in progress...", true);

        try {
            if (isTargetSprint) {
                await PMIterationService.planIssue(currentProjectId, iid, currentMilestoneId);
            } else {
                await PMIterationService.removeIssue(currentProjectId, iid);
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
        const input = document.querySelector('.js-release-version-input');
        if (input) input.value = this.state.currentMilestoneTitle;
        UI.showModal('releaseModal');
    },

    async executeRelease() {
        const newTitle = document.querySelector('.js-release-version-input').value.trim();
        if (!newTitle) return UI.showToast('版本名称不能为空', 'warning');

        UI.toggleLoading("正在同步 GitLab 里程碑及 Tag...", true);
        try {
            await PMIterationService.release(this.state.currentProjectId, {
                version: this.state.currentMilestoneTitle,
                new_title: newTitle,
                ref_branch: 'main'
            });

            UI.showToast('发布成功！里程碑已闭环。', 'success');
            this.closeModals();
            this.loadData();
        } catch (error) {
            if (error.status === 409) {
                const msgEl = document.querySelector('.js-rollover-msg');
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
        const newTitle = document.querySelector('.js-release-version-input').value.trim();
        UI.toggleLoading("正在迁移未完成任务...", true);

        try {
            await PMIterationService.release(this.state.currentProjectId, {
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
        const title = document.querySelector('.js-new-sprint-title').value.trim();
        if (!title) return UI.showToast('请输入迭代名称', 'warning');

        UI.toggleLoading("创建里程碑中...", true);
        try {
            await PMIterationService.createMilestone(this.state.currentProjectId, {
                title: title,
                start_date: document.querySelector('.js-new-sprint-start').value || null,
                due_date: document.querySelector('.js-new-sprint-due').value || null,
                description: document.querySelector('.js-new-sprint-desc').value || null
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
