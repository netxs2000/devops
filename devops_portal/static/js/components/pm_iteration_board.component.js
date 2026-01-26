/**
 * @file pm_iteration_board.component.js
 * @description Project Management Iteration Board (Kanban) with MDM Project Selection
 */
import { PMIterationService } from '../modules/pm_iteration_service.js';
import { UI, Auth } from '../modules/sys_core.js';
import '../components/pm_issue_card.component.js';

class PmIterationBoard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.state = {
            // MDM Layer
            mdmProjects: [],
            currentMdmProjectId: null,
            currentMdmProject: null,
            // GitLab Layer (derived from MDM)
            gitlabRepos: [],
            currentGitlabProjectId: null,
            // Iteration Layer
            milestones: [],
            currentMilestoneId: null,
            currentMilestoneTitle: null,
            // Board Data
            backlog: [],
            sprint: []
        };
    }

    async connectedCallback() {
        this.render();
        await this.loadMdmProjects();
        this.checkBindStatus();
    }

    checkBindStatus() {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('bind_success')) {
            window.history.replaceState({}, document.title, window.location.pathname + window.location.hash);
            UI.showToast('GitLab 账号绑定成功!', 'success');
        }
    }

    async loadMdmProjects() {
        try {
            this.state.mdmProjects = await PMIterationService.getMdmProjects();
            this.render();
        } catch (e) {
            console.error("Failed to load MDM projects", e);
            UI.showToast("加载主项目失败", "error");
        }
    }

    handleMdmProjectChange(mdmProjectId) {
        const project = this.state.mdmProjects.find(p => p.project_id === mdmProjectId);
        this.state.currentMdmProjectId = mdmProjectId;
        this.state.currentMdmProject = project;

        // Extract linked GitLab repos from MDM project
        this.state.gitlabRepos = project?.gitlab_repos || [];

        // If lead_repo exists, auto-select it
        if (project?.lead_repo_id) {
            this.state.currentGitlabProjectId = project.lead_repo_id;
            this.loadMilestones(project.lead_repo_id);
        } else {
            this.state.currentGitlabProjectId = null;
            this.state.milestones = [];
        }

        this.state.currentMilestoneId = null;
        this.state.currentMilestoneTitle = null;
        this.state.backlog = [];
        this.state.sprint = [];
        this.render();
    }

    async loadMilestones(gitlabProjectId) {
        try {
            this.state.milestones = await PMIterationService.getMilestones(gitlabProjectId);
            this.render();
        } catch (e) {
            console.error("Failed to load milestones", e);
        }
    }

    async loadBoardData() {
        try {
            const { currentGitlabProjectId, currentMilestoneTitle } = this.state;
            if (!currentGitlabProjectId || !currentMilestoneTitle) return;

            UI.toggleLoading("Syncing Board...", true);
            const [backlog, sprint] = await Promise.all([
                PMIterationService.getBacklog(currentGitlabProjectId),
                PMIterationService.getSprint(currentGitlabProjectId, currentMilestoneTitle)
            ]);
            this.state.backlog = backlog;
            this.state.sprint = sprint;
            UI.toggleLoading("", false);
            this.render();
        } catch (e) {
            UI.toggleLoading("", false);
            UI.showToast("Failed to load board: " + e.message, "error");
        }
    }

    render() {
        const totalWeight = this.state.sprint.reduce((sum, i) => sum + (i.weight || 0), 0);
        const totalCount = this.state.sprint.length;
        const closedCount = this.state.sprint.filter(i => i.state === 'closed').length;
        const progress = totalCount > 0 ? Math.round((closedCount / totalCount) * 100) : 0;

        this.shadowRoot.innerHTML = `
            <style>
                :host { display: flex; flex-direction: column; height: 100%; overflow: hidden; font-family: 'Inter', system-ui, sans-serif; }
                
                /* Header */
                .header { padding: 24px 0; border-bottom: 1px solid rgba(0,0,0,0.05); margin-bottom: 24px; }
                .header-title { font-size: 28px; font-weight: 700; color: #1d1d1f; margin: 0 0 20px 0; }
                .controls { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
                .select { padding: 10px 14px; border-radius: 10px; border: 1px solid #d2d2d7; font-size: 14px; min-width: 200px; background: white; cursor: pointer; }
                .select:focus { outline: none; border-color: #0071e3; box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.1); }
                .btn { padding: 10px 18px; border-radius: 10px; font-size: 14px; font-weight: 500; cursor: pointer; border: none; transition: all 0.2s; }
                .btn-primary { background: #0071e3; color: white; }
                .btn-primary:hover { background: #0077ED; }
                .btn-ghost { background: #f5f5f7; color: #1d1d1f; }
                .btn-ghost:hover { background: #e8e8ed; }
                .btn:disabled { opacity: 0.5; cursor: not-allowed; }
                .spacer { flex: 1; }
                .select-label { font-size: 11px; color: #86868b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
                .select-group { display: flex; flex-direction: column; }

                /* Board */
                .board { display: flex; gap: 24px; flex: 1; overflow: hidden; }
                .column { flex: 1; display: flex; flex-direction: column; background: rgba(255,255,255,0.6); backdrop-filter: blur(20px); border-radius: 16px; border: 1px solid rgba(0,0,0,0.05); box-shadow: 0 4px 24px rgba(0,0,0,0.03); }
                .col-header { padding: 20px; border-bottom: 1px solid rgba(0,0,0,0.05); }
                .col-title { font-weight: 600; font-size: 16px; color: #1d1d1f; display: flex; justify-content: space-between; align-items: center; }
                .badge { background: #E5E5EA; color: #1d1d1f; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
                
                .col-body { flex: 1; overflow-y: auto; padding: 16px; min-height: 200px; }
                .col-body.drag-over { background: rgba(0, 113, 227, 0.05); border: 2px dashed #0071e3; border-radius: 12px; }

                /* Progress */
                .progress-wrap { margin-top: 16px; }
                .progress-track { height: 6px; background: #E5E5EA; border-radius: 3px; overflow: hidden; }
                .progress-bar { height: 100%; background: linear-gradient(90deg, #34C759, #30D158); width: ${progress}%; transition: width 0.5s ease; }
                .stats-row { display: flex; justify-content: space-between; font-size: 12px; color: #86868b; margin-top: 8px; }

                /* Modals */
                .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.4); backdrop-filter: blur(4px); display: none; align-items: center; justify-content: center; z-index: 1000; }
                .modal-overlay.show { display: flex; }
                .modal { background: white; border-radius: 20px; padding: 32px; width: 90%; max-width: 480px; box-shadow: 0 20px 60px rgba(0,0,0,0.2); animation: modalIn 0.3s ease; }
                @keyframes modalIn { from { transform: scale(0.95); opacity: 0; } to { transform: scale(1); opacity: 1; } }
                .modal-title { font-size: 22px; font-weight: 700; margin: 0 0 8px 0; color: #1d1d1f; }
                .modal-desc { color: #86868b; margin: 0 0 24px 0; font-size: 14px; }
                .form-group { margin-bottom: 20px; }
                .form-label { display: block; font-size: 13px; font-weight: 500; color: #1d1d1f; margin-bottom: 8px; }
                .form-input { width: 100%; box-sizing: border-box; padding: 12px; border: 1px solid #d2d2d7; border-radius: 10px; font-size: 14px; }
                .form-input:focus { outline: none; border-color: #0071e3; }
                .modal-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 28px; }
                .hint { font-size: 12px; color: #86868b; margin-top: 8px; }
                .checklist { list-style: none; padding: 0; margin: 0 0 20px 0; }
                .checklist li { padding: 6px 0; color: #86868b; font-size: 13px; }
                .checklist li::before { content: "•"; margin-right: 8px; color: #0071e3; }
                
                .modal-title.error { color: #FF3B30; }
                
                .empty-state { padding: 40px; text-align: center; color: #86868b; font-size: 14px; }
            </style>

            <div class="header">
                <h1 class="header-title">迭代计划工作台</h1>
                <div class="controls">
                    <div class="select-group">
                        <span class="select-label">业务主项目</span>
                        <select class="select js-mdm-project">
                            <option value="" disabled ${!this.state.currentMdmProjectId ? 'selected' : ''}>选择主项目...</option>
                            ${this.state.mdmProjects.map(p => `
                                <option value="${p.project_id}" ${p.project_id === this.state.currentMdmProjectId ? 'selected' : ''}>${p.project_name}</option>
                            `).join('')}
                        </select>
                    </div>

                    <div class="select-group">
                        <span class="select-label">GitLab 仓库</span>
                        <select class="select js-gitlab-repo" ${this.state.gitlabRepos.length === 0 && !this.state.currentGitlabProjectId ? 'disabled' : ''}>
                            <option value="" disabled ${!this.state.currentGitlabProjectId ? 'selected' : ''}>选择仓库...</option>
                            ${this.state.gitlabRepos.map(r => `
                                <option value="${r.id}" ${r.id == this.state.currentGitlabProjectId ? 'selected' : ''}>${r.name || r.path_with_namespace}</option>
                            `).join('')}
                            ${this.state.currentMdmProject?.lead_repo_id && this.state.gitlabRepos.length === 0 ? `
                                <option value="${this.state.currentMdmProject.lead_repo_id}" selected>Lead Repo (ID: ${this.state.currentMdmProject.lead_repo_id})</option>
                            ` : ''}
                        </select>
                    </div>

                    <div class="select-group">
                        <span class="select-label">迭代版本</span>
                        <select class="select js-milestone" ${!this.state.currentGitlabProjectId ? 'disabled' : ''}>
                            <option value="" disabled ${!this.state.currentMilestoneId ? 'selected' : ''}>选择迭代...</option>
                            ${this.state.milestones.map(m => `
                                <option value="${m.id}" data-title="${m.title}" ${m.id == this.state.currentMilestoneId ? 'selected' : ''}>${m.title}</option>
                            `).join('')}
                        </select>
                    </div>

                    <button class="btn btn-ghost js-create-sprint" ${!this.state.currentGitlabProjectId ? 'disabled' : ''}>+ 新建迭代</button>
                    <div class="spacer"></div>
                    <button class="btn btn-ghost js-refresh">刷新</button>
                    <button class="btn btn-primary js-release" ${!this.state.currentMilestoneId ? 'disabled' : ''}>执行发布</button>
                </div>
            </div>

            <div class="board">
                <div class="column">
                    <div class="col-header">
                        <div class="col-title">待办需求池 (Backlog) <span class="badge">${this.state.backlog.length}</span></div>
                    </div>
                    <div class="col-body js-list" data-type="backlog">
                        ${this.state.backlog.length === 0 && this.state.currentMilestoneId ? '<div class="empty-state">暂无待办任务</div>' : ''}
                        ${this.state.backlog.map(item => this.renderCard(item)).join('')}
                    </div>
                </div>

                <div class="column">
                    <div class="col-header">
                        <div class="col-title">当前迭代 (Sprint) <span class="badge">${this.state.sprint.length}</span></div>
                        ${this.state.currentMilestoneId ? `
                            <div class="progress-wrap">
                                <div class="progress-track"><div class="progress-bar"></div></div>
                                <div class="stats-row">
                                    <span>进度: ${progress}% (${closedCount}/${totalCount} 已关闭)</span>
                                    <span>总权重: ${totalWeight}</span>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                    <div class="col-body js-list" data-type="sprint">
                        ${this.state.sprint.length === 0 && this.state.currentMilestoneId ? '<div class="empty-state">暂无规划任务</div>' : ''}
                        ${this.state.sprint.map(item => this.renderCard(item)).join('')}
                    </div>
                </div>
            </div>

            <!-- Create Sprint Modal -->
            <div class="modal-overlay js-modal" data-modal="create-sprint">
                <div class="modal">
                    <h2 class="modal-title">新建迭代 (Sprint)</h2>
                    <p class="modal-desc">创建一个新的里程碑来规划您的下一个交付周期。</p>
                    <div class="form-group">
                        <label class="form-label">迭代名称</label>
                        <input type="text" class="form-input js-sprint-title" placeholder="v1.2.0">
                    </div>
                    <div class="form-group" style="display: flex; gap: 12px;">
                        <div style="flex:1;">
                            <label class="form-label">开始日期</label>
                            <input type="date" class="form-input js-sprint-start">
                        </div>
                        <div style="flex:1;">
                            <label class="form-label">截止日期</label>
                            <input type="date" class="form-input js-sprint-due">
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label">描述 (可选)</label>
                        <textarea class="form-input js-sprint-desc" rows="2" placeholder="本次迭代的目标..."></textarea>
                    </div>
                    <div class="modal-actions">
                        <button class="btn btn-ghost js-close-modal">取消</button>
                        <button class="btn btn-primary js-confirm-create-sprint">创建迭代</button>
                    </div>
                </div>
            </div>

            <!-- Release Modal -->
            <div class="modal-overlay js-modal" data-modal="release">
                <div class="modal">
                    <h2 class="modal-title">确认发布版本</h2>
                    <p class="modal-desc">此操作将同步 GitLab 里程碑并创建正式 Tag。</p>
                    <div class="form-group">
                        <label class="form-label">版本名称 (将作为 Git Tag)</label>
                        <input type="text" class="form-input js-release-version" placeholder="v1.0.0" value="${this.state.currentMilestoneTitle || ''}">
                        <p class="hint">确认后系统将更新 GitLab 里程碑标题并创建同名 Tag。</p>
                    </div>
                    <ul class="checklist">
                        <li>同步更新 GitLab 里程碑标题</li>
                        <li>自动在代码库创建 Git Tag</li>
                        <li>生成版本变更日志</li>
                        <li>正式关闭该里程碑</li>
                    </ul>
                    <div class="modal-actions">
                        <button class="btn btn-ghost js-close-modal">取消</button>
                        <button class="btn btn-primary js-confirm-release">确认并发布</button>
                    </div>
                </div>
            </div>

            <!-- Rollover Modal -->
            <div class="modal-overlay js-modal" data-modal="rollover">
                <div class="modal">
                    <h2 class="modal-title error">检测到未完成任务</h2>
                    <p class="modal-desc js-rollover-msg">当前迭代存在未关闭的 Issue。</p>
                    <p style="color: #1d1d1f; font-size: 14px;">是否将未完成的任务自动移动到下一个规划中的 Milestone (或 Backlog)，并继续发布？</p>
                    <div class="modal-actions">
                        <button class="btn btn-ghost js-close-modal">取消</button>
                        <button class="btn btn-primary js-confirm-rollover">确认结转并发布</button>
                    </div>
                </div>
            </div>

            <!-- Bind GitLab Modal -->
            <div class="modal-overlay js-modal" data-modal="bind-gitlab">
                <div class="modal">
                    <h2 class="modal-title">关联 GitLab 账号</h2>
                    <p class="modal-desc">为了保障安全，您的系统账号尚未绑定 GitLab 身份。</p>
                    <p style="color: #86868b; font-size: 14px;">绑定后，您可以使用"个人身份"进行拖拽规划、新建迭代和发布操作。</p>
                    <div class="modal-actions">
                        <button class="btn btn-ghost js-close-modal">稍后</button>
                        <button class="btn btn-primary js-bind-gitlab">前往绑定</button>
                    </div>
                </div>
            </div>
        `;

        this.setupEvents();
    }

    renderCard(item) {
        return `<pm-issue-card 
            title="${item.title}" 
            iid="${item.iid}" 
            status="${item.state}" 
            author="${item.author?.name || 'Unknown'}" 
            weight="${item.weight || 0}"
            type="${(item.labels || []).includes('type::bug') ? 'bug' : 'feature'}"
            draggable="true"
            data-iid="${item.iid}">
        </pm-issue-card>`;
    }

    setupEvents() {
        // MDM Project Change
        this.shadowRoot.querySelector('.js-mdm-project').addEventListener('change', (e) => {
            this.handleMdmProjectChange(e.target.value);
        });

        // GitLab Repo Change
        this.shadowRoot.querySelector('.js-gitlab-repo').addEventListener('change', (e) => {
            this.state.currentGitlabProjectId = e.target.value;
            this.state.milestones = [];
            this.state.currentMilestoneId = null;
            this.state.currentMilestoneTitle = null;
            this.state.backlog = [];
            this.state.sprint = [];
            this.loadMilestones(this.state.currentGitlabProjectId);
        });

        // Milestone Change
        this.shadowRoot.querySelector('.js-milestone').addEventListener('change', (e) => {
            this.state.currentMilestoneId = e.target.value;
            this.state.currentMilestoneTitle = e.target.options[e.target.selectedIndex].dataset.title;
            this.loadBoardData();
        });

        // Refresh
        this.shadowRoot.querySelector('.js-refresh').addEventListener('click', () => this.loadBoardData());

        // Modal Triggers
        this.shadowRoot.querySelector('.js-create-sprint').addEventListener('click', () => this.showModal('create-sprint'));
        this.shadowRoot.querySelector('.js-release').addEventListener('click', () => {
            this.shadowRoot.querySelector('.js-release-version').value = this.state.currentMilestoneTitle || '';
            this.showModal('release');
        });

        // Modal Close
        this.shadowRoot.querySelectorAll('.js-close-modal').forEach(btn => {
            btn.addEventListener('click', () => this.hideModals());
        });

        // Modal Confirm Actions
        this.shadowRoot.querySelector('.js-confirm-create-sprint').addEventListener('click', () => this.executeCreateSprint());
        this.shadowRoot.querySelector('.js-confirm-release').addEventListener('click', () => this.executeRelease());
        this.shadowRoot.querySelector('.js-confirm-rollover').addEventListener('click', () => this.executeRollover());
        this.shadowRoot.querySelector('.js-bind-gitlab').addEventListener('click', () => {
            window.location.href = '/auth/gitlab/bind';
        });

        // Drag & Drop
        const lists = this.shadowRoot.querySelectorAll('.js-list');
        lists.forEach(list => {
            list.addEventListener('dragover', e => { e.preventDefault(); list.classList.add('drag-over'); });
            list.addEventListener('dragleave', e => list.classList.remove('drag-over'));
            list.addEventListener('drop', e => this.handleDrop(e, list.dataset.type));
        });

        // Card Drag Start
        this.shadowRoot.querySelectorAll('pm-issue-card').forEach(card => {
            card.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', JSON.stringify({
                    iid: card.dataset.iid,
                    source: card.parentElement.dataset.type
                }));
            });
        });
    }

    showModal(name) {
        this.shadowRoot.querySelectorAll('.js-modal').forEach(m => m.classList.remove('show'));
        const modal = this.shadowRoot.querySelector(`.js-modal[data-modal="${name}"]`);
        if (modal) modal.classList.add('show');
    }

    hideModals() {
        this.shadowRoot.querySelectorAll('.js-modal').forEach(m => m.classList.remove('show'));
    }

    async executeCreateSprint() {
        const title = this.shadowRoot.querySelector('.js-sprint-title').value.trim();
        if (!title) return UI.showToast('请输入迭代名称', 'warning');

        UI.toggleLoading("创建里程碑中...", true);
        try {
            await PMIterationService.createMilestone(this.state.currentGitlabProjectId, {
                title: title,
                start_date: this.shadowRoot.querySelector('.js-sprint-start').value || null,
                due_date: this.shadowRoot.querySelector('.js-sprint-due').value || null,
                description: this.shadowRoot.querySelector('.js-sprint-desc').value || null
            });

            UI.showToast('迭代创建成功!', 'success');
            this.hideModals();
            await this.loadMilestones(this.state.currentGitlabProjectId);
        } catch (e) {
            UI.showToast('创建失败: ' + e.message, 'error');
        } finally {
            UI.toggleLoading("", false);
        }
    }

    async executeRelease() {
        const newTitle = this.shadowRoot.querySelector('.js-release-version').value.trim();
        if (!newTitle) return UI.showToast('版本名称不能为空', 'warning');

        UI.toggleLoading("正在同步 GitLab 里程碑及 Tag...", true);
        try {
            await PMIterationService.release(this.state.currentGitlabProjectId, {
                version: this.state.currentMilestoneTitle,
                new_title: newTitle,
                ref_branch: 'main'
            });

            UI.showToast('发布成功！里程碑已闭环。', 'success');
            this.hideModals();
            this.loadBoardData();
        } catch (error) {
            if (error.status === 409) {
                const msgEl = this.shadowRoot.querySelector('.js-rollover-msg');
                if (msgEl) msgEl.textContent = (error.message || "当前迭代存在未完成任务。").split('|')[0];
                this.hideModals();
                this.showModal('rollover');
            } else if (error.status === 403) {
                this.hideModals();
                this.showModal('bind-gitlab');
            } else {
                UI.showToast('发布失败: ' + error.message, 'error');
            }
        } finally {
            UI.toggleLoading("", false);
        }
    }

    async executeRollover() {
        const newTitle = this.shadowRoot.querySelector('.js-release-version').value.trim();
        UI.toggleLoading("正在迁移未完成任务...", true);

        try {
            await PMIterationService.release(this.state.currentGitlabProjectId, {
                version: this.state.currentMilestoneTitle,
                new_title: newTitle,
                ref_branch: 'main',
                auto_rollover: true,
                target_milestone_id: null
            });

            UI.showToast('结转并发布成功!', 'success');
            this.hideModals();
            this.loadBoardData();
        } catch (e) {
            UI.showToast('结转操作失败: ' + e.message, 'error');
        } finally {
            UI.toggleLoading("", false);
        }
    }

    async handleDrop(e, targetType) {
        e.preventDefault();
        e.currentTarget.classList.remove('drag-over');
        const data = JSON.parse(e.dataTransfer.getData('text/plain'));

        if (data.source === targetType) return;

        const { currentGitlabProjectId, currentMilestoneId } = this.state;
        UI.toggleLoading("Moving Issue...", true);

        try {
            if (targetType === 'sprint') {
                await PMIterationService.planIssue(currentGitlabProjectId, data.iid, currentMilestoneId);
            } else {
                await PMIterationService.removeIssue(currentGitlabProjectId, data.iid);
            }
            UI.showToast("操作成功", "success");
            this.loadBoardData();
        } catch (err) {
            UI.showToast("Move failed: " + err.message, "error");
            UI.toggleLoading("", false);
        }
    }
}

customElements.define('pm-iteration-board', PmIterationBoard);
