/**
 * @file sd_ticket_list.component.js
 * @description Service Desk "My Tickets" List Component
 */
import { SDService } from '../modules/sd_service.js';

class SdTicketList extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.state = {
            tickets: [],
            loading: true
        };
    }

    async connectedCallback() {
        this.render();
        try {
            this.state.tickets = await SDService.getMyTickets();
            this.state.loading = false;
            this.render();
        } catch (e) {
            console.error("Failed to load tickets", e);
            this.state.loading = false;
            this.render();
        }
    }

    render() {
        const { tickets, loading } = this.state;

        this.shadowRoot.innerHTML = `
            <style>
                :host { display: block; max-width: 1000px; margin: 0 auto; animation: fadeIn 0.3s ease; }
                @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
                .title { font-size: 24px; font-weight: 700; color: #1d1d1f; margin: 0; }
                .btn-back { background: #f5f5f7; border: none; padding: 8px 16px; border-radius: 16px; cursor: pointer; color: #1d1d1f; font-weight: 500; font-size: 14px; }
                .btn-back:hover { background: #e8e8ed; }

                .ticket-list { background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(20px); border-radius: 20px; border: 1px solid rgba(0,0,0,0.05); overflow: hidden; }
                
                .ticket-item { padding: 20px 24px; border-bottom: 1px solid rgba(0,0,0,0.05); display: flex; align-items: center; justify-content: space-between; transition: 0.2s; }
                .ticket-item:last-child { border-bottom: none; }
                .ticket-item:hover { background: #fff; }

                .ticket-left { display: flex; align-items: center; gap: 16px; }
                .status-dot { width: 10px; height: 10px; border-radius: 50%; }
                .status-opened { background: #FF9500; box-shadow: 0 0 8px rgba(255, 149, 0, 0.4); }
                .status-closed { background: #34C759; box-shadow: 0 0 8px rgba(52, 199, 89, 0.4); }
                
                .ticket-main { display: flex; flex-direction: column; gap: 4px; }
                .ticket-title { font-size: 16px; font-weight: 600; color: #1d1d1f; }
                .ticket-meta { font-size: 12px; color: #86868b; }
                
                .ticket-right { display: flex; align-items: center; gap: 12px; }
                .badge { padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; text-transform: uppercase; background: #f5f5f7; color: #86868b; }
                .badge-bug { background: #FFF0F0; color: #FF3B30; }
                .badge-req { background: #F0F8FF; color: #0071E3; }

                .empty-state { padding: 60px; text-align: center; color: #86868b; }
            </style>

            <div class="header">
                <h2 class="title">我的提交记录</h2>
                <button class="btn-back js-back">← 返回</button>
            </div>

            <div class="ticket-list">
                ${loading ? '<div class="empty-state">加载中...</div>' : ''}
                
                ${!loading && tickets.length === 0 ? '<div class="empty-state">暂无提交记录</div>' : ''}

                ${tickets.map(t => `
                    <div class="ticket-item">
                        <div class="ticket-left">
                            <div class="status-dot ${t.status === 'opened' ? 'status-opened' : 'status-closed'}"></div>
                            <div class="ticket-main">
                                <div class="ticket-title">${t.title}</div>
                                <div class="ticket-meta">#${t.id} · ${new Date(t.created_at).toLocaleDateString()}</div>
                            </div>
                        </div>
                        <div class="ticket-right">
                            <span class="badge ${t.issue_type === 'bug' ? 'badge-bug' : 'badge-req'}">${t.issue_type}</span>
                            <span class="badge">${t.status}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        this.shadowRoot.querySelector('.js-back').addEventListener('click', () => {
            this.dispatchEvent(new CustomEvent('navigate', {
                detail: { view: 'landing' },
                bubbles: true,
                composed: true
            }));
        });
    }
}

customElements.define('sd-ticket-list', SdTicketList);
