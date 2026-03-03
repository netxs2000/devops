/**
 * @file qa_test_case_card.component.js
 * @description QA Test Case Row Component (GitLab Style)
 */
import '../components/qa_priority_badge.component.js';

class QaTestCaseCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
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
        if (!this.item) this.render();
    }

    render() {
        if (!this.item) return;
        const item = this.item;

        this.shadowRoot.innerHTML = `
            <style>
                :host { display: block; border-bottom: 1px solid #F0F0F0; }
                :host(:last-child) { border-bottom: none; }
                
                .row {
                    display: grid;
                    grid-template-columns: 32px 60px 1fr auto;
                    align-items: center;
                    padding: 12px 20px;
                    gap: 16px;
                    cursor: pointer;
                    background: white;
                    transition: all 0.1s;
                }
                .row:hover { background: #F9FAFB; }
                :host([active]) .row { background: #F2F7FF; border-left: 3px solid #0071e3; }
                
                .status-icon {
                    width: 10px;
                    height: 10px;
                    border-radius: 50%;
                    flex-shrink: 0;
                }
                .status-passed { background: #34C759; box-shadow: 0 0 0 4px rgba(52, 199, 89, 0.1); }
                .status-failed { background: #FF3B30; box-shadow: 0 0 0 4px rgba(255, 59, 48, 0.1); }
                .status-pending { background: #8E8E93; }
                .status-blocked { background: #FF9500; }
                
                .iid {
                    font-family: var(--g-font-mono);
                    font-size: 12px;
                    color: #86868b;
                }
                
                .title {
                    font-size: 14px;
                    font-weight: 500;
                    color: #1d1d1f;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                
                .meta {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }
                
                .label {
                    font-size: 11px;
                    padding: 2px 8px;
                    border-radius: 4px;
                    background: #F5F5F7;
                    color: #48484a;
                    border: 1px solid #E5E5EA;
                }
            </style>

            <div class="row js-select">
                <div class="status-icon status-${item.result || 'pending'}"></div>
                <div class="iid">#${item.iid}</div>
                <div class="title">${item.title}</div>
                <div class="meta">
                    <span class="label">${item.priority || 'P2'}</span>
                    <qa-priority-badge status="${item.result}"></qa-priority-badge>
                </div>
            </div>
        `;

        this.setupEvents();
    }

    setupEvents() {
        this.shadowRoot.querySelector('.js-select').addEventListener('click', () => {
            this.dispatchEvent(new CustomEvent('select-case', {
                detail: { item: this.item },
                bubbles: true,
                composed: true
            }));
        });
    }
}

customElements.define('qa-test-case-card', QaTestCaseCard);
