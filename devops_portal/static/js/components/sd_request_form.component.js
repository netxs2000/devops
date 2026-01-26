/**
 * @file sd_request_form.component.js
 * @description Service Desk Unified Request Form (Bug & Requirement)
 */
import { SDService } from '../modules/sd_service.js';
import { UI } from '../modules/sys_core.js';

class SdRequestForm extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.state = {
            type: 'bug', // 'bug' | 'requirement'
            products: [],
            isSubmitting: false
        };
    }

    static get observedAttributes() { return ['type']; }

    attributeChangedCallback(name, oldValue, newValue) {
        if (name === 'type' && oldValue !== newValue) {
            this.state.type = newValue;
            this.render();
        }
    }

    async connectedCallback() {
        if (!this.hasAttribute('type')) this.setAttribute('type', 'bug');
        await this.loadProducts();
    }

    async loadProducts() {
        try {
            this.state.products = await SDService.getBusinessProjects();
            this.render(); // Re-render with products
        } catch (e) {
            console.error("Failed to load products", e);
        }
    }

    render() {
        const isBug = this.state.type === 'bug';
        const title = isBug ? "提交缺陷报告" : "提报产品需求";
        const desc = isBug ? "请详细描述遇到的问题，我们将尽快修复。" : "请描述您的业务场景与期望价值。";
        const themeColor = isBug ? "#FF3B30" : "#0071E3"; // Red vs Blue

        this.shadowRoot.innerHTML = `
            <style>
                :host { display: block; max-width: 800px; margin: 0 auto; animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
                @keyframes slideUp { from { transform: translateY(40px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

                .form-container { background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(20px); border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.05); overflow: hidden; }
                
                .header { padding: 40px; background: ${isBug ? 'linear-gradient(135deg, #FFF0F0 0%, #FFF 100%)' : 'linear-gradient(135deg, #F0F8FF 0%, #FFF 100%)'}; border-bottom: 1px solid rgba(0,0,0,0.05); }
                .title { font-size: 32px; font-weight: 700; margin: 0 0 8px 0; color: #1d1d1f; }
                .subtitle { font-size: 16px; color: #86868b; margin: 0; }
                
                .body { padding: 40px; }
                
                .form-group { margin-bottom: 24px; }
                .label { display: block; font-size: 13px; font-weight: 600; color: #86868b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
                .input, .textarea, .select { width: 100%; box-sizing: border-box; padding: 14px; font-size: 16px; border: 1px solid #d2d2d7; border-radius: 12px; background: #fff; transition: border-color 0.2s; font-family: inherit; }
                .input:focus, .textarea:focus, .select:focus { outline: none; border-color: ${themeColor}; box-shadow: 0 0 0 3px ${isBug ? 'rgba(255, 59, 48, 0.1)' : 'rgba(0, 113, 227, 0.1)'}; }
                .textarea { min-height: 120px; resize: vertical; }
                
                .actions { display: flex; justify-content: flex-end; gap: 16px; margin-top: 40px; }
                .btn { padding: 12px 28px; border-radius: 20px; font-size: 16px; font-weight: 500; cursor: pointer; border: none; transition: all 0.2s; }
                .btn-cancel { background: #f5f5f7; color: #1d1d1f; }
                .btn-submit { background: ${themeColor}; color: white; box-shadow: 0 4px 12px ${isBug ? 'rgba(255, 59, 48, 0.3)' : 'rgba(0, 113, 227, 0.3)'}; }
                .btn-submit:hover { transform: translateY(-1px); box-shadow: 0 6px 16px ${isBug ? 'rgba(255, 59, 48, 0.4)' : 'rgba(0, 113, 227, 0.4)'}; }
                .btn-submit:disabled { opacity: 0.7; cursor: wait; }

                .required::after { content: '*'; color: #FF3B30; margin-left: 4px; }
            </style>

            <div class="form-container">
                <div class="header">
                    <h1 class="title">${title}</h1>
                    <p class="subtitle">${desc}</p>
                </div>
                <div class="body">
                    <div class="form-group">
                        <label class="label required">涉及业务系统</label>
                        <select class="select" id="product_id" required>
                            <option value="" disabled selected>请选择系统...</option>
                            ${this.state.products.map(p =>
            `<option value="${p.id}">${p.name}</option>`
        ).join('')}
                        </select>
                    </div>

                    <div class="form-group">
                        <label class="label required">标题摘要</label>
                        <input type="text" class="input" id="title" placeholder="简要描述问题或需求" required>
                    </div>

                    ${isBug ? `
                        <div class="form-group">
                            <label class="label required">严重程度</label>
                            <select class="select" id="severity">
                                <option value="S2">S2 - 一般功能故障 (Major)</option>
                                <option value="S1">S1 - 核心业务阻断 (Critical)</option>
                                <option value="S3">S3 - 界面或体验问题 (Minor)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="label">复现步骤</label>
                            <textarea class="textarea" id="steps" placeholder="1. 打开页面...\n2. 点击按钮...\n3. 报错信息..."></textarea>
                        </div>
                        <div class="form-group">
                            <label class="label required">实际表现 vs 期望表现</label>
                            <textarea class="textarea" id="actual" placeholder="实际看到了什么错误，期望应该是什么结果..." required></textarea>
                        </div>
                    ` : `
                        <div class="form-group">
                            <label class="label required">需求描述</label>
                            <textarea class="textarea" id="description" placeholder="请详细描述业务场景、目标用户及期望的功能行为..." required style="min-height: 200px;"></textarea>
                        </div>
                        <div class="form-group">
                            <label class="label">期望上线时间</label>
                            <input type="date" class="input" id="expected_date">
                        </div>
                    `}

                    <div class="actions">
                        <button class="btn btn-cancel js-cancel">取消</button>
                        <button class="btn btn-submit js-submit">提交反馈</button>
                    </div>
                </div>
            </div>
        `;

        this.setupEvents();
    }

    setupEvents() {
        this.shadowRoot.querySelector('.js-cancel').addEventListener('click', () => {
            this.dispatchBack();
        });

        this.shadowRoot.querySelector('.js-submit').addEventListener('click', async () => {
            const btn = this.shadowRoot.querySelector('.js-submit');

            // Basic Validation
            const productId = this.shadowRoot.getElementById('product_id').value;
            const title = this.shadowRoot.getElementById('title').value;
            if (!productId || !title) {
                alert('请填写必要信息');
                return;
            }

            btn.disabled = true;
            btn.textContent = '提交中...';

            const data = this.state.type === 'bug' ? {
                title: title,
                severity: this.shadowRoot.getElementById('severity').value,
                environment: 'Production',
                province: 'nationwide',
                steps_to_repro: this.shadowRoot.getElementById('steps').value || '-',
                actual_result: this.shadowRoot.getElementById('actual').value,
                expected_result: this.shadowRoot.getElementById('actual').value,
                priority: 'P2'
            } : {
                title: title,
                description: this.shadowRoot.getElementById('description').value,
                priority: 'P2',
                req_type: 'feature',
                province: 'nationwide',
                expected_delivery: this.shadowRoot.getElementById('expected_date').value
            };

            try {
                await SDService.submitTicket(this.state.type, productId, data);
                UI.showToast("工单提交成功", "success");
                this.dispatchBack();
            } catch (e) {
                console.error(e);
                UI.showToast(e.detail || "提交失败", "error");
                btn.disabled = false;
                btn.textContent = '提交反馈';
            }
        });
    }

    dispatchBack() {
        this.dispatchEvent(new CustomEvent('navigate', {
            detail: { view: 'landing' },
            bubbles: true,
            composed: true
        }));
    }
}

customElements.define('sd-request-form', SdRequestForm);
