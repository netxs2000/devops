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
        this._payloadCache = null;
        this._lastToken = null;
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
    },

    /**
     * 解析 JWT Token 中的载荷 (Payload) 并缓存
     */
    getPayload() {
        const token = this.getToken();
        if (!token) {
            this._payloadCache = null;
            return null;
        }

        // 如果缓存的 token 没变且已经有解析好的 payload，直接返回
        if (this._lastToken === token && this._payloadCache) {
            return this._payloadCache;
        }

        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function (c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));

            const payload = JSON.parse(jsonPayload);
            this._payloadCache = payload;
            this._lastToken = token;
            return payload;
        } catch (e) {
            console.error("JWT 解析失败", e);
            this._payloadCache = null;
            return null;
        }
    },

    /**
     * 检查是否拥有特定角色
     */
    hasRole(roleCode) {
        const payload = this.getPayload();
        if (!payload || !payload.roles) return false;
        return payload.roles.includes('SYSTEM_ADMIN') || payload.roles.includes(roleCode);
    },

    /**
     * 检查是否拥有特定权限点
     * RBAC 2.0: 支持通配符 * 代表所有权限
     */
    hasPermission(permissionCode) {
        const payload = this.getPayload();
        if (!payload) return false;
        // 超管角色直接放行
        if (payload.roles && payload.roles.includes('SYSTEM_ADMIN')) return true;
        if (!payload.permissions) return false;
        // 通配符权限放行
        if (payload.permissions.includes('*')) return true;
        return payload.permissions.includes(permissionCode);
    },

    /**
     * 获取用户的数据范围
     * @returns {number} data_scope (1-5)
     */
    getDataScope() {
        const payload = this.getPayload();
        return payload ? (payload.data_scope || 5) : 5;
    },

    /**
     * 获取用户的部门ID
     */
    getDepartmentId() {
        const payload = this.getPayload();
        return payload ? payload.department_id : null;
    },

    /**
     * 是否是平台管理员
     */
    isAdmin() {
        return this.hasRole('SYSTEM_ADMIN');
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
        container.className = 'sys-notification-container';
        document.body.appendChild(container);

        // SSE Listener
        if (Auth.isLoggedIn()) {
            this.startSSE();
        }
    },

    startSSE() {
        if (this.eventSource) this.eventSource.close();

        const token = Auth.getToken();
        this.eventSource = new EventSource(`/notifications/stream?token=${token}`);

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.show(data.message, data.type || 'info', data.metadata);
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

    show(message, type = 'info', metadata = null) {
        this.init();
        const container = document.getElementById('notification-container');

        const toast = document.createElement('div');
        toast.className = `sys-toast sys-toast--${type}`;

        const icon = {
            success: '✅',
            error: '❌',
            info: 'ℹ️',
            warning: '⚠️'
        }[type];

        let contentHtml = `
            <span class="sys-toast__icon">${icon}</span>
            <div class="sys-toast__content">
                <div class="sys-toast__title">${message}</div>
        `;

        if (metadata) {
            contentHtml += `<div class="sys-toast__meta">`;

            if (metadata.failure_reason) {
                contentHtml += `<div>Reason: <span style="color: var(--status-error);">${metadata.failure_reason}</span></div>`;
            }
            if (metadata.test_case_title) {
                contentHtml += `<div>Case: ${metadata.test_case_title}</div>`;
            }
            if (metadata.requirement_title) {
                contentHtml += `<div>Req: ${metadata.requirement_title}</div>`;
            }
            if (metadata.executor) {
                contentHtml += `<div>By: ${metadata.executor.split(' ')[0]}</div>`;
            }

            contentHtml += `</div>`;
        }

        contentHtml += `</div>`;
        toast.innerHTML = contentHtml;
        container.appendChild(toast);

        // Animate in
        setTimeout(() => toast.classList.add('is-active'), 10);

        // Auto remove
        const duration = (type === 'error' || metadata) ? 8000 : 5000;
        setTimeout(() => {
            toast.classList.remove('is-active');
            setTimeout(() => toast.remove(), 400);
        }, duration);
    }
};

window.NotificationSystem = NotificationSystem;
window.addEventListener('DOMContentLoaded', () => NotificationSystem.init());
