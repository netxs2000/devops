/**
 * @file pm_issue_card.component.js
 * @description ITeration Plan Issue Card Web Component (Apple Style)
 */

class PMIssueCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    static get observedAttributes() {
        return ['title', 'iid', 'status', 'author', 'weight', 'type'];
    }

    attributeChangedCallback() {
        this.render();
    }

    connectedCallback() {
        this.render();
    }

    render() {
        const title = this.getAttribute('title') || '-';
        const iid = this.getAttribute('iid') || '0';
        const status = this.getAttribute('status') || 'opened';
        const author = this.getAttribute('author') || 'Unknown';
        const weight = this.getAttribute('weight');
        const type = this.getAttribute('type') || 'feature';

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    user-select: none;
                }
                .card {
                    background-color: var(--sys-bg-sidebar, #ffffff);
                    padding: 16px;
                    border-radius: 14px;
                    border: 1px solid rgba(0, 0, 0, 0.05);
                    cursor: grab;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    position: relative;
                    overflow: hidden;
                }
                .card:hover {
                    transform: translateY(-2px) scale(1.01);
                    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.04);
                    border-color: var(--primary, #0071E3);
                }
                .card:active {
                    cursor: grabbing;
                    transform: scale(0.98);
                }
                .card.is-closed {
                    opacity: 0.6;
                }
                .card.is-closed::before {
                    content: '';
                    position: absolute;
                    left: 0;
                    top: 0;
                    bottom: 0;
                    width: 4px;
                    background-color: #34C759; /* Apple Success Green */
                }
                .header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 8px;
                }
                .iid {
                    font-size: 11px;
                    color: #86868B;
                    font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, monospace;
                    font-weight: 500;
                }
                .title {
                    font-size: 14px;
                    font-weight: 500;
                    color: #1D1D1F;
                    line-height: 1.4;
                    margin-bottom: 12px;
                    display: -webkit-box;
                    -webkit-line-clamp: 2;
                    -webkit-box-orient: vertical;
                    overflow: hidden;
                }
                .footer {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    font-size: 11px;
                    color: #86868B;
                }
                .label {
                    padding: 2px 6px;
                    border-radius: 6px;
                    font-size: 10px;
                    font-weight: 600;
                    text-transform: uppercase;
                }
                .label.bug {
                    color: #FF3B30;
                    background: rgba(255, 59, 48, 0.1);
                }
                .label.feature {
                    color: #0071E3;
                    background: rgba(0, 113, 227, 0.1);
                }
                .weight-badge {
                    background-color: rgba(0, 0, 0, 0.03);
                    padding: 2px 6px;
                    border-radius: 4px;
                    color: #1D1D1F;
                    font-weight: 600;
                }
            </style>
            <div class="card ${status === 'closed' ? 'is-closed' : ''}">
                <div class="header">
                    <span class="iid">#${iid}</span>
                    <span class="label ${type}">${type}</span>
                </div>
                <div class="title">${title}</div>
                <div class="footer">
                    <span class="author">${author}</span>
                    ${weight ? `<span class="weight-badge">${weight} pts</span>` : ''}
                </div>
            </div>
        `;
    }
}

customElements.define('pm-issue-card', PMIssueCard);
