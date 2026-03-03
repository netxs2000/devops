/**
 * @file qa_test_case_detail.component.js
 * @description QA Test Case Detail View (GitLab Style)
 */
import { UI } from '../modules/sys_core.js';

class QaTestCaseDetail extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.item = null;
    }

    set data(item) {
        this.item = item;
        this.render();
    }

    render() {
        if (!this.item) {
            this.shadowRoot.innerHTML = `
                <div style="height: 100%; display: flex; align-items: center; justify-content: center; color: #86868b; font-size: 14px;">
                    Select a test case to view details
                </div>
            `;
            return;
        }

        const item = this.item;

        this.shadowRoot.innerHTML = `
            <style>
                :host { display: block; height: 100%; background: white; }
                .detail-container {
                    display: grid;
                    grid-template-columns: 1fr 280px;
                    height: 100%;
                }
                
                /* Main Content Area */
                .main-content {
                    padding: 32px 40px;
                    border-right: 1px solid #F0F0F0;
                    overflow-y: auto;
                }
                
                .header {
                    margin-bottom: 32px;
                    border-bottom: 1px solid #F0F0F0;
                    padding-bottom: 24px;
                }
                .iid {
                    font-family: var(--g-font-mono);
                    color: #86868b;
                    font-size: 14px;
                    margin-bottom: 8px;
                }
                .title {
                    font-size: 24px;
                    font-weight: 600;
                    color: #1d1d1f;
                    line-height: 1.3;
                }
                
                .section {
                    margin-bottom: 32px;
                }
                .section-title {
                    font-size: 13px;
                    font-weight: 600;
                    color: #86868b;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    margin-bottom: 16px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                .content-box {
                    font-size: 15px;
                    line-height: 1.6;
                    color: #1d1d1f;
                    background: #F9FAFB;
                    padding: 20px;
                    border-radius: 12px;
                    border: 1px solid #F0F0F0;
                }

                /* Steps List */
                .steps-list { counter-reset: step; }
                .step-item {
                    display: flex;
                    gap: 16px;
                    margin-bottom: 20px;
                    padding-bottom: 20px;
                    border-bottom: 1px dashed #E5E5EA;
                    transition: opacity 0.2s;
                }
                .step-item:last-child { border-bottom: none; }
                .step-item.is-completed { opacity: 0.5; }
                
                .step-check {
                    width: 20px;
                    height: 20px;
                    border-radius: 4px;
                    border: 2px solid #D2D2D7;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    margin-top: 2px;
                    flex-shrink: 0;
                    background: white;
                    transition: all 0.2s;
                }
                .step-check.is-checked {
                    background: #34C759;
                    border-color: #34C759;
                    color: white;
                }
                
                .step-num {
                    counter-increment: step;
                    width: 24px;
                    height: 24px;
                    background: #F5F5F7;
                    color: #86868b;
                    border-radius: 50%;
                    text-align: center;
                    line-height: 24px;
                    font-size: 11px;
                    font-weight: 600;
                    flex-shrink: 0;
                }
                .step-item.is-active .step-num { background: #0071e3; color: white; }

                .step-body { flex: 1; }
                .step-action { font-weight: 500; margin-bottom: 8px; }
                .step-item.is-completed .step-action { text-decoration: line-through; }
                .step-expect { color: #6e6e73; font-size: 14px; background: white; padding: 12px; border-radius: 8px; border: 1px solid #F0F0F0; margin-top: 8px; }

                /* Sidebar Area */
                .sidebar {
                    padding: 32px 24px;
                    background: #F9FAFB;
                    overflow-y: auto;
                    display: flex;
                    flex-direction: column;
                }
                
                .sidebar-group {
                    margin-bottom: 24px;
                }
                .sidebar-label {
                    font-size: 11px;
                    font-weight: 600;
                    color: #86868b;
                    text-transform: uppercase;
                    margin-bottom: 8px;
                }
                .sidebar-value {
                    font-size: 14px;
                    color: #1d1d1f;
                    font-weight: 500;
                }
                
                .status-badge {
                    display: inline-flex;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: 600;
                    text-transform: capitalize;
                }
                .status-passed { background: #E6F4EA; color: #1E8E3E; }
                .status-failed { background: #FCE8E6; color: #D93025; }
                .status-pending { background: #F1F3F4; color: #5F6368; }

                /* Actions */
                .exec-toolbar {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                    margin-top: auto;
                    padding-top: 24px;
                    border-top: 1px solid #E5E5EA;
                }
                .exec-comment {
                    width: 100%;
                    min-height: 80px;
                    border-radius: 8px;
                    border: 1px solid #D2D2D7;
                    padding: 10px;
                    font-size: 13px;
                    resize: vertical;
                    margin-bottom: 12px;
                    font-family: inherit;
                }
                .exec-comment:focus { outline: none; border-color: #0071e3; ring: 2px rgba(0,113,227,0.1); }

                .btn-exec {
                    width: 100%;
                    padding: 12px;
                    border-radius: 10px;
                    border: 1px solid #D2D2D7;
                    background: white;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 500;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                    transition: all 0.2s;
                }
                .btn-exec:hover { transform: translateY(-1px); box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
                .btn-pass:hover { background: #E6F4EA; border-color: #1E8E3E; color: #1E8E3E; }
                .btn-fail:hover { background: #FCE8E6; border-color: #D93025; color: #D93025; }
                .btn-bug { background: #1d1d1f; color: white; border: none; }
                .btn-bug:hover { opacity: 0.9; }

                .exec-env-selector {
                    width: 100%;
                    padding: 8px 10px;
                    border-radius: 8px;
                    border: 1px solid #D2D2D7;
                    background: white;
                    font-size: 13px;
                    color: #1d1d1f;
                    margin-bottom: 12px;
                    cursor: pointer;
                }
            </style>

            <div class="detail-container">
                <div class="main-content">
                    <div class="header">
                        <div class="iid">Test Case #${item.iid}</div>
                        <h1 class="title">${item.title}</h1>
                    </div>

                    <div class="section">
                        <div class="section-title">Pre-conditions</div>
                        <div class="content-box">
                            ${item.pre_conditions || 'No pre-conditions specified.'}
                        </div>
                    </div>

                    <div class="section">
                        <div class="section-title" style="display:flex; justify-content:space-between; align-items:center;">
                            Execution Steps
                            <div id="step-progress" style="font-size:12px; font-weight:500; color:#6e6e73;">0% of ${item.steps?.length || 0} items</div>
                        </div>
                        <div style="height:4px; background:#F2F2F7; border-radius:2px; margin-bottom:20px; overflow:hidden;">
                            <div id="progress-bar" style="height:100%; background:#34C759; width:0%; transition:width 0.3s ease;"></div>
                        </div>
                        <div class="steps-list">
                            ${(item.steps || []).map(s => `
                                <div class="step-item js-step-item" data-step="${s.step_number}">
                                    <div class="step-check js-step-check">
                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" style="display:none;"><polyline points="20 6 9 17 4 12"></polyline></svg>
                                    </div>
                                    <div class="step-num">${s.step_number}</div>
                                    <div class="step-body">
                                        <div class="step-action">${s.action}</div>
                                        <div class="step-expect">
                                            <span style="font-weight:600; color:#1d1d1f; font-size:11px; text-transform:uppercase; display:block; margin-bottom:4px;">Expected:</span>
                                            ${s.expected_result}
                                        </div>
                                    </div>
                                </div>
                            `).join('') || '<div style="color:#86868b; font-style:italic;">No steps defined.</div>'}
                        </div>
                    </div>
                </div>

                <div class="sidebar">
                    <div class="sidebar-group">
                        <div class="sidebar-label">Current Status</div>
                        <div class="status-badge status-${item.result || 'pending'}">
                            ${item.result || 'Pending'}
                        </div>
                    </div>

                    <div class="sidebar-group">
                        <div class="sidebar-label">Priority</div>
                        <div class="sidebar-value">${item.priority || 'P2'}</div>
                    </div>

                    <div class="sidebar-group">
                        <div class="sidebar-label">Requirement</div>
                        <div class="sidebar-value" style="color:#0071e3; cursor:pointer;">
                            ${item.requirement_id ? '#' + item.requirement_id : 'None'}
                        </div>
                    </div>

                    <div class="sidebar-group">
                        <div class="sidebar-label">Project</div>
                        <div class="sidebar-value">${item.project_name || '-'}</div>
                    </div>

                    <div class="exec-toolbar">
                        <div class="sidebar-label" style="text-align: center; margin-bottom: 8px;">Execution Feedback</div>
                        
                        <select class="exec-env-selector js-exec-env">
                            <option value="Dev">Environment: Development</option>
                            <option value="QA" selected>Environment: QA / Testing</option>
                            <option value="Pre-prod">Environment: Pre-production</option>
                            <option value="Prod">Environment: Production</option>
                        </select>

                        <textarea class="exec-comment js-exec-comment" placeholder="Add execution notes or evidence (required for failure)..."></textarea>
                        
                        <button class="btn-exec btn-pass js-exec" data-result="passed">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
                            Mark as Passed
                        </button>
                        <button class="btn-exec btn-fail js-exec" data-result="failed">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                            Mark as Failed
                        </button>
                        <button class="btn-exec btn-bug js-report-bug">
                             <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2c0 4-4 8-4 8s-4-4-4-8 4-8 4-8z"></path><path d="M8 14c0 4 4 8 4 8s4-4 4-8-4-8-4-8z"></path><circle cx="9" cy="9" r="2"></circle><circle cx="15" cy="9" r="2"></circle></svg>
                            Report Bug
                        </button>
                    </div>
                </div>
            </div>
        `;

        this.setupEvents();
    }

    setupEvents() {
        const updateProgress = () => {
            const total = this.item.steps?.length || 0;
            const completed = this.shadowRoot.querySelectorAll('.js-step-check.is-checked').length;
            const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

            const bar = this.shadowRoot.querySelector('#progress-bar');
            const text = this.shadowRoot.querySelector('#step-progress');
            if (bar) bar.style.width = `${percent}%`;
            if (text) text.textContent = `${percent}% of ${total} items`;
        };

        // Step Checklist Logic
        this.shadowRoot.querySelectorAll('.js-step-item').forEach(item => {
            const check = item.querySelector('.js-step-check');
            const svg = check.querySelector('svg');

            check.onclick = () => {
                const isChecked = check.classList.toggle('is-checked');
                item.classList.toggle('is-completed', isChecked);
                svg.style.display = isChecked ? 'block' : 'none';
                updateProgress();
            };
        });

        this.shadowRoot.querySelectorAll('.js-exec').forEach(btn => {
            btn.onclick = () => {
                const comment = this.shadowRoot.querySelector('.js-exec-comment').value;
                const env = this.shadowRoot.querySelector('.js-exec-env').value;

                // Validation: Failure requires a comment
                if (btn.dataset.result === 'failed' && !comment.trim()) {
                    return UI.showToast("Comment is required for failures", "error");
                }

                this.dispatchEvent(new CustomEvent('execute', {
                    detail: {
                        iid: this.item.iid,
                        result: btn.dataset.result,
                        report: {
                            comment: comment,
                            environment: env
                        }
                    },
                    bubbles: true,
                    composed: true
                }));
            };
        });

        const bugBtn = this.shadowRoot.querySelector('.js-report-bug');
        if (bugBtn) {
            bugBtn.onclick = () => {
                this.dispatchEvent(new CustomEvent('report-bug', {
                    detail: { iid: this.item.iid, title: this.item.title },
                    bubbles: true,
                    composed: true
                }));
            };
        }
    }
}

customElements.define('qa-test-case-detail', QaTestCaseDetail);
