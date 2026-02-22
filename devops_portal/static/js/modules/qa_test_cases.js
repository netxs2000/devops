/**
 * @file qa_test_cases.js
 * @description QA Test Management Controller (GitLab EE Style)
 */
import { UI } from './sys_core.js';
import { QAService } from './qa_service.js';
import QaDefectHandler from './qa_defects.js';
import SysUtilsHandler from './sys_utils.js';

// Import Components
import '../components/qa_test_case_card.component.js';
import '../components/qa_test_case_detail.component.js';
import '../components/adm_product_selector.component.js';
import '../components/qa_test_case_form.component.js';

const QaTestCaseHandler = {
    projectId: null,
    currentCase: null,
    allCases: [],  // Raw data cache for client-side filtering

    init() {
        console.log("QA Test Case Handler (GitLab Style) Initialized");
        this.bindEvents();
    },

    bindEvents() {
        const container = document.getElementById('qa-test-results');

        // Listen for events bubbled up from components
        if (container && !container.dataset.bound) {
            // 行为：点击列表行触发详情展示
            container.addEventListener('select-case', (e) => {
                this.showDetail(e.detail.item);

                // 视觉：切换 Active 状态
                container.querySelectorAll('qa-test-case-card').forEach(card => {
                    if (card.data.iid === e.detail.item.iid) {
                        card.setAttribute('active', '');
                    } else {
                        card.removeAttribute('active');
                    }
                });
            });

            container.addEventListener('execute', (e) => {
                this.handleExecution(e.detail.iid, e.detail.result, e.detail.report);
            });

            container.addEventListener('report-bug', (e) => {
                QaDefectHandler.initCreateForm(e.detail.iid);
            });

            container.dataset.bound = "true";
        }

        // Product Selector
        const selector = document.querySelector('adm-product-selector');
        if (selector && !selector.dataset.bound) {
            selector.addEventListener('change', (e) => {
                const { type, id } = e.detail;
                if (id) {
                    this.load(type, id);
                }
            });
            selector.dataset.bound = "true";
        }

        // Filter Toolbar Events
        const searchInput = document.getElementById('qa-tc-search');
        if (searchInput && !searchInput.dataset.bound) {
            searchInput.addEventListener('input', () => this.applyFilters());
            searchInput.dataset.bound = 'true';
        }
        const statusFilter = document.getElementById('qa-tc-filter-status');
        if (statusFilter && !statusFilter.dataset.bound) {
            statusFilter.addEventListener('change', () => this.applyFilters());
            statusFilter.dataset.bound = 'true';
        }
        const priorityFilter = document.getElementById('qa-tc-filter-priority');
        if (priorityFilter && !priorityFilter.dataset.bound) {
            priorityFilter.addEventListener('change', () => this.applyFilters());
            priorityFilter.dataset.bound = 'true';
        }
    },

    /**
     * 加载测试用例列表
     */
    async load(scopeType = 'project', id = null, keepDetail = false) {
        // 如果没有传入 ID，尝试从全局选择器获取
        if (!id) {
            const selector = document.querySelector('adm-product-selector');
            if (selector && selector._state) {
                scopeType = selector._state.selectedType;
                id = selector._state.selectedId;
            }
        }

        if (!id) return;

        this.projectId = (scopeType === 'product' || scopeType === 'project') ? id : null;
        this.scopeType = scopeType;

        const container = document.getElementById('qa-test-results');
        const detailPane = document.getElementById('qa-test-case-detail-pane');
        if (!container) return;

        UI.toggleLoading("Fetching Repository...", true);
        container.innerHTML = '';
        if (detailPane && !keepDetail) detailPane.classList.add('u-hide'); // 隐藏详情区，除非明确要求保留

        try {
            const data = await QAService.getTestCases(scopeType, id);
            UI.toggleLoading("", false);
            this.allCases = data; // Cache for filtering

            // Show filter toolbar
            const toolbar = document.getElementById('qa-filter-toolbar');
            if (toolbar) toolbar.classList.remove('u-hide');

            // Reset filter controls
            const searchEl = document.getElementById('qa-tc-search');
            if (searchEl) searchEl.value = '';
            const statusEl = document.getElementById('qa-tc-filter-status');
            if (statusEl) statusEl.value = 'all';
            const priorityEl = document.getElementById('qa-tc-filter-priority');
            if (priorityEl) priorityEl.value = 'all';

            if (data.length === 0) {
                container.innerHTML = `<div class="empty-state">No test cases found.</div>`;
                this.updateStats({ total: 0, passed: 0, failed: 0 });
                this._updateFilterCount(0, 0);
                return;
            }

            this.renderList(data, container);
            this._updateFilterCount(data.length, data.length);

            if (scopeType === 'project') {
                const summary = await QAService.getTestSummary(id);
                this.updateStats(summary);
            } else {
                this.calcStatsLocal(data);
            }

            SysUtilsHandler.loadExtraData();

        } catch (e) {
            UI.toggleLoading("", false);
            container.innerHTML = `<div class="u-text-error u-p-20">Failed to load: ${e.message}</div>`;
        }
    },

    renderList(data, container) {
        const frag = document.createDocumentFragment();
        data.forEach(item => {
            const card = document.createElement('qa-test-case-card');
            card.data = item;
            frag.appendChild(card);
        });
        container.appendChild(frag);
    },

    /**
     * 客户端联合筛选：搜索词 + 执行状态 + 优先级
     */
    applyFilters() {
        const keyword = (document.getElementById('qa-tc-search')?.value || '').trim().toLowerCase();
        const statusVal = document.getElementById('qa-tc-filter-status')?.value || 'all';
        const priorityVal = document.getElementById('qa-tc-filter-priority')?.value || 'all';

        let filtered = this.allCases;

        // Keyword: match iid or title
        if (keyword) {
            filtered = filtered.filter(item =>
                String(item.iid).includes(keyword) ||
                (item.title || '').toLowerCase().includes(keyword)
            );
        }

        // Status filter
        if (statusVal !== 'all') {
            filtered = filtered.filter(item => (item.result || 'pending') === statusVal);
        }

        // Priority filter
        if (priorityVal !== 'all') {
            filtered = filtered.filter(item => (item.priority || 'P2') === priorityVal);
        }

        const container = document.getElementById('qa-test-results');
        if (!container) return;

        container.innerHTML = '';
        if (filtered.length === 0) {
            container.innerHTML = `<div class="empty-state" style="padding:40px; color:#86868b;">没有匹配的用例</div>`;
        } else {
            this.renderList(filtered, container);
        }

        this._updateFilterCount(filtered.length, this.allCases.length);
    },

    _updateFilterCount(shown, total) {
        const countEl = document.getElementById('qa-tc-count-display');
        const totalEl = document.getElementById('qa-tc-total-display');
        if (countEl) countEl.textContent = shown;
        if (totalEl) totalEl.textContent = total;
    },

    /**
     * 展示 GitLab 样式的详情面板
     */
    showDetail(item) {
        this.currentCase = item;
        const pane = document.getElementById('qa-test-case-detail-pane');
        if (!pane) return;

        pane.classList.remove('u-hide');
        pane.innerHTML = '';
        const detail = document.createElement('qa-test-case-detail');
        detail.data = item;
        pane.appendChild(detail);
    },

    async handleExecution(iid, result, report = null) {
        if (!this.projectId) return UI.showToast("Project Context Lost", "error");

        try {
            await QAService.executeTest(this.projectId, iid, result, report);
            UI.showToast(`Test #${iid} marked as ${result}`, "success");

            // 为保持一致性，重新加载列表
            await this.load(this.scopeType, this.projectId, true);

            // 如果当前正在查看详情，同步更新详情视图，并恢复 Active 视觉
            if (this.currentCase && this.currentCase.iid === iid) {
                const updatedItem = { ...this.currentCase, result };
                this.showDetail(updatedItem);

                // 强制恢复 Active 项（因为 load() 重新绘制了列表）
                const container = document.getElementById('qa-test-results');
                if (container) {
                    container.querySelectorAll('qa-test-case-card').forEach(card => {
                        if (card.data.iid === iid) card.setAttribute('active', '');
                    });
                }
            }
        } catch (e) {
            UI.showToast(e.message, "error");
        }
    },

    updateStats(summary) {
        UI.animateValue('stat-passed', 0, summary.passed || 0, 500);
        UI.animateValue('stat-failed', 0, summary.failed || 0, 500);
        UI.animateValue('stat-total', 0, summary.total || 0, 500);

        const rate = summary.total > 0 ? Math.round((summary.passed / summary.total) * 100) : 0;
        UI.animateValue('stat-rate', 0, rate, 500);

        const grid = document.getElementById('qa-stats-grid');
        if (grid) {
            grid.classList.remove('u-hide');
            grid.classList.add('u-grid');
        }
    },

    calcStatsLocal(data) {
        const summary = {
            total: data.length,
            passed: data.filter(i => i.result === 'passed').length,
            failed: data.filter(i => i.result === 'failed').length
        };
        this.updateStats(summary);
    },

    openModal() {
        window.location.hash = 'test-case-form';
    }
};

export default QaTestCaseHandler;
