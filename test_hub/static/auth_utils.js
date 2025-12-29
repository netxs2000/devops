/**
 * Service Desk Frontend Authentication & API Utilities
 * 提供统一的认证管理和 API 请求拦截功能
 */

const AUTH_CONFIG = {
    TOKEN_KEY: 'sd_token',
    USER_KEY: 'sd_user',
    LOGIN_PAGE: 'service_desk_login.html'
};

const Auth = {
    /**
     * 获取存储的 Token
     */
    getToken() {
        return localStorage.getItem(AUTH_CONFIG.TOKEN_KEY);
    },

    /**
     * 保存 Token
     */
    setToken(token) {
        localStorage.setItem(AUTH_CONFIG.TOKEN_KEY, token);
    },

    /**
     * 清除认证信息并跳转到登录页
     */
    logout() {
        localStorage.removeItem(AUTH_CONFIG.TOKEN_KEY);
        localStorage.removeItem(AUTH_CONFIG.USER_KEY);
        window.location.href = AUTH_CONFIG.LOGIN_PAGE;
    },

    /**
     * 检查是否已登录
     */
    isLoggedIn() {
        return !!this.getToken();
    },

    /**
     * 获取当前用户信息
     * 如果缓存中有则返回缓存，否则请求后端
     */
    async getCurrentUser() {
        const cachedUser = localStorage.getItem(AUTH_CONFIG.USER_KEY);
        if (cachedUser) {
            try {
                return JSON.parse(cachedUser);
            } catch (e) {
                console.error("解析缓存用户信息失败", e);
            }
        }

        try {
            const user = await Api.get('/auth/me');
            localStorage.setItem(AUTH_CONFIG.USER_KEY, JSON.stringify(user));
            return user;
        } catch (error) {
            console.error("获取用户信息失败", error);
            if (error.status === 401) {
                this.logout();
            }
            return null;
        }
    }
};

const Api = {
    /**
     * 基础请求方法，包含常用的拦截逻辑
     */
    async request(path, options = {}) {
        const token = Auth.getToken();

        // 默认 Header
        const headers = {
            'Accept': 'application/json',
            ...(options.headers || {})
        };

        // 如果有 Token 则注入
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const url = path.startsWith('http') ? path : path; // 相对路径

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            // 拦截 401 Unauthorized
            if (response.status === 401) {
                Auth.logout();
                throw { status: 401, message: '未授权或登录已过期' };
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw {
                    status: response.status,
                    message: errorData.detail || '请求失败',
                    data: errorData
                };
            }

            return await response.json();
        } catch (error) {
            throw error;
        }
    },

    get(path) {
        return this.request(path, { method: 'GET' });
    },

    post(path, data) {
        return this.request(path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    }
};

// 导出到全局供 HTML 使用
window.Auth = Auth;
window.Api = Api;

/**
 * Global Notification System
 */
const NotificationSystem = {
    init() {
        if (document.getElementById('notification-container')) return;
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            gap: 10px;
            pointer-events: none;
        `;
        document.body.appendChild(container);

        // SSE Listener
        if (Auth.isLoggedIn()) {
            this.startSSE();
        }
    },

    startSSE() {
        if (this.eventSource) this.eventSource.close();

        const token = Auth.getToken();
        // 因为 EventSource 不能原生传 Header，我们通过 URL 参数或 Cookie 处理，
        // 这里采用后台支持的 token 参数模式，或者简单的 open_browser 鉴权模拟
        this.eventSource = new EventSource(`/notifications/stream?token=${token}`);

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.show(data.message, data.type || 'info');
            } catch (e) {
                console.error("SSE Message parsing error", e);
            }
        };

        this.eventSource.onerror = () => {
            console.warn("SSE Connection lost. Retrying in 10s...");
            this.eventSource.close();
            setTimeout(() => this.startSSE(), 10000);
        };
    },

    show(message, type = 'info') {
        this.init();
        const container = document.getElementById('notification-container');

        const toast = document.createElement('div');
        const colors = {
            success: '#10b981',
            error: '#ef4444',
            info: '#3b82f6',
            warning: '#f59e0b'
        };

        toast.style.cssText = `
            background: rgba(15, 15, 35, 0.9);
            border-left: 4px solid ${colors[type]};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5);
            backdrop-filter: blur(8px);
            font-family: sans-serif;
            font-size: 14px;
            min-width: 250px;
            transform: translateX(120%);
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            pointer-events: auto;
            display: flex;
            align-items: center;
            gap: 10px;
        `;

        const icon = {
            success: '✅',
            error: '❌',
            info: 'ℹ️',
            warning: '⚠️'
        }[type];

        toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
        container.appendChild(toast);

        // Animate in
        setTimeout(() => toast.style.transform = 'translateX(0)', 10);

        // Auto remove
        setTimeout(() => {
            toast.style.transform = 'translateX(120%)';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
};

window.NotificationSystem = NotificationSystem;
window.addEventListener('DOMContentLoaded', () => NotificationSystem.init());
