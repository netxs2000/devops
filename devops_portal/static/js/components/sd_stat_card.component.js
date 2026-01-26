/**
 * @file sd_stat_card.component.js
 * @description Service Desk Statistics Card Web Component (Apple Style)
 */

class SDStatCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    static get observedAttributes() {
        return ['label', 'value', 'type'];
    }

    attributeChangedCallback() {
        this.render();
    }

    connectedCallback() {
        this.render();
    }

    render() {
        const label = this.getAttribute('label') || '-';
        const value = this.getAttribute('value') || '-';
        const type = this.getAttribute('type') || 'default';

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    flex: 1;
                    min-width: 150px;
                }
                .card {
                    background: rgba(255, 255, 255, 0.72);
                    backdrop-filter: blur(20px) saturate(180%);
                    -webkit-backdrop-filter: blur(20px) saturate(180%);
                    border-radius: 20px;
                    padding: 24px;
                    text-align: center;
                    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                }
                :host(:hover) .card {
                    transform: translateY(-4px);
                    background: rgba(255, 255, 255, 0.85);
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.04);
                }
                .value {
                    font-size: 32px;
                    font-weight: 700;
                    color: var(--primary, #1D1D1F);
                    margin-bottom: 8px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                }
                .label {
                    font-size: 13px;
                    font-weight: 500;
                    color: var(--secondary, #86868B);
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                /* Specialized types */
                .type-time .value {
                    color: #0071E3; /* Apple Blue */
                }
            </style>
            <div class="card type-${type}">
                <div class="value">${value}</div>
                <div class="label">${label}</div>
            </div>
        `;
    }
}

customElements.define('sd-stat-card', SDStatCard);
