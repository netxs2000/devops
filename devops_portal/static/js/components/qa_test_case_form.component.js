/**
 * @file qa_test_case_form.component.js
 * @description 独立测试用例录入表单组件 (QA Domain) - Apple Style Edition
 * @author Antigravity
 */
import { Auth, Api, UI } from '../modules/sys_core.js';
import { QAService } from '../modules/qa_service.js';

class QaTestCaseForm extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.state = {
            products: [],
            organizations: [],
            selectedProductId: null,
            selectedOrgId: null,
            targetProjectId: null, // Resolved from product
            isLoading: false,
            steps: [{ action: '', expected: '' }]
        };
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
            this.state.products = products;
            this.state.organizations = organizations;
        } catch (e) {
            console.error("加载产品/部门列表失败", e);
        }
    }

    async resolveProject(productId) {
        if (!productId) return;
        try {
            // 简单的逻辑：获取该产品关联的项目，取第一个作为默认录入仓库
            // 实际生产中可能需要更复杂的映射逻辑
            const response = await Api.get(`/admin/products/${productId}/projects`);
            if (response && response.length > 0) {
                this.state.targetProjectId = response[0].id;
                console.log(`Resolved target project for product ${productId}: ${this.state.targetProjectId}`);
            } else {
                UI.showToast("该产品未关联任何 GitLab 项目，无法录入用例", "warning");
                this.state.targetProjectId = null;
            }
        } catch (e) {
            console.error("解析关联项目失败", e);
        }
    }

    addStep() {
        this.state.steps.push({ action: '', expected: '' });
        this.render();
    }

    removeStep(index) {
        if (this.state.steps.length > 1) {
            this.state.steps.splice(index, 1);
            this.render();
        }
    }

    async handleAiGenerate() {
        const reqIid = this.shadowRoot.getElementById('req_iid').value;
        const projectId = this.state.targetProjectId;

        if (!reqIid || !projectId) {
            return UI.showToast("请先选择所属产品并输入关联需求 ID", "warning");
        }

        this.state.isLoading = true;
        this.render();

        try {
            const data = await QAService.suggestSteps(projectId, reqIid);
            if (data.steps && data.steps.length > 0) {
                this.state.steps = data.steps.map(s => ({
                    action: s.action,
                    expected: s.expected
                }));
                UI.showToast("✨ AI 已根据需求验收标准为您补全步骤", "success");
            } else {
                UI.showToast("未能从需求中提取到有效步骤", "info");
            }
        } catch (e) {
            UI.showToast("AI 生成失败: " + e.message, "error");
        } finally {
            this.state.isLoading = false;
            this.render();
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        const title = this.shadowRoot.getElementById('title').value;
        const productId = this.shadowRoot.getElementById('product_id').value;
        const productName = this.shadowRoot.getElementById('product_id').options[this.shadowRoot.getElementById('product_id').selectedIndex].text;
        const orgId = this.shadowRoot.getElementById('org_id').value;
        const orgName = this.shadowRoot.getElementById('org_id').options[this.shadowRoot.getElementById('org_id').selectedIndex]?.text || '';

        const projectId = this.state.targetProjectId;

        if (!title || !projectId) {
            return UI.showToast("标题与所属产品为必填项", "warning");
        }

        const stepsData = [];
        this.shadowRoot.querySelectorAll('.step-row').forEach((row, idx) => {
            const action = row.querySelector('.input-action').value;
            const expected = row.querySelector('.input-expected').value;
            if (action) {
                stepsData.push({ step_number: idx + 1, action, expected_result: expected });
            }
        });

        const payload = {
            title,
            requirement_iid: parseInt(this.shadowRoot.getElementById('req_iid').value) || null,
            priority: this.shadowRoot.getElementById('priority').value,
            test_type: this.shadowRoot.getElementById('test_type').value,
            pre_conditions: this.shadowRoot.getElementById('pre_conditions').value,
            product_id: productName, // 传递名称用于 Label
            org_id: orgName,         // 传递名称用于 Label
            steps: stepsData
        };

        this.state.isLoading = true;
        this.render();

        try {
            await QAService.createTestCase(projectId, payload);
            UI.showToast("测试用例已保存并同步至 GitLab", "success");

            // 延迟跳转，让用户看到成功提示
            setTimeout(() => {
                this.dispatchEvent(new CustomEvent('navigate', {
                    detail: { view: 'test-cases' },
                    bubbles: true,
                    composed: true
                }));
            }, 1000);

        } catch (err) {
            UI.showToast("同步失败: " + err.message, "error");
            this.state.isLoading = false;
            this.render();
        }
    }

    render() {
        const themeColor = '#0071e3';
        const { products, selectedProductId, steps, isLoading } = this.state;

        this.shadowRoot.innerHTML = `
            <style>
                :host { display: block; max-width: 900px; margin: 40px auto; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
                
                .form-card { background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(20px) saturate(180%); border-radius: 24px; border: 1px solid rgba(0,0,0,0.1); box-shadow: 0 20px 40px rgba(0,0,0,0.05); overflow: hidden; }
                
                .header { padding: 48px; background: linear-gradient(135deg, #f5f5f7 0%, #fff 100%); border-bottom: 1px solid rgba(0,0,0,0.05); }
                .title { font-size: 36px; font-weight: 700; color: #1d1d1f; margin: 0 0 12px 0; letter-spacing: -0.02em; }
                .subtitle { font-size: 17px; color: #86868b; margin: 0; }
                
                .body { padding: 48px; }
                
                .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; margin-bottom: 32px; }
                .form-group { margin-bottom: 24px; }
                .form-group.full { grid-column: span 2; }
                
                .label { display: block; font-size: 13px; font-weight: 600; color: #86868b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px; }
                
                .input, .textarea, .select { 
                    width: 100%; box-sizing: border-box; padding: 16px; font-size: 16px; 
                    border: 1px solid #d2d2d7; border-radius: 12px; background: rgba(255,255,255,0.8); 
                    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); 
                }
                .input:focus, .textarea:focus, .select:focus { outline: none; border-color: ${themeColor}; box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.1); }
                
                .textarea { min-height: 100px; resize: vertical; }

                /* Steps Design */
                .steps-section { margin-top: 40px; border-top: 1px solid #f5f5f7; padding-top: 40px; }
                .step-row { display: grid; grid-template-columns: 2fr 1.5fr 44px; gap: 12px; margin-bottom: 12px; align-items: center; }
                .btn-remove { width: 44px; height: 44px; border-radius: 50%; border: none; background: #fff1f0; color: #ff4d4f; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 18px; transition: all 0.2s; }
                .btn-remove:hover { background: #ffccc7; transform: scale(1.05); }

                .btn-add { width: 100%; padding: 14px; border-radius: 12px; border: 1px dashed #d2d2d7; background: transparent; color: #86868b; cursor: pointer; font-size: 15px; font-weight: 500; margin-top: 8px; transition: all 0.2s; }
                .btn-add:hover { border-color: ${themeColor}; color: ${themeColor}; background: rgba(0,113,227,0.02); }

                .actions { display: flex; justify-content: flex-end; gap: 16px; margin-top: 56px; padding-top: 32px; border-top: 1px solid #f5f5f7; }
                .btn { padding: 14px 32px; border-radius: 22px; font-size: 17px; font-weight: 600; cursor: pointer; border: none; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); }
                .btn-ghost { background: #f5f5f7; color: #1d1d1f; }
                .btn-ghost:hover { background: #e8e8ed; }
                .btn-primary { background: ${themeColor}; color: white; box-shadow: 0 8px 20px rgba(0,113,227,0.2); }
                .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 12px 28px rgba(0,113,227,0.3); }
                .btn-primary:active { transform: translateY(0); }
                .btn:disabled { opacity: 0.5; cursor: not-allowed; }

                .ai-badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 20px; background: #f2f7ff; color: #0062ff; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.2s; margin-left: auto; }
                .ai-badge:hover { background: #e5f0ff; }

                .required::after { content: '*'; color: #ff3b30; margin-left: 4px; }
                
                .loading-overlay { position: fixed; inset: 0; background: rgba(255,255,255,0.6); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 100; font-weight: 600; color: #1d1d1f; }
            </style>

            <div class="form-card">
                ${isLoading ? '<div class="loading-overlay">⏳ 正在同步至云端...</div>' : ''}
                <div class="header">
                    <h1 class="title">建立测试用例</h1>
                    <p class="subtitle">录入结构化的测试场景，支持 AI 自动化补全执行步骤。</p>
                </div>
                
                <form class="body" id="tc-form">
                    <div class="grid">
                        <div class="form-group">
                            <label class="label required">所属部门</label>
                            <select class="select" id="org_id" required>
                                <option value="" disabled selected>🔍 请选择归属部门...</option>
                                ${this.state.organizations.map(o => {
            const indent = o.org_level > 1 ? '&nbsp;&nbsp;'.repeat(o.org_level - 1) + '├─ ' : '';
            return `<option value="${o.org_id}" ${this.state.selectedOrgId == o.org_id ? 'selected' : ''}>${indent}${o.org_name}</option>`;
        }).join('')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="label required">所属产品</label>
                            <select class="select" id="product_id" required>
                                <option value="" disabled selected>🔍 请选择归属业务产品...</option>
                                ${products.map(p => `<option value="${p.product_id}" ${selectedProductId == p.product_id ? 'selected' : ''}>${p.product_name}</option>`).join('')}
                            </select>
                        </div>

                        <div class="form-group">
                            <label class="label required">用例标题</label>
                            <input type="text" class="input" id="title" placeholder="例如：验证多因素认证登录流程" required>
                        </div>
                        <div class="form-group">
                            <label class="label">关联需求 ID (Issue IID)</label>
                            <div style="display: flex; gap: 8px;">
                                <input type="number" class="input" id="req_iid" placeholder="可选项">
                                <div class="ai-badge js-ai-generate">✨ AI 生成步骤</div>
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="label">优先级</label>
                            <select class="select" id="priority">
                                <option value="P0">P0 - 紧急 (Blocker)</option>
                                <option value="P1">P1 - 高 (Critical)</option>
                                <option value="P2" selected>P2 - 中 (Normal)</option>
                                <option value="P3">P3 - 低 (Minor)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="label">测试类型</label>
                            <select class="select" id="test_type">
                                <option value="功能测试" selected>功能测试</option>
                                <option value="兼容性测试">兼容性测试</option>
                                <option value="性能测试">性能测试</option>
                                <option value="安全测试">安全测试</option>
                                <option value="UI/体验测试">UI/体验测试</option>
                            </select>
                        </div>

                        <div class="form-group full">
                            <label class="label">前置条件</label>
                            <textarea class="textarea" id="pre_conditions" placeholder="描述执行该用例前系统需达到的状态..."></textarea>
                        </div>
                    </div>

                    <div class="steps-section">
                        <label class="label">执行步骤与预期反馈 (Steps)</label>
                        <div id="steps-container">
                            ${steps.map((s, i) => `
                                <div class="step-row" data-index="${i}">
                                    <input type="text" class="input input-action" placeholder="操作步骤 ${i + 1}" value="${s.action}">
                                    <input type="text" class="input input-expected" placeholder="预期反馈 ${i + 1}" value="${s.expected}">
                                    <button type="button" class="btn-remove" data-index="${i}">×</button>
                                </div>
                            `).join('')}
                        </div>
                        <button type="button" class="btn-add js-btn-add">+ 添加新步骤</button>
                    </div>

                    <div class="actions">
                        <button type="button" class="btn btn-ghost js-btn-cancel">取消并返回</button>
                        <button type="submit" class="btn btn-primary" ${!this.state.targetProjectId ? 'disabled' : ''}>
                            ${this.state.targetProjectId ? '保存并同步至 GitLab' : '请先选择有效产品'}
                        </button>
                    </div>
                </form>
            </div>
        `;

        this.setupEvents();
    }

    setupEvents() {
        const form = this.shadowRoot.getElementById('tc-form');
        form.onsubmit = (e) => this.handleSubmit(e);

        this.shadowRoot.getElementById('product_id').onchange = (e) => {
            this.state.selectedProductId = e.target.value;
            this.resolveProject(e.target.value).then(() => this.render());
        };

        const orgSelect = this.shadowRoot.getElementById('org_id');
        if (orgSelect) {
            orgSelect.onchange = (e) => {
                this.state.selectedOrgId = e.target.value;
            };
        }

        this.shadowRoot.querySelector('.js-btn-add').onclick = () => this.addStep();

        this.shadowRoot.querySelectorAll('.btn-remove').forEach(btn => {
            btn.onclick = () => this.removeStep(parseInt(btn.dataset.index));
        });

        this.shadowRoot.querySelector('.js-btn-cancel').onclick = () => {
            this.dispatchEvent(new CustomEvent('navigate', {
                detail: { view: 'test-cases' },
                bubbles: true,
                composed: true
            }));
        };

        const aiBtn = this.shadowRoot.querySelector('.js-ai-generate');
        if (aiBtn) aiBtn.onclick = () => this.handleAiGenerate();
    }
}

customElements.define('qa-test-case-form', QaTestCaseForm);
