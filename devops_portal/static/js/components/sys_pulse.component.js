/**
 * @file sys_pulse.component.js
 * @description DevEx Pulse Component (Web Component)
 */
import { Api, UI, Auth } from '../modules/sys_core.js';

class SysPulse extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.state = {
            submitted: false,
            score: null,
            email: null
        };
    }

    async connectedCallback() {
        // Auth check
        const payload = Auth.getPayload();
        this.state.email = (payload && payload.sub) ? payload.sub : "anonymous@tjhq.com";

        await this.checkStatus();
        this.render();
    }

    async checkStatus() {
        try {
            const data = await Api.get(`/devex-pulse/status/${this.state.email}`);
            if (data.submitted) {
                this.state.submitted = true;
                this.state.score = data.score;
            }
        } catch (e) {
            console.error("Pulse status check failed", e);
        }
    }

    render() {
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100%;
                    font-family: 'Inter', system-ui, sans-serif;
                    background: transparent; 
                }
                
                .container {
                    background: rgba(255, 255, 255, 0.8);
                    backdrop-filter: blur(20px);
                    padding: 40px;
                    border-radius: 24px;
                    text-align: center;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.05);
                    max-width: 500px;
                    width: 100%;
                    box-sizing: border-box;
                }

                h1 { font-size: 24px; font-weight: 700; color: #1d1d1f; margin: 0 0 12px 0; }
                p { color: #86868b; margin: 0 0 32px 0; font-size: 15px; }

                .faces-grid {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 24px;
                    gap: 12px;
                }

                .face-btn {
                    background: #f5f5f7;
                    border: none;
                    border-radius: 16px;
                    width: 64px;
                    height: 64px;
                    font-size: 28px;
                    cursor: pointer;
                    transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .face-btn:hover:not(:disabled) {
                    transform: scale(1.1);
                    background: white;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }

                .face-btn.selected {
                    background: #0071e3;
                    color: white;
                    transform: scale(1.1);
                    box-shadow: 0 8px 16px rgba(0, 113, 227, 0.3);
                }

                .face-btn:disabled {
                    cursor: default;
                    opacity: 0.5;
                }
                .face-btn.selected:disabled {
                    opacity: 1;
                }

                .message {
                    font-size: 14px;
                    margin-top: 20px;
                    padding: 12px;
                    border-radius: 12px;
                    opacity: 0;
                    transform: translateY(10px);
                    transition: all 0.3s;
                }
                .message.show { opacity: 1; transform: translateY(0); }
                .message.success { background: #E8F5E9; color: #2E7D32; }
                .message.error { background: #FFEBEE; color: #C62828; }

                /* Tooltip logic via title attribute mainly, but simplified here */
            </style>

            <div class="container">
                <h1>DevEx Pulse</h1>
                <p>How was your developer experience today?</p>

                <div class="faces-grid">
                    <button class="face-btn js-btn" data-score="1" title="Very Dissatisfied">😫</button>
                    <button class="face-btn js-btn" data-score="2" title="Dissatisfied">😕</button>
                    <button class="face-btn js-btn" data-score="3" title="Neutral">😐</button>
                    <button class="face-btn js-btn" data-score="4" title="Satisfied">🙂</button>
                    <button class="face-btn js-btn" data-score="5" title="Very Satisfied">🤩</button>
                </div>

                <div id="msg" class="message"></div>
            </div>
        `;

        if (this.state.submitted) {
            this.highlight(this.state.score);
            this.showMessage("You've already checked in today. Keep rocking!", 'success');
            this.disableAll();
        } else {
            this.shadowRoot.querySelectorAll('.js-btn').forEach(btn => {
                btn.addEventListener('click', () => this.submit(btn.dataset.score));
            });
        }
    }

    async submit(score) {
        if (this.state.submitted) return;

        const container = this.shadowRoot.querySelector('.container');
        container.style.opacity = '0.7';

        try {
            await Api.post('/devex-pulse/submit', {
                user_email: this.state.email,
                score: parseInt(score)
            });
            this.state.submitted = true;
            this.highlight(score);
            this.disableAll();
            this.showMessage("Feedback received! Promoting flow state...", 'success');
        } catch (e) {
            this.showMessage("Failed to submit. Try again.", 'error');
        } finally {
            container.style.opacity = '1';
        }
    }

    highlight(score) {
        this.shadowRoot.querySelectorAll('.js-btn').forEach(btn => {
            if (parseInt(btn.dataset.score) === parseInt(score)) {
                btn.classList.add('selected');
            } else {
                btn.classList.remove('selected');
            }
        });
    }

    disableAll() {
        this.shadowRoot.querySelectorAll('.js-btn').forEach(btn => btn.disabled = true);
    }

    showMessage(text, type) {
        const msg = this.shadowRoot.getElementById('msg');
        msg.textContent = text;
        msg.className = `message show ${type}`;
    }
}

customElements.define('sys-pulse', SysPulse);
