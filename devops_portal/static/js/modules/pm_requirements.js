import { Api, UI } from './sys_core.js';

const PmRequirementHandler = {
    /**
     * 初始化事件监听 (事件委派)
     */
    init() {
        const container = document.getElementById('reqResults');
        if (!container || container.dataset.initialized) return;

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

        container.dataset.initialized = "true";
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
     * 加载需求列表
     */
    async load() {
        const projectIdInput = document.getElementById('projectId');
        if (!projectIdInput) return;
        const projectId = projectIdInput.value;
        if (!projectId) return;

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

            this.updateStats(stats);
            this.render(reqs, stats.risk_requirements.map(r => r.iid), container);
        } catch (e) {
            container.innerHTML = '';
            const error = document.createElement('div');
            error.className = 'empty-state u-text-error';
            error.textContent = `Failed to load: ${e.message}`;
            container.appendChild(error);
        }
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
            empty.textContent = 'No requirements. Click "+ Req" to add.';
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

        UI.toggleLoading("📐 Engineering Requirement to GitLab...", true);

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

        UI.toggleLoading("🧠 AI Semantic Scanning...", true);

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
                empty.textContent = 'No duplicates detected. ✨';
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
