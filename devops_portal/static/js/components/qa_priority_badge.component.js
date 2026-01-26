/**
 * @file qa_priority_badge.component.js
 * @description 测试用例优先级/状态标签组件 (Quality Assurance Domain) - Apple Style Edition
 * @author Antigravity
 */
class QaPriorityBadge extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    static get observedAttributes() {
        return ['level', 'status'];
    }

    attributeChangedCallback() {
        this.render();
    }

    connectedCallback() {
        this.render();
    }

    render() {
        const level = this.getAttribute('level') || 'P2';
        const status = this.getAttribute('status') || ''; // 'passed', 'failed', 'blocked', 'pending'

        const config = {
            'P0': { color: '#FF3B30', bg: 'rgba(255, 59, 48, 0.1)', label: 'P0 紧急' },
            'P1': { color: '#FF9500', bg: 'rgba(255, 149, 0, 0.1)', label: 'P1 高' },
            'P2': { color: '#007AFF', bg: 'rgba(0, 122, 255, 0.1)', label: 'P2 中' },
            'P3': { color: '#8E8E93', bg: 'rgba(142, 142, 147, 0.1)', label: 'P3 低' },
            'passed': { color: '#34C759', bg: 'rgba(52, 199, 89, 0.1)', label: '已通过' },
            'failed': { color: '#FF3B30', bg: 'rgba(255, 59, 48, 0.1)', label: '未通过' },
            'blocked': { color: '#AF52DE', bg: 'rgba(175, 82, 222, 0.1)', label: '阻塞' },
            'pending': { color: '#86868B', bg: 'rgba(134, 134, 139, 0.1)', label: '待测试' }
        };

        const target = status || level;
        const theme = config[target] || config['P2'];

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: inline-block;
                    vertical-align: middle;
                }
                .badge {
                    display: inline-flex;
                    align-items: center;
                    padding: 4px 10px;
                    border-radius: 100px;
                    font-size: 11px;
                    font-weight: 600;
                    letter-spacing: -0.2px;
                    color: ${theme.color};
                    background: ${theme.bg};
                    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                    white-space: nowrap;
                    border: 0.5px solid rgba(0, 0, 0, 0.05);
                }
                :host(:hover) .badge {
                    transform: scale(1.05);
                    filter: brightness(1.05);
                }
            </style>
            <div class="badge">${theme.label}</div>
        `;
    }
}

customElements.define('qa-priority-badge', QaPriorityBadge);
