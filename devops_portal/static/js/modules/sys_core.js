/**
 * @file sys_core.js
 * @description 核心基础设施 (System Domain) - 提供全局 Auth, Api 和 UI 工具类。
 * @author Antigravity
 */

const AUTH_CONFIG = {
    TOKEN_KEY: 'sd_token',
    USER_KEY: 'sd_user',
    LOGIN_PAGE: '/'  // 重定向到首页，由全局登录 Modal 处理
};

/**
 * 身份认证管理
 */
export const Auth = {
    getToken() {
        return localStorage.getItem(AUTH_CONFIG.TOKEN_KEY);
    },

    setToken(token) {
        localStorage.setItem(AUTH_CONFIG.TOKEN_KEY, token);
    },

    logout() {
        localStorage.removeItem(AUTH_CONFIG.TOKEN_KEY);
        localStorage.removeItem(AUTH_CONFIG.USER_KEY);
        this._payloadCache = null;
        this._lastToken = null;
        // 触发全局登录事件，由 index.html 处理
        document.dispatchEvent(new CustomEvent('sys:logout'));
        window.location.href = AUTH_CONFIG.LOGIN_PAGE;
    },

    isLoggedIn() {
        const token = this.getToken();
        if (!token) return false;

        // 检查 JWT 是否过期
        try {
            const payload = this.getPayload();
            if (!payload || !payload.exp) return false;
            // exp 是 Unix 时间戳 (秒)
            if (Date.now() >= payload.exp * 1000) {
                // Token 已过期，清理并返回 false
                this.logout();
                return false;
            }
            return true;
        } catch (e) {
            return false;
        }
    },

    async getCurrentUser() {
        // DevEnv Fix: Always fetch from server to validate session
        // const cachedUser = localStorage.getItem(AUTH_CONFIG.USER_KEY);

        try {
            const user = await Api.get('/auth/me');
            if (user) {
                localStorage.setItem(AUTH_CONFIG.USER_KEY, JSON.stringify(user));
            }
            return user;
        } catch (error) {
            console.error("获取用户信息失败", error);
            // 明确捕获 401 未授权，触发登出
            if (error.status === 401) { this.logout(); }
            return null;
        }
    },

    getPayload() {
        const token = this.getToken();
        if (!token) {
            this._payloadCache = null;
            return null;
        }

        if (this._lastToken === token && this._payloadCache) {
            return this._payloadCache;
        }

        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => {
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

    hasRole(roleCode) {
        const payload = this.getPayload();
        if (!payload || !payload.roles) return false;
        return payload.roles.includes('SYSTEM_ADMIN') || payload.roles.includes(roleCode);
    },

    hasPermission(permissionCode) {
        const payload = this.getPayload();
        if (!payload) return false;
        if (payload.roles && payload.roles.includes('SYSTEM_ADMIN')) return true;
        if (!payload.permissions) return false;
        if (payload.permissions.includes('*')) return true;
        return payload.permissions.includes(permissionCode);
    },

    isAdmin() {
        return this.hasRole('SYSTEM_ADMIN');
    }
};

/**
 * 统一网络请求工具类
 */
export const Api = {
    async request(path, options = {}) {
        const token = Auth.getToken();
        const headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            ...(options.headers || {})
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(path, { ...options, headers });

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
        } catch (error) { throw error; }
    },

    get(path) { return this.request(path, { method: 'GET' }); },
    post(path, data) { return this.request(path, { method: 'POST', body: JSON.stringify(data) }); }
};

/**
 * 统一 UI 交互工具类
 */
export const UI = {
    toggleLoading(message = "Synchronizing Data...", show = true) {
        const loadingDiv = document.getElementById('loading');
        if (loadingDiv) {
            loadingDiv.innerText = message;
            if (show) {
                loadingDiv.classList.remove('u-hide');
                loadingDiv.classList.add('u-block');
            } else {
                loadingDiv.classList.add('u-hide');
                loadingDiv.classList.remove('u-block');
            }
        }
    },

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container') || document.getElementById('notification-container');
        if (!container) {
            // 如果容器不存在则创建 (NotificationSystem 逻辑迁移)
            const newContainer = document.createElement('div');
            newContainer.id = 'notification-container';
            newContainer.className = 'sys-notification-container';
            document.body.appendChild(newContainer);
            return this.showToast(message, type);
        }

        const toast = document.createElement('div');
        toast.className = `sys-toast sys-toast--${type}`;

        const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };

        const iconEl = document.createElement('span');
        iconEl.className = 'sys-toast__icon';
        iconEl.textContent = icons[type] || 'ℹ️';
        toast.appendChild(iconEl);

        const content = document.createElement('div');
        content.className = 'sys-toast__content';
        const title = document.createElement('div');
        title.className = 'sys-toast__title';
        title.textContent = 'System Notice';
        const meta = document.createElement('div');
        meta.className = 'sys-toast__meta';
        meta.textContent = message;

        content.appendChild(title);
        content.appendChild(meta);
        toast.appendChild(content);

        container.appendChild(toast);
        setTimeout(() => toast.classList.add('is-active'), 10);
        setTimeout(() => {
            toast.classList.remove('is-active');
            setTimeout(() => toast.remove(), 400);
        }, 6000);
    },

    animateValue(id, start, end, duration) {
        const obj = document.getElementById(id);
        if (!obj) return;
        const startTimestamp = performance.now();
        const step = (timestamp) => {
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const current = Math.floor(progress * (end - start) + start);
            obj.textContent = current + (id.includes('rate') ? '%' : '');
            if (progress < 1) {
                window.requestAnimationFrame(step);
            } else {
                obj.textContent = end + (id.includes('rate') ? '%' : '');
            }
        };
        window.requestAnimationFrame(step);
    },

    toggleNav(el) {
        const group = el.closest('.nav-group');
        if (group) group.classList.toggle('expanded');
    },

    showModal(id) {
        const modal = document.getElementById(id);
        if (modal) {
            modal.classList.remove('u-hide');
            modal.classList.add('u-flex');
        }
    },

    hideModal(id) {
        const modal = document.getElementById(id);
        if (modal) {
            modal.classList.add('u-hide');
            modal.classList.remove('u-flex');
        }
    }
};

/**
 * 全局通知监听 (SSE)
 */
export const NotificationSystem = {
    startSSE() {
        if (this.eventSource) this.eventSource.close();
        const token = Auth.getToken();
        if (!token) return;

        this.eventSource = new EventSource(`/notifications/stream?token=${token}`);
        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                UI.showToast(data.message, data.type || 'info');
            } catch (e) {
                console.error("SSE Message parsing error", e);
            }
        };
        this.eventSource.onerror = () => {
            this.eventSource.close();
            setTimeout(() => this.startSSE(), 10000);
        };
    }
};

// 保持对旧代码的临时全局注入，直到所有模块完成重构
window.Auth = Auth;
window.Api = Api;
window.UI = UI;
window.NotificationSystem = NotificationSystem;

export default { Auth, Api, UI, NotificationSystem };
