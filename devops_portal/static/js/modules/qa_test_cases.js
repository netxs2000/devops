/**
 * @file qa_test_cases.js
 * @description QA Test Management Controller (Refactored)
 */
import { UI } from './sys_core.js';
import { QAService } from './qa_service.js';
import QaDefectHandler from './qa_defects.js';
import SysUtilsHandler from './sys_utils.js';

// Import CSS for Components (if needed globally) or rely on shadow DOM styles
import '../components/qa_test_case_card.component.js';
import '../components/adm_product_selector.component.js';

const QaTestCaseHandler = {
    projectId: null,

    init() {
        console.log("QA Test Case Handler Initialized");
        this.bindEvents();
    },

    bindEvents() {
        const container = document.getElementById('qa-test-results');

        // Listen for events bubbled up from components
        if (container && !container.dataset.bound) {
            container.addEventListener('execute', (e) => {
                this.handleExecution(e.detail.iid, e.detail.result);
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

        // Modal Logic (Create Case) remains in main DOM for now or can be refactored to component later
        this.bindModalEvents();
    },

    bindModalEvents() {
        const modal = document.getElementById('modalOverlay');
        if (modal && !modal.dataset.bound) {
            modal.addEventListener('click', (e) => {
                const t = e.target;
                if (t.classList.contains('js-btn-submit-case')) this.submitCreate();
                if (t.classList.contains('js-btn-close-modal')) this.closeModal();
                if (t.classList.contains('js-btn-add-step')) this.addStepRow();
                if (t.classList.contains('js-btn-ai-generate')) this.generateMagicSteps();
            });
            modal.dataset.bound = "true";
        }
    },

    /**
     * Load Test Cases
     * @param {string} scopeType - 'project' | 'product' | 'org' (default based on inputs)
     * @param {string} id - ID
     */
    async load(scopeType = 'project', id = null) {
        // Fallback to manual input if no ID passed (legacy mode)
        if (!id) {
            id = document.getElementById('projectId')?.value;
            if (!id && !scopeType) return;
        }

        this.projectId = (scopeType === 'project') ? id : null; // Track current project context

        const container = document.getElementById('qa-test-results');
        if (!container) return;

        UI.toggleLoading("Syncing Test Cases...", true);
        container.innerHTML = ''; // Clear old content

        try {
            // 1. Fetch Data
            const data = await QAService.getTestCases(scopeType, id);

            UI.toggleLoading("", false);

            if (data.length === 0) {
                container.innerHTML = `<div class="empty-state">No test cases found for ${scopeType} ${id}.</div>`;
                this.updateStats({ total: 0, passed: 0, failed: 0 });
                return;
            }

            // 2. Render Cards
            this.renderList(data, container);

            // 3. Update Stats (Client-side calc for aggregated, or fetch summary for project)
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

    async handleExecution(iid, result) {
        if (!this.projectId) return UI.showToast("Project Context Lost. Please reload.", "error");

        try {
            await QAService.executeTest(this.projectId, iid, result);
            UI.showToast(`Test #${iid} marked as ${result}`, "success");

            // Update UI card state instantly without reload
            const card = document.querySelector(`qa-test-case-card`);
            // In a real list, we need to find the specific element. 
            // Since we don't have IDs on the element itself easily unless we set them.
            // Let's re-fetch for simplicity or update data.
            this.load('project', this.projectId);
        } catch (e) {
            UI.showToast(e.message, "error");
        }
    },

    // --- Create Modal Logic (Simplified) ---

    openModal() {
        UI.showModal('modalOverlay');
        this.resetForm();
    },

    closeModal() {
        UI.hideModal('modalOverlay');
    },

    resetForm() {
        const fields = ['new_title', 'new_req_iid', 'new_pre'];
        fields.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
        document.getElementById('stepsContainer').innerHTML = '';
        this.addStepRow(); // Add one initial row
    },

    addStepRow() {
        const container = document.getElementById('stepsContainer');
        const row = document.createElement('div');
        row.className = 'step-row u-flex u-gap-10 u-mb-8';
        row.innerHTML = `<input type="text" placeholder="Action" class="form-control step-action u-span-2 u-flex-2"><input type="text" placeholder="Expected" class="form-control step-expected u-flex-1">`;
        container.appendChild(row);
    },

    async generateMagicSteps() {
        // ... (AI Logic reuse QAService)
        const reqIid = document.getElementById('new_req_iid').value;
        if (!reqIid || !this.projectId) return UI.showToast("Req ID & Project Context required", "warning");

        UI.toggleLoading("AI Generating...", true);
        try {
            const data = await QAService.suggestSteps(this.projectId, reqIid);
            if (data.steps) {
                const container = document.getElementById('stepsContainer');
                container.innerHTML = '';
                data.steps.forEach(s => {
                    const row = document.createElement('div');
                    row.className = 'step-row u-flex u-gap-10 u-mb-8';
                    row.innerHTML = `<input type="text" value="${s.action}" class="form-control step-action u-span-2 u-flex-2"><input type="text" value="${s.expected}" class="form-control step-expected u-flex-1">`;
                    container.appendChild(row);
                });
            }
        } catch (e) { UI.showToast(e.message, "error"); }
        finally { UI.toggleLoading("", false); }
    },

    async submitCreate() {
        const title = document.getElementById('new_title').value;
        if (!title || !this.projectId) return UI.showToast("Title & Project required", "warning");

        const steps = [];
        document.querySelectorAll('#stepsContainer .step-row').forEach((row, idx) => {
            const action = row.querySelector('.step-action').value;
            const expected = row.querySelector('.step-expected').value;
            if (action) steps.push({ step_number: idx + 1, action, expected_result: expected });
        });

        const payload = {
            title,
            requirement_id: parseInt(document.getElementById('new_req_iid').value) || null,
            priority: document.getElementById('new_priority').value,
            test_type: document.getElementById('new_type').value,
            pre_conditions: document.getElementById('new_pre').value.split('\n').filter(l => l.trim()),
            steps
        };

        try {
            await QAService.createTestCase(this.projectId, payload);
            UI.showToast("Created!", "success");
            this.closeModal();
            this.load('project', this.projectId);
        } catch (e) {
            UI.showToast(e.message, "error");
        }
    }
};

export default QaTestCaseHandler;
