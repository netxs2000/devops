/**
 * @file adm_product_card.component.js
 * @description Administration Product Information Card (Apple Style)
 */

class AdmProductCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    static get observedAttributes() {
        return ['name', 'category', 'status', 'owner', 'id'];
    }

    attributeChangedCallback() {
        this.render();
    }

    connectedCallback() {
        this.render();
    }

    render() {
        const name = this.getAttribute('name') || 'Unknown Product';
        const category = this.getAttribute('category') || 'General';
        const status = this.getAttribute('status') || 'INACTIVE';
        const owner = this.getAttribute('owner') || 'Platform';
        const prodId = this.getAttribute('id') || '-';

        const statusClass = status === 'ACTIVE' ? 'status--active' : 'status--pending';

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                }
                .card {
                    background: rgba(255, 255, 255, 0.72);
                    backdrop-filter: blur(20px) saturate(180%);
                    -webkit-backdrop-filter: blur(20px) saturate(180%);
                    border-radius: 16px;
                    padding: 20px;
                    border: 1px solid rgba(0, 0, 0, 0.05);
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.01);
                }
                .card:hover {
                    transform: translateY(-4px);
                    box-shadow: 0 20px 40px rgba(0,0,0,0.04);
                    border-color: var(--primary, #0071E3);
                }
                .header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                }
                .name {
                    font-size: 16px;
                    font-weight: 600;
                    color: #1D1D1F;
                    margin: 0;
                }
                .category {
                    font-size: 12px;
                    color: #86868B;
                    font-weight: 500;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                .meta {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }
                .meta-item {
                    font-size: 13px;
                    color: #424245;
                    display: flex;
                    justify-content: space-between;
                }
                .label {
                    color: #86868B;
                }
                .status {
                    display: inline-flex;
                    align-items: center;
                    padding: 4px 10px;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
                .status--active {
                    background: rgba(52, 199, 89, 0.1);
                    color: #34C759;
                }
                .status--pending {
                    background: rgba(255, 159, 10, 0.1);
                    color: #FF9F0A;
                }
                .footer {
                    margin-top: 8px;
                    padding-top: 12px;
                    border-top: 1px solid rgba(0, 0, 0, 0.05);
                    display: flex;
                    justify-content: flex-end;
                }
            </style>
            <div class="card">
                <div class="header">
                    <div class="meta">
                        <span class="category">${category}</span>
                        <h3 class="name">${name}</h3>
                    </div>
                    <span class="status ${statusClass}">${status}</span>
                </div>
                <div class="meta-item">
                    <span class="label">ID</span>
                    <span>${prodId}</span>
                </div>
                <div class="meta-item">
                    <span class="label">Owner</span>
                    <span>${owner}</span>
                </div>
            </div>
        `;
    }
}

customElements.define('adm-product-card', AdmProductCard);
