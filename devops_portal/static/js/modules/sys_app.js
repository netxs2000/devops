import { Auth, Api, UI, NotificationSystem } from './sys_core.js';
import QaTestCaseHandler from './qa_test_cases.js';
import QaDefectHandler from './qa_defects.js';
import PmRequirementHandler from './pm_requirements.js';
import SdServiceDeskHandler from './sd_service_desk.js';
import SDPortalHandler from './sd_portal.js';
import PmMatrixHandler from './pm_matrix.js';
import RptOverviewHandler from './rpt_overview.js';
import SysUtilsHandler from './sys_utils.js';
import AdmManageHandler from './adm_manage.js';
import SecService from './sec_service.js';


const SysAppHandler = {
    state: {
        currentView: null,
        user: null,
        navConfig: [
            {
                title: "项目执行",
                expanded: true,
                items: [
                    { id: "nav-iterations", label: "迭代计划", href: "#iteration_plan", view: "iteration_plan", icon: "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" },
                    { id: "nav-reqs", label: "需求管理", href: "#requirements", view: "requirements", icon: "M9 11l3 3L22 4; M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" },
                    { id: "nav-support", label: "工单管理", href: "#support", view: "support", icon: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z; M8 9h8; M8 13h6" }
                ]
            },
            {
                title: "质量保障",
                expanded: true,
                items: [
                    { id: "nav-dashboard", label: "质量看板", href: "#dashboard", view: "dashboard", icon: "rect x=3 y=3 width=7 height=7; rect x=14 y=3 width=7 height=7; rect x=14 y=14 width=7 height=7; rect x=3 y=14 width=7 height=7", active: true },
                    { id: "nav-tests", label: "测试用例", href: "#test-cases", view: "test-cases", icon: "M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" },
                    { id: "nav-test-execution", label: "测试执行", href: "#test-execution", view: "test-execution", icon: "M13 2L3 14h9l-1 8 10-12h-9l1-8z" },
                    { id: "nav-defects", label: "缺陷管理", href: "#defects", view: "defects", icon: "circle cx=12 cy=12 r=10; line x1=12 y1=8 x2=12 y2=12; line x1=12 y1=16 x2=12.01 y2=16", badgeId: "badge-defects" },
                    { id: "nav-security", label: "安全扫描", href: "#security", view: "security", icon: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" },
                    { id: "nav-matrix", label: "追溯矩阵", href: "#matrix", view: "matrix", icon: "M12 2v20M2 12h20; M17 7l-5 5-5-5" }
                ]
            },
            {
                title: "洞察与治理",
                expanded: true,
                items: [
                    { id: "nav-reports", label: "质量洞察", href: "#reports", view: "reports", icon: "M21.21 15.89A10 10 0 1 1 8 2.83; M22 12A10 10 0 0 0 12 2v10z" },
                    { id: "nav-governance", label: "元数据治理", href: "http://localhost:9002/", target: "_blank", classes: ["u-text-main"], icon: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" },
                    { id: "nav-decision-hub", label: "决策中心", href: "http://localhost:8501/", target: "_blank", classes: ["u-text-primary", "u-weight-600"], icon: "circle cx=12 cy=12 r=10; polyline points=12 6 12 12 16 14" }
                ]
            },
            {
                title: "平台管理",
                adminOnly: true,
                expanded: true,
                items: [
                    { id: "nav-admin-approvals", label: "用户注册审批", href: "#admin_approvals", view: "admin_approvals", icon: "M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2; circle cx=8.5 cy=7 r=4; polyline points=17 11 19 13 23 9" },
                    { id: "nav-admin-orgs", label: "研发组织管理", href: "#admin_orgs", view: "admin_orgs", icon: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" },
                    { id: "nav-admin-products", label: "产品体系管理", href: "#admin_products", view: "admin_products", icon: "rect x=2 y=3 width=20 height=14 rx=2 ry=2; line x1=8 y1=21 x2=16 y2=21; line x1=12 y1=17 x2=12 y2=21" },
                    { id: "nav-admin-okrs", label: "OKR 治理中心", href: "#admin_okrs", view: "admin_okrs", icon: "circle cx=12 cy=12 r=10; circle cx=12 cy=12 r=6; circle cx=12 cy=12 r=2" },
                    { id: "nav-admin-projects", label: "项目映射配置", href: "#admin_projects", view: "admin_projects", icon: "polyline points=4 7 4 4 20 4 20 7; line x1=9 y1=20 x2=15 y2=20; line x1=12 y1=4 x2=12 y2=20" },
                    { id: "nav-admin-users", label: "员工身份目录", href: "#admin_users", view: "admin_users", icon: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2; circle cx=9 cy=7 r=4; path d=M23 21v-2a4 4 0 0 0-3-3.87; path d=M16 3.13a4 4 0 0 1 0 7.75" }
                ]
            },
            {
                title: "支持与战略",
                expanded: true,
                items: [
                    { id: "nav-sd-submit", label: "工单反馈", href: "#sd_submit", view: "sd_submit", icon: "M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7; M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" },
                    { id: "nav-sd-my", label: "我的工单", href: "#sd_my", view: "sd_my", icon: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z; M8 9h8; M8 13h6" },
                    { id: "nav-pulse", label: "心情指数打卡", href: "#pulse", view: "pulse", icon: "circle cx=12 cy=12 r=10; path d=M8 14s1.5 2 4 2 4-2 4-2; line x1=9 y1=9 x2=9.01 y2=9; line x1=15 y1=9 x2=15.01 y2=9" }
                ]
            }
        ]
    },

    /**
     * 初始化
     */
    async init() {
        console.log("Sys App Handler Initialized.");
        this.handleOAuthCallback();
        this.bindEvents();

        // 初始化核心模块处理器
        QaTestCaseHandler.init();
        QaDefectHandler.init();
        QaDefectHandler.init();
        PmRequirementHandler.init();
        PmMatrixHandler.init();
        SecService.init();

        await this.initUser();
        NotificationSystem.startSSE();
        this.checkGitLabStatus();
    },

    /**
     * 处理 OAuth 回调参数 (access_token)
     */
    handleOAuthCallback() {
        const urlParams = new URLSearchParams(window.location.search);
        const token = urlParams.get('access_token');
        const authState = urlParams.get('auth_state');
        const authError = urlParams.get('auth_error');

        if (token) {
            Auth.setToken(token);
            const newUrl = window.location.pathname + window.location.hash;
            window.history.replaceState({}, document.title, newUrl);
            UI.showToast('Login successful via GitLab!', 'success');
        } else if (authState === 'pending') {
            const newUrl = window.location.pathname + window.location.hash;
            window.history.replaceState({}, document.title, newUrl);
            alert('您的账号已通过 GitLab 自动创建，但目前处于“待审批”状态。请联系系统管理员激活您的账号后再试。');
        } else if (authError) {
            const newUrl = window.location.pathname + window.location.hash;
            window.history.replaceState({}, document.title, newUrl);
            const errorMsgs = {
                'domain_not_allowed': '您的 GitLab 邮箱域名不在允许的范围内，请联系管理员。',
                'token_exchange_failed': 'GitLab 令牌交换失败，请重试。',
                'user_info_failed': '获取 GitLab 用户信息失败。',
                'email_missing': '您的 GitLab 账号缺少邮箱信息。'
            };
            UI.showToast(errorMsgs[authError] || `登录失败: ${authError}`, 'error');
        }
    },

    async handleLocalLogin() {
        const email = document.getElementById('login-email').value.trim();
        const password = document.getElementById('login-password').value;
        const errorEl = document.getElementById('login-error');
        const btn = document.getElementById('login-submit');

        if (!email || !password) {
            if (errorEl) {
                errorEl.textContent = '请输入邮箱和密码';
                errorEl.classList.remove('u-hide');
            }
            return;
        }

        if (btn) {
            btn.disabled = true;
            btn.textContent = '登录中...';
        }
        if (errorEl) errorEl.classList.add('u-hide');

        try {
            const formData = new URLSearchParams();
            formData.append('username', email);
            formData.append('password', password);

            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                Auth.setToken(result.access_token);
                UI.showToast('登录成功', 'success');
                location.reload();
            } else {
                if (errorEl) {
                    errorEl.textContent = result.detail || '登录失败，请检查账号密码';
                    errorEl.classList.remove('u-hide');
                }
            }
        } catch (err) {
            if (errorEl) {
                errorEl.textContent = '连接服务器失败';
                errorEl.classList.remove('u-hide');
            }
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = '登录';
            }
        }
    },

    /**
     * 检查并提示 GitLab 绑定状态
     */
    async checkGitLabStatus() {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('bind_success')) {
            window.history.replaceState({}, document.title, window.location.pathname + window.location.hash);
            UI.showToast('GitLab Account Linked Successfully!', 'success');
        } else if (urlParams.get('bind_error')) {
            const error = urlParams.get('bind_error');
            window.history.replaceState({}, document.title, window.location.pathname + window.location.hash);
            UI.showToast(`GitLab Binding Failed: ${error}`, 'error');
        }
    },

    /**
     * 绑定全局静态事件
     */
    bindEvents() {
        // Hash 变化监听
        window.addEventListener('hashchange', () => {
            const view = window.location.hash.substring(1);
            if (view) this.switchView(view);
        });

        // 视图切换委托
        document.addEventListener('click', (e) => {
            const link = e.target.closest('.js-view-trigger');
            if (link && link.dataset.view) {
                e.preventDefault();
                this.switchView(link.dataset.view);
            }
        });

        // 全局导航事件监听 (支持 Web Components 触发)
        document.addEventListener('navigate', (e) => {
            const view = e.detail.view;
            if (view) this.switchView(view);
        });

        // 侧边栏折叠委派
        const sidebar = document.getElementById('sidebar-nav-container');
        if (sidebar) {
            sidebar.addEventListener('click', (e) => {
                const title = e.target.closest('.js-nav-group-title');
                if (title) {
                    const group = title.closest('.js-nav-group');
                    if (group) group.classList.toggle('expanded');
                }
            });
        }

        // --- Header & Global Actions ---
        this.bindAction('.js-btn-load-repo', () => {
            QaTestCaseHandler.load();
        });

        this.bindAction('.js-btn-open-create-modal', () => {
            QaTestCaseHandler.openModal();
        });

        this.bindAction('.js-btn-create-req', () => {
            PmRequirementHandler.openModal();
        });

        this.bindAction('.js-btn-batch-pass', () => {
            QaTestCaseHandler.batchPass();
        });

        this.bindAction('.js-btn-open-req-modal', () => {
            PmRequirementHandler.openModal();
        });

        this.bindAction('.js-btn-sync-req', () => {
            PmRequirementHandler.load();
        });

        this.bindAction('.js-btn-dedup-scan', () => {
            PmRequirementHandler.runDeduplicationScan();
        });

        this.bindAction('.js-btn-export-rtm', () => {
            UI.showToast("RTM Export coming soon...", "info");
        });

        this.bindAction('.js-btn-browse-assets', () => {
            SysUtilsHandler.loadAssetLibrary();
        });

        this.bindAction('.js-btn-open-import-modal', () => {
            UI.showModal('importModalOverlay');
        });

        this.bindAction('.js-btn-export-report', () => {
            UI.showToast("Report generation initiated...", "info");
        });

        this.bindAction('.js-logout', () => Auth.logout());

        this.bindAction('.js-btn-gitlab-bind', () => {
            window.location.href = '/auth/gitlab/bind';
        });

        // GitLab 登录按钮 (在登录 Modal 中)
        this.bindAction('#gitlab-login', () => {
            window.location.href = '/auth/gitlab/login';
        });

        this.bindAction('#login-submit', () => this.handleLocalLogin());

        // 模态框关闭及通用动作委派
        document.addEventListener('click', (e) => {
            const target = e.target;
            if (target.closest('.js-btn-close-req-modal')) PmRequirementHandler.closeModal();
            if (target.closest('.js-btn-close-import-modal')) UI.hideModal('importModalOverlay');
            if (target.closest('.js-btn-close-asset-modal')) UI.hideModal('assetModalOverlay');
            if (target.closest('.js-btn-close-code-modal')) UI.hideModal('codeModalOverlay');
            if (target.closest('.js-btn-close-conflict-modal')) UI.hideModal('conflictModalOverlay');
            if (target.closest('.js-btn-close-dedup-modal')) UI.hideModal('dedupModalOverlay');
            if (target.closest('.js-btn-close-rca-modal')) UI.hideModal('rcaModalOverlay');
            if (target.closest('.js-btn-close-gitlab-modal')) UI.hideModal('bindGitLabModal');

            // 业务提交
            if (target.closest('.js-btn-submit-req')) PmRequirementHandler.submit();
            if (target.closest('.js-btn-submit-import')) SysUtilsHandler.submitImport();
            if (target.closest('.js-btn-clone-project')) UI.showToast("Clone feature coming soon...", "info");
            if (target.closest('.js-btn-sync-tickets')) SdServiceDeskHandler.loadTickets();
        });
    },

    bindAction(selector, fn) {
        const el = document.querySelector(selector);
        if (el) el.addEventListener('click', fn);
    },

    /**
     * 初始化用户信息
     */
    async initUser() {
        if (!Auth.isLoggedIn()) {
            console.log("User not logged in, skipping user init.");
            return;
        }

        try {
            const user = await Auth.getCurrentUser();
            if (user) {
                this.state.user = user;
                this.renderUserProfile(user);
                this.renderSidebar(user);

                // 恢复上次浏览视图
                const initialView = window.location.hash.substring(1) || 'dashboard';
                this.switchView(initialView);
            }
        } catch (e) {
            console.error("User init failed", e);
        }
    },

    /**
     * 渲染个人资料卡片
     */
    renderUserProfile(user) {
        const setText = (id, txt) => {
            const el = document.getElementById(id);
            if (el) el.textContent = txt;
        };

        // Fix: Use safe access for user fields
        const displayName = user.full_name || user.username || 'User';
        setText('user-display-name', displayName);
        setText('user-avatar', (displayName.charAt(0) || 'U').toUpperCase());

        const dept = user.department?.org_name || user.department_code || 'No Dept';
        const loc = user.location?.location_name || 'Global';
        setText('user-display-dept', `${dept} • ${loc}`);

        const badge = document.getElementById('data-scope-badge-v2');
        const scopeValue = document.getElementById('scope-value-v2');
        const scopeIcon = document.getElementById('scope-icon-v2');

        if (badge && scopeValue) {
            scopeValue.textContent = loc;
            if (loc === 'Global') {
                badge.classList.add('sys-tag--global');
                if (scopeIcon) scopeIcon.textContent = '🌐';
            }
            badge.classList.add('u-inline-flex');
        }
    },

    /**
     * 渲染侧边栏 (安全方式)
     */
    renderSidebar(user) {
        const container = document.getElementById('sidebar-nav-container');
        if (!container) return;

        const isAdmin = Auth.isAdmin();
        const hasUserManage = Auth.hasPermission('USER:MANAGE');
        console.log(`RenderSidebar: isAdmin=${isAdmin}, hasUserManage=${hasUserManage}`);

        container.innerHTML = '';
        const groupTemplate = document.getElementById('sys-nav-group-tpl');
        const linkTemplate = document.getElementById('sys-nav-link-tpl');

        this.state.navConfig.forEach((group, idx) => {
            console.log(`Processing group ${idx}: ${group.title}, adminOnly=${group.adminOnly}`);
            if (group.adminOnly && !isAdmin && !hasUserManage) {
                console.log(`Skipping group ${group.title} due to missing permissions`);
                return;
            }

            const groupClone = groupTemplate.content.cloneNode(true);
            const groupEl = groupClone.querySelector('.js-nav-group');
            const groupTitle = groupClone.querySelector('.js-group-label');
            const itemsContainer = groupClone.querySelector('.js-nav-items');

            groupTitle.textContent = group.title;
            if (group.expanded) groupEl.classList.add('expanded');

            group.items.forEach(item => {
                const linkClone = linkTemplate.content.cloneNode(true);
                const linkEl = linkClone.querySelector('.js-nav-link');
                const labelEl = linkClone.querySelector('.js-link-label');
                const iconEl = linkClone.querySelector('.js-nav-icon');
                const badgeEl = linkClone.querySelector('.js-nav-badge');

                linkEl.href = item.href;
                if (item.id) linkEl.id = item.id;
                if (item.view) {
                    linkEl.classList.add('js-view-trigger');
                    linkEl.dataset.view = item.view;
                }
                if (item.target) linkEl.target = item.target;
                if (item.classes) item.classes.forEach(c => linkEl.classList.add(c));

                labelEl.textContent = item.label;
                if (item.badgeId) {
                    badgeEl.id = item.badgeId;
                }

                this.injectIcon(iconEl, item.icon);
                itemsContainer.appendChild(linkClone);
            });

            container.appendChild(groupClone);
        });
    },

    injectIcon(svgEl, iconStr) {
        const parts = iconStr.split(';');
        parts.forEach(part => {
            part = part.trim();
            if (part.startsWith('M')) {
                const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
                path.setAttribute("d", part);
                svgEl.appendChild(path);
            } else if (part.includes('=')) {
                const tag = part.split(' ')[0];
                const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
                const attrs = part.substring(tag.length).trim().split(' ');
                attrs.forEach(attr => {
                    const [k, v] = attr.split('=');
                    if (k && v) el.setAttribute(k, v.replace(/\"/g, ''));
                });
                svgEl.appendChild(el);
            }
        });
    },

    /**
     * 切换主视图区域
     */
    switchView(view) {
        console.log(`Switching to view: ${view}`);
        this.state.currentView = view;
        window.location.hash = view;

        const navItems = [
            'nav-dashboard', 'nav-tests', 'nav-test-execution', 'nav-defects', 'nav-reqs',
            'nav-matrix', 'nav-reports', 'nav-governance', 'nav-pulse', 'nav-support',
            'nav-security',
            'nav-sd-submit', 'nav-sd-my', 'nav-decision-hub', 'nav-admin-approvals',
            'nav-admin-products', 'nav-admin-okrs', 'nav-admin-projects', 'nav-admin-users', 'nav-admin-orgs'
        ];

        const viewItems = [
            'qa-dashboard-view', 'qa-case-form-view', 'qa-test-results', 'qa-stats-grid', 'qa-execution-view', 'qa-defect-view', 'pm-matrix-view',
            'pm-requirements-view', 'pm-iteration-view', 'rpt-insights-view', 'sd-support-view',
            'qa-security-view',
            'sd-submit-view', 'sd-my-view', 'sd-portal-view', 'sys-decision-hub-view', 'sys-governance-view', 'sys-pulse-view',
            'adm-approvals-view', 'adm-products-view', 'adm-okrs-view', 'adm-projects-view', 'adm-users-view', 'adm-orgs-view'
        ];

        navItems.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.classList.remove('active');
        });

        viewItems.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.classList.add('u-hide');
        });

        const activeNav = document.getElementById(`nav-${view.replace('_', '-')}`) ||
            document.querySelector(`.nav-link[data-view="${view}"]`);

        if (activeNav) {
            activeNav.classList.add('active');
            const group = activeNav.closest('.nav-group');
            if (group) group.classList.add('expanded');
        }

        const headerEl = document.getElementById('sys-header');
        const headerViews = ['dashboard', 'tests', 'test-cases'];

        if (headerEl) {
            if (headerViews.includes(view) || view === 'dashboard') {
                headerEl.classList.remove('u-hide');
                headerEl.classList.add('u-flex');
            } else {
                headerEl.classList.add('u-hide');
                headerEl.classList.remove('u-flex');
            }
        }

        this.loadViewLogic(view);
    },

    /**
     * 异步加载各视图专有逻辑
     */
    async loadViewLogic(view) {
        const show = (id, cls = 'u-block') => {
            const el = document.getElementById(id);
            if (el) { el.classList.remove('u-hide'); el.classList.add(cls); }
        };

        switch (view) {
            case 'iteration_plan':
                show('pm-iteration-view');
                const iterView = document.getElementById('pm-iteration-view');
                if (iterView && !iterView.querySelector('pm-iteration-board')) {
                    iterView.innerHTML = '';
                    const board = document.createElement('pm-iteration-board');
                    iterView.appendChild(board);
                }
                break;
            case 'dashboard':
            case 'test-cases':
            case 'tests':
                show('qa-dashboard-view', 'block');
                show('qa-test-results', 'flex');
                show('qa-stats-grid', 'grid');
                QaTestCaseHandler.load();
                SysUtilsHandler.loadExtraData();
                break;
            case 'test-case-form':
                show('qa-case-form-view');
                const formView = document.getElementById('qa-case-form-view');
                if (formView && !formView.querySelector('qa-test-case-form')) {
                    formView.innerHTML = '<qa-test-case-form></qa-test-case-form>';
                }
                break;
            case 'test-execution':
                show('qa-execution-view');
                break;
            case 'defects':
                show('qa-defect-view');
                QaDefectHandler.load();
                break;
            case 'requirements':
                show('pm-requirements-view');
                PmRequirementHandler.init();
                break;
            case 'support':
                show('sd-support-view');
                SdServiceDeskHandler.loadTickets();
                break;
            case 'matrix':
                show('pm-matrix-view');
                break;
            case 'reports':
                show('rpt-insights-view');
                RptOverviewHandler.render();
                break;
            case 'sd_submit':
                show('sd-portal-view');
                SDPortalHandler.init(); // Ensure container is ready
                SDPortalHandler.renderLanding();
                break;
            case 'sd_my':
                show('sd-portal-view');
                SDPortalHandler.init();
                SDPortalHandler.renderMyTickets();
                break;
            case 'pulse':
                show('sys-pulse-view');
                const pulseView = document.getElementById('sys-pulse-view');
                if (pulseView) {
                    pulseView.innerHTML = '';
                    const pulse = document.createElement('sys-pulse');
                    pulseView.appendChild(pulse);
                }
                break;
            case 'admin_approvals':
                show('adm-approvals-view');
                break;
            case 'admin_products':
                show('adm-products-view');
                AdmManageHandler.loadProducts();
                break;
            case 'admin_okrs':
                show('adm-okrs-view');
                AdmManageHandler.loadOkrs();
                break;
            case 'admin_projects':
                show('adm-projects-view');
                AdmManageHandler.loadProjects();
                break;
            case 'admin_users':
                show('adm-users-view');
                AdmManageHandler.initUserView();
                AdmManageHandler.loadUsers();
                break;
            case 'admin_orgs':
                show('adm-orgs-view');
                AdmManageHandler.initOrgView();
                AdmManageHandler.loadOrganizations();
                break;
            case 'security':
                show('qa-security-view');
                SecService.loadHistory();
                break;
        }
    },

    iframeLoad(id, src) {
        const frame = document.getElementById(id);
        if (frame && !frame.src.includes(src)) {
            frame.src = src;
        }
        UI.toggleLoading('', false);
    }
};

// 自动初始化
document.addEventListener('DOMContentLoaded', () => SysAppHandler.init());

// ES6 Module Export
export default SysAppHandler;
