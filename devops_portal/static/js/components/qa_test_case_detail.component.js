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
                }
                .step-item:last-child { border-bottom: none; }
                
                .step-num {
                    counter-increment: step;
                    width: 24px;
                    height: 24px;
                    background: #0071e3;
                    color: white;
                    border-radius: 50%;
                    text-align: center;
                    line-height: 24px;
                    font-size: 12px;
                    font-weight: 600;
                    flex-shrink: 0;
                }
                .step-body { flex: 1; }
                .step-action { font-weight: 500; margin-bottom: 8px; }
                .step-expect { color: #6e6e73; font-size: 14px; background: white; padding: 12px; border-radius: 8px; border: 1px solid #F0F0F0; margin-top: 8px; }

                /* Sidebar Area */
                .sidebar {
                    padding: 32px 24px;
                    background: #F9FAFB;
                    overflow-y: auto;
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
                    margin-top: 32px;
                    padding-top: 24px;
                    border-top: 1px solid #E5E5EA;
                }
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
                .btn-pass:hover { background: #E6F4EA; border-color: #1E8E3E; color: #1E8E3E; }
                .btn-fail:hover { background: #FCE8E6; border-color: #D93025; color: #D93025; }
                .btn-bug { background: #1d1d1f; color: white; border: none; }
                .btn-bug:hover { opacity: 0.9; }
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
                        <div class="section-title">Execution Steps</div>
                        <div class="steps-list">
                            ${(item.steps || []).map(s => `
                                <div class="step-item">
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
                        <div class="sidebar-label" style="text-align: center; margin-bottom: 4px;">Quick Execute</div>
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
        this.shadowRoot.querySelectorAll('.js-exec').forEach(btn => {
            btn.onclick = () => {
                this.dispatchEvent(new CustomEvent('execute', {
                    detail: { iid: this.item.iid, result: btn.dataset.result },
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
