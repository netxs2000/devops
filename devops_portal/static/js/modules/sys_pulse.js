import { Api, UI, Auth } from './sys_core.js';

/**
 * @file sys_pulse.js
 * @description的心情指数打卡逻辑 (Developer Experience Pulse)
 */
const SysPulseHandler = {
    state: {
        userEmail: null,
        submitted: false
    },

    /**
     * 初始化
     */
    async init() {
        console.log("Sys Pulse: Monitoring developer vibes...");

        // 获取当前用户邮箱
        const payload = Auth.getPayload();
        if (payload && payload.sub) {
            this.state.userEmail = payload.sub;
        } else {
            // 回退处理：如果 Auth 没获取到，尝试从 DOM 或默认
            this.state.userEmail = "anonymous@tjhq.com";
        }

        this.bindEvents();
        await this.checkStatus();
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        const container = document.getElementById('faces-container');
        if (container) {
            container.addEventListener('click', (e) => {
                const btn = e.target.closest('.js-pulse-btn');
                if (btn && !btn.disabled) {
                    const score = parseInt(btn.dataset.score);
                    this.submitFeedback(score);
                }
            });
        }
    },

    /**
     * 检查今日打卡状态
     */
    async checkStatus() {
        try {
            const data = await Api.get(`/devex-pulse/status/${this.state.userEmail}`);
            if (data.submitted) {
                this.state.submitted = true;
                this.showResult(data.message || "您今日已完成心情打卡，感谢反馈！", "success");
                this.disableButtons();
                if (data.score) {
                    this.highlightButton(data.score);
                }
            }
        } catch (e) {
            console.error("Pulse status check failed", e);
        }
    },

    /**
     * 提交打卡
     */
    async submitFeedback(score) {
        if (this.state.submitted) return;

        UI.toggleLoading("提交反馈中...", true);
        try {
            const res = await Api.post('/devex-pulse/submit', {
                user_email: this.state.userEmail,
                score: score
            });

            this.state.submitted = true;
            this.showResult(res.message || "打卡成功！愿您的研发体验日益精进。", "success");
            this.disableButtons();
            this.highlightButton(score);

            UI.showToast("打卡成功", "success");
        } catch (e) {
            this.showResult(e.message || "提交失败，请稍后重试", "error");
            UI.showToast("提交失败", "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    /**
     * 显示结果信息
     */
    showResult(msg, type) {
        const el = document.getElementById('message');
        if (!el) return;

        el.textContent = msg;
        el.className = `sys-pulse_message is-${type}`;
        el.style.display = 'block';
    },

    /**
     * 禁用按钮
     */
    disableButtons() {
        document.querySelectorAll('.js-pulse-btn').forEach(b => {
            b.disabled = true;
        });
    },

    /**
     * 高亮选中项
     */
    highlightButton(score) {
        const btn = document.querySelector(`.js-pulse-btn[data-score="${score}"]`);
        if (btn) btn.classList.add('is-selected');
    }
};

export default SysPulseHandler;

// 自动初始化
document.addEventListener('DOMContentLoaded', () => {
    SysPulseHandler.init();
});
