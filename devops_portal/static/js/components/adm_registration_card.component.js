/**
 * @file adm_registration_card.component.js
 * @description Apple Style Registration Approval Card
 */

class AdmRegistrationCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    static get observedAttributes() {
        return ['name', 'email', 'company', 'date', 'status', 'gitlab-id'];
    }

    attributeChangedCallback() { this.render(); }
    connectedCallback() { this.render(); }

    render() {
        const name = this.getAttribute('name') || '-';
        const email = this.getAttribute('email') || '-';
        const company = this.getAttribute('company') || '-';
        const date = this.getAttribute('date') || '-';
        const status = this.getAttribute('status') || 'pending';
        const gitlabId = this.getAttribute('gitlab-id');

        this.shadowRoot.innerHTML = `
            <style>
                :host { display: block; }
                .card {
                    background: rgba(255, 255, 255, 0.72);
                    backdrop-filter: blur(20px) saturate(180%);
                    -webkit-backdrop-filter: blur(20px) saturate(180%);
                    border-radius: 16px;
                    padding: 16px;
                    border: 1px solid rgba(0, 0, 0, 0.05);
                    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.01);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    transition: all 0.2s ease;
                }
                .card:hover {
                    box-shadow: 0 12px 24px rgba(0,0,0,0.04);
                }
                .info-main { display: flex; flex-direction: column; gap: 4px; }
                .name { font-size: 15px; font-weight: 600; color: #1D1D1F; }
                .meta { font-size: 12px; color: #86868B; display: flex; gap: 8px; align-items: center; }
                .company { color: var(--primary, #0071E3); font-weight: 500; }
                .actions { display: flex; gap: 8px; }
                .btn {
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 600;
                    border: none;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .btn--approve { background: #0071E3; color: white; }
                .btn--approve:hover { background: #0077ED; transform: scale(1.05); }
                .btn--reject { background: rgba(255, 59, 48, 0.1); color: #FF3B30; }
                .btn--reject:hover { background: rgba(255, 59, 48, 0.2); }
                .badge { font-size: 11px; font-weight: 700; color: #86868B; background: rgba(0,0,0,0.05); padding: 2px 8px; border-radius: 4px; }
                .status--pending { color: #FF9F0A; background: rgba(255, 159, 10, 0.1); }
            </style>
            <div class="card">
                <div class="info-main">
                    <div class="name">${name} <span class="badge status--${status}">${status}</span></div>
                    <div class="meta">
                        <span>${email}</span>
                        <span>•</span>
                        <span class="company">${company}</span>
                    </div>
                    <div class="meta" style="margin-top: 4px; font-size: 11px;">
                        Requested at: ${date}
                        ${gitlabId ? `<span style="color: #34C759;">(Bound to GitLab: ${gitlabId})</span>` : ''}
                    </div>
                </div>
                <div class="actions">
                    ${status === 'pending' ? `
                        <button class="btn btn--reject js-btn-reject" data-email="${email}">拒绝驳回</button>
                        <button class="btn btn--approve js-btn-approve" data-email="${email}">通过授权</button>
                    ` : `
                        <span class="u-text-dim">已处理</span>
                    `}
                </div>
            </div>
        `;

        this.shadowRoot.querySelectorAll('.btn').forEach(btn => {
            btn.onclick = (e) => {
                const action = btn.classList.contains('js-btn-approve') ? 'approve' : 'reject';
                this.dispatchEvent(new CustomEvent('action', {
                    detail: { action, email: btn.dataset.email },
                    bubbles: true,
                    composed: true
                }));
            };
        });
    }
}
customElements.define('adm-registration-card', AdmRegistrationCard);
