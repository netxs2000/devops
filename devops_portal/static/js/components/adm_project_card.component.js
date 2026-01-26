/**
 * @file adm_project_card.component.js
 * @description MDM Project Card for Mapping View (Apple Style)
 */

class AdmProjectCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    static get observedAttributes() {
        return ['name', 'id', 'type', 'status', 'binding', 'repos'];
    }

    attributeChangedCallback() { this.render(); }
    connectedCallback() { this.render(); }

    render() {
        const name = this.getAttribute('name') || 'Untitled Project';
        const projId = this.getAttribute('id') || '-';
        const type = this.getAttribute('type') || 'SPRINT';
        const status = this.getAttribute('status') || 'PENDING';
        const binding = this.getAttribute('binding') === 'true';
        const repos = this.getAttribute('repos') || '0';

        const statusClass = status === 'RELEASED' ? 'status--active' : 'status--pending';

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
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                }
                .card:hover {
                    box-shadow: 0 12px 24px rgba(0,0,0,0.04);
                    border-color: var(--primary, #0071E3);
                }
                .header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
                .title-group { display: flex; flex-direction: column; }
                .name { font-size: 15px; font-weight: 600; color: #1D1D1F; margin: 0; }
                .pid { font-size: 11px; color: #86868B; font-family: var(--g-font-mono); }
                .badge { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 6px; text-transform: uppercase; }
                .status--active { background: rgba(52, 199, 89, 0.1); color: #34C759; }
                .status--pending { background: rgba(142, 142, 147, 0.1); color: #8E8E93; }
                .meta { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 12px; font-size: 12px; }
                .label { color: #86868B; margin-bottom: 2px; display: block; font-size: 10px; text-transform: uppercase; }
                .val { color: #1D1D1F; font-weight: 500; }
                .binding { display: flex; align-items: center; gap: 4px; }
                .binding--yes { color: #34C759; }
                .binding--no { color: #FF9F0A; }
            </style>
            <div class="card">
                <div class="header">
                    <div class="title-group">
                        <span class="pid">${projId}</span>
                        <h4 class="name">${name}</h4>
                    </div>
                    <span class="badge ${statusClass}">${status}</span>
                </div>
                <div class="meta">
                    <div>
                        <span class="label">Type</span>
                        <span class="val">${type}</span>
                    </div>
                    <div>
                        <span class="label">Repos</span>
                        <span class="val">${repos} Connected</span>
                    </div>
                </div>
                <div class="u-mt-12 binding ${binding ? 'binding--yes' : 'binding--no'}" style="font-size: 12px; border-top: 1px solid rgba(0,0,0,0.05); padding-top: 10px;">
                    ${binding ? '● 已关联技术栈 (Syncing)' : '○ 尚未绑定 GitLab 仓库'}
                </div>
            </div>
        `;
    }
}
customElements.define('adm-project-card', AdmProjectCard);
