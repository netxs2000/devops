/**
 * @file sd_landing.component.js
 * @description Service Desk Landing View (User Portal)
 */

class SdLanding extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    connectedCallback() {
        this.render();
        this.setupEvents();
    }

    render() {
        this.shadowRoot.innerHTML = `
            <style>
                :host { display: block; padding: 40px; max-width: 1200px; margin: 0 auto; animtion: fadeIn 0.3s ease; }
                @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
                
                .header { text-align: center; margin-bottom: 60px; }
                .title { font-size: 48px; font-weight: 700; margin-bottom: 16px; background: linear-gradient(135deg, #1d1d1f 0%, #434344 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
                .subtitle { font-size: 24px; color: #86868b; max-width: 600px; margin: 0 auto; }
                
                .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 32px; margin-bottom: 60px; }
                
                .card {
                    background: rgba(255, 255, 255, 0.8);
                    backdrop-filter: blur(20px);
                    border: 1px solid rgba(0,0,0,0.05);
                    border-radius: 24px;
                    padding: 32px;
                    cursor: pointer;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    text-align: center;
                    position: relative;
                    overflow: hidden;
                }
                .card:hover { transform: translateY(-8px); box-shadow: 0 20px 40px rgba(0,0,0,0.08); background: #fff; }
                
                .icon { width: 64px; height: 64px; background: var(--icon-bg, #f5f5f7); border-radius: 16px; display: flex; align-items: center; justify-content: center; margin: 0 auto 24px; transition: transform 0.3s ease; }
                .card:hover .icon { transform: scale(1.1) rotate(5deg); }
                
                .card-title { font-size: 20px; font-weight: 600; margin-bottom: 8px; color: #1d1d1f; }
                .card-desc { font-size: 14px; color: #86868b; line-height: 1.5; margin-bottom: 24px; }
                
                .btn-fake { display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 13px; font-weight: 500; background: #f5f5f7; color: #1d1d1f; transition: all 0.2s; }
                .card:hover .btn-fake { background: #0071e3; color: white; }

                .stats { margin-top: 60px; }
                .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
            </style>

            <div class="header">
                <h1 class="title">Service Desk</h1>
                <p class="subtitle">技术支持与需求提报中心</p>
            </div>

            <div class="card-grid">
                <div class="card js-nav" data-target="bug_form">
                    <div class="icon" style="--icon-bg: #FFE5E5;">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#FF3B30" stroke-width="2"><path d="M12 2c0 4-4 8-4 8s-4-4-4-8 4-8 4-8z"></path><path d="M8 14c0 4 4 8 4 8s4-4 4-8-4-8-4-8z"></path><circle cx="9" cy="9" r="2"></circle><circle cx="15" cy="9" r="2"></circle></svg>
                    </div>
                    <div class="card-title">提交缺陷</div>
                    <div class="card-desc">发现系统问题？立即提交缺陷报告，我们将优先处理。</div>
                    <div class="btn-fake">Report Bug</div>
                </div>

                <div class="card js-nav" data-target="req_form">
                    <div class="icon" style="--icon-bg: #E5F0FF;">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#0071E3" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
                    </div>
                    <div class="card-title">提交需求</div>
                    <div class="card-desc">有新的功能想法？告诉我们，帮助产品持续进化。</div>
                    <div class="btn-fake">New Feature</div>
                </div>

                <div class="card js-nav" data-target="my_tickets">
                    <div class="icon" style="--icon-bg: #E5FFE5;">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#34C759" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>
                    </div>
                    <div class="card-title">我的工单</div>
                    <div class="card-desc">查看您提交的所有工单状态及处理进度。</div>
                    <div class="btn-fake">My Tickets</div>
                </div>
            </div>

            <div class="stats js-stats-container">
                <!-- Stats injected dynamically -->
            </div>
        `;
    }

    setupEvents() {
        this.shadowRoot.querySelectorAll('.js-nav').forEach(el => {
            el.addEventListener('click', () => {
                this.dispatchEvent(new CustomEvent('navigate', {
                    detail: { view: el.dataset.target },
                    bubbles: true,
                    composed: true
                }));
            });
        });
    }
}

customElements.define('sd-landing', SdLanding);
