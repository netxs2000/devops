/**
 * @file adm_product_selector.component.js
 * @description 产品/部门聚合切换器组件 (Administration Domain) - Apple Style Edition
 * @author Antigravity
 */
import { Api } from '../modules/sys_core.js';

class AdmProductSelector extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this._state = {
            products: [],
            organizations: [],
            selectedType: 'product', // 'product' | 'org'
            selectedId: null
        };
    }

    static get observedAttributes() {
        return ['selected-type', 'selected-id'];
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (oldValue !== newValue) {
            if (name === 'selected-type') this._state.selectedType = newValue;
            if (name === 'selected-id') this._state.selectedId = newValue;
            this.render();
        }
    }

    async connectedCallback() {
        await this.fetchData();
        this.render();
    }

    async fetchData() {
        try {
            const [products, organizations] = await Promise.all([
                Api.get('/admin/products'),
                Api.get('/admin/organizations')
            ]);
            this._state.products = products;
            this._state.organizations = organizations;
        } catch (error) {
            console.error('Failed to fetch selector data:', error);
        }
    }

    handleSwitch(type) {
        this._state.selectedType = type;
        this._state.selectedId = null; // 重置选中项
        this.render();
        this.emitChange();
    }

    handleSelect(e) {
        this._state.selectedId = e.target.value;
        this.emitChange();
    }

    emitChange() {
        this.dispatchEvent(new CustomEvent('change', {
            detail: {
                type: this._state.selectedType,
                id: this._state.selectedId
            },
            bubbles: true,
            composed: true
        }));
    }

    render() {
        const { products, organizations, selectedType, selectedId } = this._state;
        const options = selectedType === 'product' ? products : organizations;
        const idKey = selectedType === 'product' ? 'product_id' : 'org_id';
        const nameKey = selectedType === 'product' ? 'product_name' : 'org_name';

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                }
                .container {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 8px 16px;
                    background: rgba(255, 255, 255, 0.72);
                    backdrop-filter: blur(20px) saturate(180%);
                    -webkit-backdrop-filter: blur(20px) saturate(180%);
                    border-radius: 12px;
                    border: 1px solid rgba(0, 0, 0, 0.08);
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.01);
                }
                .segmented-control {
                    display: flex;
                    background: rgba(0, 0, 0, 0.05);
                    padding: 2px;
                    border-radius: 8px;
                    position: relative;
                }
                .segment {
                    padding: 6px 12px;
                    font-size: 13px;
                    font-weight: 500;
                    color: #86868B;
                    cursor: pointer;
                    border-radius: 6px;
                    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                    user-select: none;
                }
                .segment.active {
                    background: #FFFFFF;
                    color: #1D1D1F;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
                }
                .select-wrapper {
                    position: relative;
                    flex: 1;
                }
                select {
                    width: 100%;
                    appearance: none;
                    background: transparent;
                    border: none;
                    padding: 8px 32px 8px 12px;
                    font-size: 14px;
                    font-weight: 500;
                    color: #1D1D1F;
                    cursor: pointer;
                    outline: none;
                }
                .select-wrapper::after {
                    content: "↓";
                    position: absolute;
                    right: 12px;
                    top: 50%;
                    transform: translateY(-50%);
                    font-size: 12px;
                    color: #86868B;
                    pointer-events: none;
                }
                .divider {
                    width: 1px;
                    height: 20px;
                    background: rgba(0, 0, 0, 0.08);
                }
            </style>
            <div class="container">
                <div class="segmented-control">
                    <div class="segment ${selectedType === 'product' ? 'active' : ''}" 
                         data-type="product">产品</div>
                    <div class="segment ${selectedType === 'org' ? 'active' : ''}" 
                         data-type="org">部门</div>
                </div>
                <div class="divider"></div>
                <div class="select-wrapper">
                    <select id="main-select">
                        <option value="">请选择${selectedType === 'product' ? '产品' : '部门'}...</option>
                        ${options.map(opt => `
                            <option value="${opt[idKey]}" ${selectedId === opt[idKey] ? 'selected' : ''}>
                                ${opt[nameKey]}
                            </option>
                        `).join('')}
                    </select>
                </div>
            </div>
        `;

        this.shadowRoot.querySelectorAll('.segment').forEach(seg => {
            seg.onclick = () => this.handleSwitch(seg.dataset.type);
        });

        this.shadowRoot.getElementById('main-select').onchange = (e) => this.handleSelect(e);
    }
}

customElements.define('adm-product-selector', AdmProductSelector);
