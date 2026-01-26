/**
 * @file qa_test_case_card.component.js
 * @description QA Test Case Row/Card Component
 */
import '../components/qa_priority_badge.component.js';

class QaTestCaseCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.isOpen = false;
        this.item = null;
    }

    set data(item) {
        this.item = item;
        this.render();
    }

    get data() {
        return this.item;
    }

    connectedCallback() {
        // Initial render if data not set yet
        if (!this.item) this.render();
    }

    toggle() {
        this.isOpen = !this.isOpen;
        const content = this.shadowRoot.querySelector('.content');
        const icon = this.shadowRoot.querySelector('.expand-icon');

        if (this.isOpen) {
            content.classList.add('open');
            icon.style.transform = 'rotate(90deg)';
        } else {
            content.classList.remove('open');
            icon.style.transform = 'rotate(0deg)';
        }
    }

    render() {
        if (!this.item) return;
        const item = this.item;

        // Status Colors (matching Blob)
        const statusColors = {
            'passed': '#34C759',
            'failed': '#FF3B30',
            'pending': '#8E8E93',
            'blocked': '#FF9500',
            'skipped': '#8E8E93'
        };
        const statusColor = statusColors[item.result] || '#8E8E93';

        this.shadowRoot.innerHTML = `
            <style>
                :host { display: block; margin-bottom: 12px; }
                .card {
                    background: white;
                    border: 1px solid rgba(0,0,0,0.05);
                    border-radius: 12px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
                    overflow: hidden;
                    transition: all 0.2s ease;
                }
                .card:hover {
                    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                    transform: translateY(-1px);
                }
                
                /* Header */
                .header {
                    display: grid;
                    grid-template-columns: 24px 4px 60px 1fr auto;
                    align-items: center;
                    padding: 16px 20px;
                    gap: 16px;
                    cursor: pointer;
                    user-select: none;
                }
                
                .expand-icon {
                    color: #8E8E93;
                    transition: transform 0.2s;
                }
                
                .status-blob {
                    width: 4px;
                    height: 4px;
                    border-radius: 2px;
                    background: ${statusColor};
                    height: 24px;
                }
                
                .iid {
                    font-family: 'SF Mono', 'Menlo', monospace;
                    font-size: 13px;
                    color: #86868b;
                }
                
                .title-area {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                .title {
                    font-size: 15px;
                    font-weight: 500;
                    color: #1d1d1f;
                }
                .project-tag {
                    font-size: 11px;
                    padding: 2px 6px;
                    border-radius: 4px;
                    background: #F5F5F7;
                    color: #1d1d1f;
                }
                
                .actions {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }
                
                /* Content (Expanded) */
                .content {
                    display: none;
                    border-top: 1px solid #F5F5F7;
                    background: #FAFAFA;
                    padding: 24px;
                }
                .content.open { display: grid; grid-template-columns: 2fr 1fr; gap: 32px; }
                
                /* Steps */
                .steps-list { counter-reset: step; }
                .step-item {
                    display: flex;
                    gap: 16px;
                    margin-bottom: 12px;
                    font-size: 14px;
                }
                .step-num {
                    counter-increment: step;
                    width: 20px;
                    height: 20px;
                    background: #E5E5EA;
                    color: #1d1d1f;
                    border-radius: 50%;
                    text-align: center;
                    line-height: 20px;
                    font-size: 11px;
                    font-weight: 600;
                    flex-shrink: 0;
                }
                .step-desc { flex: 1; }
                .step-expect { flex: 1; color: #6e6e73; border-left: 2px solid #E5E5EA; padding-left: 12px; }
                
                /* Shelf (Exec Buttons) */
                .shelf {
                    display: flex;
                    gap: 8px;
                    flex-wrap: wrap;
                    align-content: flex-start;
                }
                .btn {
                    border: none;
                    background: white;
                    padding: 8px 16px;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 500;
                    cursor: pointer;
                    border: 1px solid #E5E5EA;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    transition: all 0.1s;
                }
                .btn:hover { transform: scale(1.02); }
                .btn-pass { color: #34C759; border-color: #34C759; background: #F2FBF5; }
                .btn-fail { color: #FF3B30; border-color: #FF3B30; background: #FFF0F0; }
                .btn-block { color: #FF9500; border-color: #FF9500; background: #FFF8E5; }
                .btn-bug { color: #1d1d1f; border-color: #1d1d1f; }
                
                .meta-group { margin-top: 24px; font-size: 12px; color: #86868b; }
                .meta-row { display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px dashed #E5E5EA; padding-bottom: 4px; }
            </style>

            <div class="card">
                <div class="header js-toggle">
                    <svg class="expand-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="9 18 15 12 9 6"></polyline>
                    </svg>
                    <div class="status-blob"></div>
                    <div class="iid">#${item.iid}</div>
                    <div class="title-area">
                        <span class="title">${item.title}</span>
                        ${item.project_name ? `<span class="project-tag">${item.project_name}</span>` : ''}
                    </div>
                    <div class="actions">
                        <qa-priority-badge level="${item.priority}"></qa-priority-badge>
                        <qa-priority-badge status="${item.result}"></qa-priority-badge>
                    </div>
                </div>

                <div class="content">
                    <div class="left-col">
                        <h4 style="margin: 0 0 16px 0; font-size: 13px; color:#86868b; text-transform:uppercase;">Test Steps</h4>
                        <div class="steps-list">
                            ${(item.steps || []).map(s => `
                                <div class="step-item">
                                    <div class="step-num">${s.step_number}</div>
                                    <div class="step-desc">${s.action}</div>
                                    <div class="step-expect">${s.expected_result}</div>
                                </div>
                            `).join('') || '<div class="step-item" style="color:#86868b; font-style:italic;">No steps defined.</div>'}
                        </div>
                    </div>
                    
                    <div class="right-col">
                        <div class="shelf">
                            <button class="btn btn-pass js-exec" data-result="passed">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>
                                Pass
                            </button>
                            <button class="btn btn-fail js-exec" data-result="failed">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                                Fail
                            </button>
                            <button class="btn btn-block js-exec" data-result="blocked">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><circle cx="12" cy="12" r="10"></circle><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line></svg>
                                Block
                            </button>
                            <button class="btn btn-bug js-report-bug">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2c0 4-4 8-4 8s-4-4-4-8 4-8 4-8z"></path><path d="M8 14c0 4 4 8 4 8s4-4 4-8-4-8-4-8z"></path><circle cx="9" cy="9" r="2"></circle><circle cx="15" cy="9" r="2"></circle></svg>
                                Bug
                            </button>
                        </div>

                        <div class="meta-group">
                            <div class="meta-row"><span>Requirement</span> <span>${item.requirement_id ? '#' + item.requirement_id : '-'}</span></div>
                            <div class="meta-row"><span>Pre-cond</span> <span>${(item.pre_conditions || []).length} items</span></div>
                            <div class="meta-row"><span>Linked Bugs</span> <span>${(item.linked_bugs || []).length}</span></div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.setupEvents();
    }

    setupEvents() {
        this.shadowRoot.querySelector('.js-toggle').addEventListener('click', () => this.toggle());

        this.shadowRoot.querySelectorAll('.js-exec').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.dispatchEvent(new CustomEvent('execute', {
                    detail: { iid: this.item.iid, result: btn.dataset.result },
                    bubbles: true,
                    composed: true
                }));
            });
        });

        this.shadowRoot.querySelector('.js-report-bug').addEventListener('click', (e) => {
            e.stopPropagation();
            this.dispatchEvent(new CustomEvent('report-bug', {
                detail: { iid: this.item.iid, title: this.item.title },
                bubbles: true,
                composed: true
            }));
        });
    }
}

customElements.define('qa-test-case-card', QaTestCaseCard);
