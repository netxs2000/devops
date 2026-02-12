/**
 * @file pm_requirements.js
 * @description 需求管理模块 (Project Management Domain)
 *
 * 支持按 MDM 产品/组织聚合加载需求，提供即时搜索与状态/风险筛选。
 */
import { Api, UI } from './sys_core.js';
import '../components/adm_product_selector.component.js';

const PmRequirementHandler = {
    /** 模块内部状态 */
    state: {
        rawData: [],          // API 返回的全量需求数据
        riskIids: [],         // 风险需求 IID 列表
        filters: {
            keyword: '',
            status: 'all',
            risk: 'all'
        },
        currentFilter: {      // 产品/部门选择器上下文
            type: null,
            id: null
        },
        /** 当前加载模式: 'product' (聚合) 或 'project' (单项目兼容) */
        mode: null
    },

    /**
     * 初始化事件监听 (事件委派)
     */
    init() {
        const container = document.getElementById('reqResults');
        if (!container || container.dataset.initialized) return;

        // 需求卡片按钮事件委派
        container.addEventListener('click', (e) => {
            const btn = e.target.closest('button');
            if (!btn) return;

            const row = btn.closest('.js-req-card');
            if (!row) return;

            const iid = row.dataset.iid;
            const nextState = row.dataset.nextState;

            if (btn.classList.contains('js-req-next-action')) {
                this.updateReviewStatus(iid, nextState);
            } else if (btn.classList.contains('js-req-conflict-action')) {
                this.checkConflicts(iid);
            }
        });

        // 产品选择器绑定
        const selector = document.getElementById('req-product-selector');
        if (selector && !selector.dataset.bound) {
            selector.addEventListener('change', (e) => {
                const { type, id } = e.detail;
                if (id) {
                    this.state.currentFilter = { type, id };
                    this.state.mode = 'product';
                    this.loadByProduct();
                }
            });
            selector.dataset.bound = "true";
        }

        // 搜索框绑定 (防抖)
        const searchInput = document.getElementById('req-search');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce((e) => {
                this.state.filters.keyword = e.target.value.toLowerCase();
                this.applyFilters();
            }, 300));
        }

        // 下拉筛选绑定
        const statusFilter = document.getElementById('req-filter-status');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                this.state.filters.status = e.target.value;
                this.applyFilters();
            });
        }

        const riskFilter = document.getElementById('req-filter-risk');
        if (riskFilter) {
            riskFilter.addEventListener('change', (e) => {
                this.state.filters.risk = e.target.value;
                this.applyFilters();
            });
        }

        container.dataset.initialized = "true";
    },

    /**
     * 防抖函数
     */
    debounce(func, wait) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    },

    /**
     * 按产品/部门聚合加载需求 (使用追溯矩阵接口)
     */
    async loadByProduct() {
        const { type, id } = this.state.currentFilter;
        if (!type || !id) return;

        const container = document.getElementById('reqResults');
        if (!container) return;

        container.innerHTML = '<div class="empty-state">Loading Requirements...</div>';

        try {
            const params = new URLSearchParams();
            if (type === 'product') params.append('product_id', id);
            if (type === 'org') params.append('org_id', id);

            // 使用已有的聚合接口获取需求
            const data = await Api.get(
                `/test-management/aggregated/requirements?${params.toString()}`
            );

            // 将 TraceabilityMatrixItem 转换为 RequirementSummary 格式
            const reqs = (data || []).map(item => ({
                iid: item.requirement.iid,
                title: item.requirement.title,
                state: item.requirement.state,
                review_state: item.requirement.review_state,
                test_case_count: (item.test_cases || []).length,
                defect_count: (item.defects || []).length,
                mr_count: (item.merge_requests || []).length
            }));

            // 无用例的需求视为 At Risk
            const riskIids = reqs
                .filter(r => r.test_case_count === 0 && r.review_state === 'approved')
                .map(r => r.iid);

            this.state.rawData = reqs;
            this.state.riskIids = riskIids;

            // 统计数据
            const total = reqs.length;
            const approved = reqs.filter(r => r.review_state === 'approved').length;
            const covered = reqs.filter(r => r.test_case_count > 0).length;
            this.updateStats({
                coverage_rate: total > 0 ? Math.round((covered / total) * 100) : 0,
                pass_rate: 0,
                risk_requirements: riskIids.map(iid => ({ iid })),
                approved_count: approved
            });

            this.applyFilters();
        } catch (e) {
            container.innerHTML = '';
            const error = document.createElement('div');
            error.className = 'empty-state u-text-error';
            error.textContent = `Failed to load: ${e.message}`;
            container.appendChild(error);
        }
    },

    /**
     * 兼容旧的按单项目加载 (保留原有调用入口)
     */
    async load() {
        const projectIdInput = document.getElementById('projectId');
        if (!projectIdInput) return;
        const projectId = projectIdInput.value;
        if (!projectId) return;

        this.state.mode = 'project';
        const container = document.getElementById('reqResults');
        if (!container) return;

        this.init();

        container.innerHTML = '';
        const loader = document.createElement('div');
        loader.className = 'empty-state';
        loader.textContent = 'Loading Requirements...';
        container.appendChild(loader);

        try {
            const [reqs, stats] = await Promise.all([
                Api.get(`/projects/${projectId}/requirements`),
                Api.get(`/projects/${projectId}/requirements/stats`)
            ]);

            this.state.rawData = reqs.map(r => ({
                ...r,
                test_case_count: -1,
                defect_count: -1,
                mr_count: -1
            }));
            this.state.riskIids = stats.risk_requirements.map(r => r.iid);

            this.updateStats(stats);
            this.applyFilters();
        } catch (e) {
            container.innerHTML = '';
            const error = document.createElement('div');
            error.className = 'empty-state u-text-error';
            error.textContent = `Failed to load: ${e.message}`;
            container.appendChild(error);
        }
    },

    /**
     * 前端即时过滤
     */
    applyFilters() {
        const { keyword, status, risk } = this.state.filters;
        const container = document.getElementById('reqResults');

        const filtered = this.state.rawData.filter(r => {
            // 1. 关键词搜索
            if (keyword) {
                const searchStr = `${r.iid} ${r.title}`.toLowerCase();
                if (!searchStr.includes(keyword)) return false;
            }

            // 2. 状态筛选
            if (status !== 'all' && r.review_state !== status) return false;

            // 3. 风险筛选
            if (risk === 'at-risk' && !this.state.riskIids.includes(r.iid)) return false;
            if (risk === 'safe' && this.state.riskIids.includes(r.iid)) return false;

            return true;
        });

        this.updateCount(filtered.length);
        this.render(filtered, this.state.riskIids, container);
    },

    /**
     * 更新记录计数
     */
    updateCount(count) {
        const el = document.getElementById('req-count-display');
        if (el) el.textContent = count;
    },

    /**
     * 更新统计数据
     */
    updateStats(stats) {
        const fields = {
            'req-coverage-rate': `${stats.coverage_rate}%`,
            'req-pass-rate': `${stats.pass_rate}%`,
            'req-risk-count': stats.risk_requirements.length,
            'req-approved-total': stats.approved_count
        };
        for (let id in fields) {
            const el = document.getElementById(id);
            if (el) el.textContent = fields[id];
        }
    },

    /**
     * 渲染需求卡片
     */
    render(reqs, riskIids, container) {
        container.innerHTML = '';

        if (reqs.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'empty-state';
            empty.textContent = 'No matching requirements found.';
            container.appendChild(empty);
            return;
        }

        const template = document.getElementById('pm-requirement-tpl');
        const fragment = document.createDocumentFragment();

        const stateConfig = {
            'draft': { label: 'Draft', color: 'passed', next: 'under-review', nextLabel: 'Submit for Review' },
            'under-review': { label: 'Reviewing', color: 'blocked', next: 'approved', nextLabel: 'Approve' },
            'approved': { label: 'Approved', color: 'passed', next: 'rejected', nextLabel: 'Reset/Reject' },
            'rejected': { label: 'Rejected', color: 'failed', next: 'draft', nextLabel: 'Back to Draft' }
        };

        reqs.forEach(r => {
            const clone = template.content.cloneNode(true);
            const card = clone.querySelector('.js-req-card');
            const config = stateConfig[r.review_state] || stateConfig['draft'];

            card.dataset.iid = r.iid;
            card.dataset.nextState = config.next;

            const isRisk = riskIids.includes(r.iid) && r.review_state === 'approved';
            if (isRisk) card.classList.add('sys-req-at-risk-border');

            const blob = clone.querySelector('.js-req-status-blob');
            blob.classList.add(`blob-${r.review_state === 'approved' ? 'passed' : (r.review_state === 'rejected' ? 'failed' : 'pending')}`);

            clone.querySelector('.js-req-iid').textContent = `#${r.iid}`;
            if (isRisk) {
                const riskTag = clone.querySelector('.js-req-risk-tag');
                if (riskTag) riskTag.classList.remove('u-hide');
            }

            clone.querySelector('.js-req-title').textContent = r.title;

            const badge = clone.querySelector('.js-req-status-badge');
            badge.textContent = config.label;
            badge.classList.add(r.review_state === 'approved' ? 'u-bg-success-10' : (r.review_state === 'rejected' ? 'u-bg-error-10' : 'u-bg-white-03'));

            const nextBtn = clone.querySelector('.js-req-next-action');
            nextBtn.textContent = config.nextLabel;

            fragment.appendChild(clone);
        });

        container.appendChild(fragment);
    },

    /**
     * 语义冲突扫描 (单个)
     */
    async checkConflicts(iid) {
        const projectId = document.getElementById('projectId').value;
        UI.toggleLoading("Comparing with existing logic...", true);
        try {
            const data = await Api.get(`/projects/${projectId}/requirements/${iid}/conflicts`);
            const container = document.getElementById('conflictResults');
            if (container) {
                container.innerHTML = `<div class="p-4">${data.analysis || 'No immediate conflicts detected.'}</div>`;
                UI.showModal('conflictModalOverlay');
            }
        } catch (e) {
            UI.showToast("Conflict scan failed", "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 提交需求
     */
    async submit() {
        const projectIdInput = document.getElementById('projectId');
        if (!projectIdInput) return;
        const projectId = projectIdInput.value;
        if (!projectId) return alert("Select a project first");

        const titleInput = document.getElementById('req_title');
        const valueInput = document.getElementById('req_value');

        const payload = {
            title: titleInput ? titleInput.value : '',
            priority: document.getElementById('req_priority')?.value || 'P2',
            category: document.getElementById('req_category')?.value || 'Functional',
            business_value: valueInput ? valueInput.value : '',
            acceptance_criteria: Array.from(document.querySelectorAll('#acContainer .ac-row input')).map(i => i.value).filter(v => v)
        };

        if (!payload.title) return alert("Title is mandatory");

        UI.toggleLoading("Engineering Requirement to GitLab...", true);

        try {
            const data = await Api.post(`/projects/${projectId}/requirements`, payload);
            UI.showToast("DOR Passed: Requirement deployed!", "success");
            this.closeModal();
            this.load();
        } catch (e) {
            UI.showToast("DOR Violation: " + e.message, "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 更新审核状态
     */
    async updateReviewStatus(iid, nextState) {
        const projectIdInput = document.getElementById('projectId');
        if (!projectIdInput) return;
        const projectId = projectIdInput.value;
        UI.toggleLoading("Updating review state...", true);
        try {
            await Api.post(`/projects/${projectId}/requirements/${iid}/review?review_state=${nextState}`);
            UI.showToast("State updated.", "success");
            this.load();
        } catch (e) {
            UI.showToast(e.message, "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 语义冲突扫描
     */
    async runDeduplicationScan() {
        const projectIdInput = document.getElementById('projectId');
        if (!projectIdInput) return;
        const projectId = projectIdInput.value;
        if (!projectId) return alert("Select a project first");

        UI.toggleLoading("AI Semantic Scanning...", true);

        try {
            const data = await Api.get(`/projects/${projectId}/deduplication/scan?type=requirement`);

            const savingVal = document.getElementById('dedup-saving-val');
            const groupCount = document.getElementById('dedup-group-count');
            if (savingVal) savingVal.textContent = `${data.saving_potential}%`;
            if (groupCount) groupCount.textContent = data.total_groups;

            const list = document.getElementById('dedup-results-list');
            if (!list) return;

            list.innerHTML = '';
            if (data.clusters.length === 0) {
                const empty = document.createElement('div');
                empty.className = 'empty-state';
                empty.textContent = 'No duplicates detected.';
                list.appendChild(empty);
            } else {
                data.clusters.forEach(c => {
                    const groupDiv = document.createElement('div');
                    groupDiv.className = 'dedup-group';

                    const primeDiv = document.createElement('div');
                    primeDiv.className = 'prime-issue';
                    const primeB = document.createElement('b');
                    primeB.textContent = 'PRIME:';
                    primeDiv.appendChild(primeB);
                    primeDiv.appendChild(document.createTextNode(` #${c.prime.iid} `));
                    const primeTitle = document.createElement('span');
                    primeTitle.textContent = c.prime.title;
                    primeDiv.appendChild(primeTitle);
                    groupDiv.appendChild(primeDiv);

                    c.duplicates.forEach(d => {
                        const dupDiv = document.createElement('div');
                        dupDiv.className = 'dup-issue';
                        dupDiv.textContent = `Similar: #${d.iid} `;
                        const dupTitle = document.createElement('span');
                        dupTitle.textContent = d.title;
                        dupDiv.appendChild(dupTitle);
                        groupDiv.appendChild(dupDiv);
                    });

                    const actDiv = document.createElement('div');
                    actDiv.className = 'u-mt-10';
                    const btn = document.createElement('button');
                    btn.className = 'btn-primary btn-merge-prime';
                    btn.textContent = 'Merge into Prime';
                    actDiv.appendChild(btn);
                    groupDiv.appendChild(actDiv);

                    list.appendChild(groupDiv);
                });
            }
            UI.showModal('dedupModalOverlay');
        } catch (e) {
            UI.showToast("AI Scan Error: " + e.message, "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    openModal() { UI.showModal('reqModalOverlay'); },
    closeModal() { UI.hideModal('reqModalOverlay'); }
};

export default PmRequirementHandler;
