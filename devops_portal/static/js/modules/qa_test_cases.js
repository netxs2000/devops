import { Api, UI } from './sys_core.js';
import QaDefectHandler from './qa_defects.js';
import SysUtilsHandler from './sys_utils.js';

const QaTestCaseHandler = {
    selectedIids: new Set(),

    /**
     * 初始化事件监听器 (事件委派)
     */
    init() {
        const container = document.getElementById('qa-test-results');
        if (container && !container.dataset.initialized) {
            container.addEventListener('click', (e) => {
                const target = e.target;

                // 1. 处理选择框
                const selector = target.closest('.js-case-selector');
                if (selector) {
                    const row = selector.closest('.js-test-card');
                    this.toggleSelection(row, selector);
                    return;
                }

                // 2. 处理展开/收起
                const toggleHeader = target.closest('.js-case-toggle');
                if (toggleHeader) {
                    const row = toggleHeader.closest('.js-test-card');
                    this.toggleTestCase(row);
                    return;
                }

                // 3. 处理执行按钮
                const shelfBtn = target.closest('.btn-shelf');
                if (shelfBtn) {
                    const row = shelfBtn.closest('.js-test-card');
                    const iid = row.dataset.iid;

                    if (shelfBtn.classList.contains('js-btn-pass')) this.executeTest(iid, 'passed', shelfBtn);
                    else if (shelfBtn.classList.contains('js-btn-fail')) this.executeTest(iid, 'failed', shelfBtn);
                    else if (shelfBtn.classList.contains('js-btn-block')) this.executeTest(iid, 'blocked', shelfBtn);
                    else if (shelfBtn.classList.contains('js-btn-bug')) {
                        QaDefectHandler.initCreateForm(iid);
                    }
                    else if (shelfBtn.classList.contains('js-btn-ack')) this.ackTestChange(iid);
                    else if (shelfBtn.classList.contains('js-btn-magic')) {
                        this.generateMagicCode(iid);
                    }
                }
            });
            container.dataset.initialized = "true";
        }

        // 绑定 Modal 事件 (仅初始化一次)
        const modal = document.getElementById('modalOverlay');
        if (modal && !modal.dataset.initialized) {
            modal.addEventListener('click', (e) => {
                const target = e.target;
                if (target.classList.contains('js-btn-add-step')) this.addStepRow();
                if (target.classList.contains('js-btn-close-modal')) this.closeModal();
                if (target.classList.contains('js-btn-submit-case')) this.submit();
                if (target.classList.contains('js-btn-ai-generate')) this.generateMagicSteps();
            });
            modal.dataset.initialized = "true";
        }
    },

    /**
     * 打开创建模态框
     */
    openModal() {
        this.init();
        UI.showModal('modalOverlay');
    },

    /**
     * 关闭模态框
     */
    closeModal() {
        UI.hideModal('modalOverlay');
        this.resetForm();
    },

    /**
     * 重置表单
     */
    resetForm() {
        const fields = ['new_title', 'new_req_iid', 'new_pre'];
        fields.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        const container = document.getElementById('stepsContainer');
        if (container) {
            container.innerHTML = `
                <div class="step-row u-flex u-gap-10 u-mb-8">
                    <input type="text" placeholder="Action" class="form-control step-action u-span-2 u-flex-2">
                    <input type="text" placeholder="Expected" class="form-control step-expected u-flex-1">
                </div>`;
        }
    },

    /**
     * 添加步骤行
     */
    addStepRow() {
        const container = document.getElementById('stepsContainer');
        if (!container) return;
        const row = document.createElement('div');
        row.className = 'step-row u-flex u-gap-10 u-mb-8';
        row.innerHTML = `
            <input type="text" placeholder="Action" class="form-control step-action u-span-2 u-flex-2">
            <input type="text" placeholder="Expected" class="form-control step-expected u-flex-1">
        `;
        container.appendChild(row);
    },

    /**
     * AI 生成步骤
     */
    async generateMagicSteps() {
        const reqIid = document.getElementById('new_req_iid').value;
        const projectId = document.getElementById('projectId').value;

        if (!reqIid) return UI.showToast("Please provide Requirement IID", "warning");

        UI.toggleLoading("AI is thinking...", true);
        try {
            const data = await Api.get(`/projects/${projectId}/requirements/${reqIid}/suggest-test-steps`);
            const container = document.getElementById('stepsContainer');
            if (container && data.steps) {
                container.innerHTML = '';
                data.steps.forEach(s => {
                    const row = document.createElement('div');
                    row.className = 'step-row u-flex u-gap-10 u-mb-8';
                    row.innerHTML = `
                        <input type="text" value="${s.action}" class="form-control step-action u-span-2 u-flex-2">
                        <input type="text" value="${s.expected}" class="form-control step-expected u-flex-1">
                    `;
                    container.appendChild(row);
                });
                UI.showToast("AI Generated Steps added", "success");
            }
        } catch (e) {
            UI.showToast("AI Generation Failed: " + e.message, "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 提交新用例
     */
    async submit() {
        const projectId = document.getElementById('projectId').value;
        const title = document.getElementById('new_title').value;
        if (!title) return UI.showToast("Title is required", "warning");

        const steps = [];
        document.querySelectorAll('#stepsContainer .step-row').forEach((row, idx) => {
            const action = row.querySelector('.step-action').value;
            const expected = row.querySelector('.step-expected').value;
            if (action) {
                steps.push({
                    step_number: idx + 1,
                    action,
                    expected_result: expected
                });
            }
        });

        const payload = {
            title,
            requirement_id: parseInt(document.getElementById('new_req_iid').value) || null,
            priority: document.getElementById('new_priority').value,
            test_type: document.getElementById('new_type').value,
            pre_conditions: document.getElementById('new_pre').value.split('\n').filter(l => l.trim()),
            steps
        };

        UI.toggleLoading("Creating GitLab Issue...", true);
        try {
            await Api.post(`/projects/${projectId}/test-cases`, payload);
            UI.showToast("Test Case created successfully!", "success");
            this.closeModal();
            this.load();
        } catch (err) {
            UI.showToast("Creation failed: " + err.message, "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * Magic Code (AI 代码生成建议)
     */
    async generateMagicCode(iid) {
        const projectId = document.getElementById('projectId').value;
        UI.toggleLoading("Generating automation snippet...", true);
        try {
            const data = await Api.get(`/projects/${projectId}/test-cases/${iid}/suggest-code`);
            const display = document.getElementById('code-display');
            if (display) {
                display.textContent = data.code;
                UI.showModal('codeModalOverlay');
            }
        } catch (e) {
            UI.showToast("Code generation failed", "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 加载测试用例
     */
    async load(silent = false) {
        const projectIdInput = document.getElementById('projectId');
        if (!projectIdInput) return;
        const projectId = projectIdInput.value;
        if (!projectId) return alert("Project ID Required");

        const container = document.getElementById('qa-test-results');
        if (!container) return;

        this.init(); // 确保委派已初始化

        if (!silent) {
            container.innerHTML = '';
            const loader = document.createElement('div');
            loader.className = 'empty-state';
            loader.textContent = 'Decoding GitLab Objects...';
            container.appendChild(loader);
            UI.toggleLoading("Decoding GitLab Objects...", true);
        }

        try {
            const [data, summary] = await Promise.all([
                Api.get(`/projects/${projectId}/test-cases`),
                Api.get(`/projects/${projectId}/test-summary`)
            ]);

            UI.toggleLoading("", false);

            const titleEl = document.getElementById('projectTitle');
            if (titleEl) {
                titleEl.textContent = `Viewing Suite for PID: ${projectId} • ${data.length} Scenarios`;
            }

            this.updateSummaryStats(data, summary);

            if (data.length === 0) {
                container.innerHTML = '';
                const empty = document.createElement('div');
                empty.className = 'empty-state';
                empty.textContent = 'No structured "type::test" issues found.';
                container.appendChild(empty);
                return;
            }

            this.render(data, container);

            SysUtilsHandler.loadExtraData();
        } catch (err) {
            UI.toggleLoading("", false);
            console.error(err);
            UI.showToast("Sync Failed: " + err.message, "error");
        }
    },

    /**
     * 更新统计
     */
    updateSummaryStats(data, summary) {
        let totalBugs = 0;
        data.forEach(item => totalBugs += (item.linked_bugs ? item.linked_bugs.length : 0));

        const getVal = (id) => {
            const el = document.getElementById(id);
            return el ? parseInt(el.textContent) || 0 : 0;
        };

        UI.animateValue('stat-passed', getVal('stat-passed'), summary.passed, 500);
        UI.animateValue('stat-failed', getVal('stat-failed'), summary.failed, 500);
        UI.animateValue('stat-total', getVal('stat-total'), summary.total, 500);
        UI.animateValue('stat-bugs', getVal('stat-bugs'), totalBugs, 500);

        const bugAlert = document.getElementById('bug-alert-icon');
        if (bugAlert) {
            if (totalBugs > 5) {
                bugAlert.classList.remove('u-hide');
                bugAlert.classList.add('u-block');
            } else {
                bugAlert.classList.add('u-hide');
                bugAlert.classList.remove('u-block');
            }
        }

        const rate = summary.total > 0 ? Math.round((summary.passed / summary.total) * 100) : 0;
        UI.animateValue('stat-rate', getVal('stat-rate'), rate, 500);

        const grid = document.getElementById('qa-stats-grid');
        if (grid) {
            grid.classList.remove('u-hide');
            grid.classList.add('u-grid');
        }
    },

    /**
     * 渲染卡片
     */
    render(data, container) {
        container.innerHTML = '';
        const template = document.getElementById('qa-test-case-tpl');
        const stepTemplate = document.getElementById('qa-test-step-tpl');
        const fragment = document.createDocumentFragment();

        data.forEach(item => {
            const clone = template.content.cloneNode(true);
            const card = clone.querySelector('.js-test-card');

            card.dataset.iid = item.iid;
            card.classList.add(`card-${item.iid}`);

            // 头部填充
            clone.querySelector('.js-status-blob').classList.add(`blob-${item.result}`);
            clone.querySelector('.js-case-iid').textContent = `#${item.iid}`;
            clone.querySelector('.js-case-title').textContent = item.title;

            const isStale = (item.labels || []).includes('status::stale');
            if (isStale) {
                clone.querySelector('.js-stale-badge').classList.remove('u-hide');
                clone.querySelector('.js-btn-ack').classList.remove('u-hide');
            }

            clone.querySelector('.js-tag-priority').textContent = item.priority;
            clone.querySelector('.js-tag-priority').classList.add(`tag-priority-${item.priority}`);
            clone.querySelector('.js-tag-type').textContent = item.test_type;

            // 内容填充
            const stepsContainer = clone.querySelector('.js-steps-container');
            if (item.steps && item.steps.length > 0) {
                item.steps.forEach(s => {
                    const sClone = stepTemplate.content.cloneNode(true);
                    sClone.querySelector('.js-step-num').textContent = s.step_number;
                    sClone.querySelector('.js-step-action').textContent = s.action;
                    sClone.querySelector('.js-step-expected').textContent = s.expected_result;
                    stepsContainer.appendChild(sClone);
                });
            } else {
                const emptySteps = document.createElement('p');
                emptySteps.className = 'u-text-dim';
                emptySteps.textContent = 'No steps.';
                stepsContainer.appendChild(emptySteps);
            }

            clone.querySelector('.js-meta-req').textContent = item.requirement_id ? `#${item.requirement_id}` : 'None';

            // Bug Pills (Safe)
            const bugContainer = clone.querySelector('.js-meta-bugs');
            if (item.linked_bugs && item.linked_bugs.length > 0) {
                item.linked_bugs.forEach(b => {
                    const span = document.createElement('span');
                    span.className = 'bug-pill';
                    span.textContent = `#${b.iid}`;
                    bugContainer.appendChild(span);
                });
            } else {
                const noBugs = document.createElement('span');
                noBugs.className = 'u-text-dim';
                noBugs.textContent = 'No defects';
                bugContainer.appendChild(noBugs);
            }

            clone.querySelector('.js-meta-pre').textContent = item.pre_conditions.join('\n') || 'None';
            clone.querySelector('.js-case-link').href = item.web_url;

            fragment.appendChild(clone);
        });

        container.appendChild(fragment);
    },

    /**
     * 切换选择
     */
    toggleSelection(row, checkbox) {
        const iid = row.dataset.iid;
        if (this.selectedIids.has(iid)) {
            this.selectedIids.delete(iid);
            checkbox.classList.remove('checked');
        } else {
            this.selectedIids.add(iid);
            checkbox.classList.add('checked');
        }
    },

    /**
     * 展开/收起
     */
    toggleTestCase(row) {
        const content = row.querySelector('.js-case-content');
        const isActive = content.classList.contains('active');

        // 可选：收起其它所有
        document.querySelectorAll('.js-case-content').forEach(c => c.classList.remove('active'));

        if (!isActive) {
            content.classList.add('active');
        }
    },

    /**
     * 单个用例执行
     */
    async executeTest(iid, result, btn) {
        const projectId = document.getElementById('projectId').value;
        const originalText = btn.textContent;

        btn.disabled = true;
        btn.textContent = "Submitting...";

        try {
            const data = await Api.post(`/projects/${projectId}/test-cases/${iid}/execute?result=${result}`);
            if (data.status === 'success') {
                const blob = document.querySelector(`.card-${iid} .js-status-blob`);
                if (blob) {
                    blob.className = 'status-blob js-status-blob'; // Reset
                    blob.classList.add(`blob-${result}`);
                }
                UI.showToast(`Test #${iid} marked as ${result}`, "success");
                this.load(true); // 静默刷新
            }
        } catch (err) {
            UI.showToast("Execution Error: " + err.message, "error");
            btn.disabled = false;
            btn.textContent = originalText;
        }
    },

    /**
     * 批量通过
     */
    async batchPass() {
        if (this.selectedIids.size === 0) return alert("Please select test cases first");
        const projectIdInput = document.getElementById('projectId');
        if (!projectIdInput) return;
        const projectId = projectIdInput.value;

        if (!confirm(`Mark ${this.selectedIids.size} cases as PASSED?`)) return;

        UI.toggleLoading(`Batch Processing ${this.selectedIids.size} items...`, true);

        try {
            const tasks = Array.from(this.selectedIids).map(iid =>
                Api.post(`/projects/${projectId}/test-cases/${iid}/execute?result=passed`)
            );
            await Promise.all(tasks);
            this.selectedIids.clear();
            UI.showToast("Batch execution completed!", "success");
            this.load();
        } catch (err) {
            UI.showToast("Batch execution failed: " + err.message, "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 同步需求变更
     */
    async ackTestChange(iid) {
        const projectIdInput = document.getElementById('projectId');
        if (!projectIdInput) return;
        const projectId = projectIdInput.value;
        try {
            await Api.post(`/projects/${projectId}/test-cases/${iid}/ack`, {});
            UI.showToast(`Test #${iid} synced and active.`, "success");
            this.load();
        } catch (e) {
            UI.showToast("Failed to acknowledge change: " + e.message, "error");
        }
    }
};

export default QaTestCaseHandler;
