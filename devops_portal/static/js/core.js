/**
 * @file core.js
 * @description 核心基础设施，提供全局 Api、UI 和 Auth 工具类。
 * @author Antigravity
 */

/**
 * 统一网络请求工具类
 */
class Api {
    /**
     * 发送网络请求的通用方法
     * @param {string} url 请求路径
     * @param {Object} options fetch 配置项
     * @returns {Promise<any>} 返回 JSON 数据
     * @throws {Error} 请求失败或状态码非 200 时抛出异常
     */
    static async request(url, options = {}) {
        const token = Auth.getToken();
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(url, { ...options, headers });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || `Request failed with status ${response.status}`);
        }
        return data;
    }

    static get(url) { return this.request(url, { method: 'GET' }); }
    static post(url, body) { return this.request(url, { method: 'POST', body: JSON.stringify(body) }); }
}

/**
 * 全局配置信息
 */
const Config = {
    GITLAB_URL: 'https://gitlab.com', // 示例地址，实际会从环境变量或通过其它方式获取
    // 敏感 token 不应直接放在前端，仅作占位参考
};

/**
 * 统一 UI 交互工具类
 */
class UI {
    /**
     * 显示全局 Loading 状态
     * @param {string} message 提示文本
     * @param {boolean} show 是否显示
     */
    static toggleLoading(message = "Synchronizing Data...", show = true) {
        const loadingDiv = document.getElementById('loading');
        if (loadingDiv) {
            loadingDiv.innerText = message;
            loadingDiv.style.display = show ? 'block' : 'none';
        }
    }

    /**
     * 显示系统通知（Toast）
     * @param {string} message 消息正文
     * @param {string} type 类型: 'success' | 'error' | 'info'
     */
    static showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const t = document.createElement('div');
        t.className = `toast toast-${type}`;
        t.innerHTML = `
            <div style="font-size:18px"></div>
            <div style="flex:1">
                <div style="font-weight:600; font-size:13px; color:var(--text-main)">System Update</div>
                <div style="font-size:12px; color:var(--text-dim);">${message}</div>
            </div>
        `;
        container.appendChild(t);
        setTimeout(() => {
            t.style.opacity = '0';
            t.style.transform = 'translateX(20px)';
            setTimeout(() => t.remove(), 500);
        }, 6000);
    }

    /**
     * 数字增长动画效果
     * @param {string} id 元素 ID
     * @param {number} start 起始值
     * @param {number} end 目标值
     * @param {number} duration 持续时间(ms)
     */
    static animateValue(id, start, end, duration) {
        const obj = document.getElementById(id);
        if (!obj) return;
        const startTimestamp = performance.now();
        const step = (timestamp) => {
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const current = Math.floor(progress * (end - start) + start);
            obj.innerText = current + (id.includes('rate') ? '%' : '');
            if (progress < 1) {
                window.requestAnimationFrame(step);
            } else {
                obj.innerText = end + (id.includes('rate') ? '%' : '');
            }
        };
        window.requestAnimationFrame(step);
    }

    /**
     * 切换导航菜单折叠状态
     * @param {HTMLElement} el 点击的标题元素
     */
    static toggleNav(el) {
        console.log('UI.toggleNav triggered on:', el);
        // Ensure we find the parent .nav-group regardless of which element was passed
        const group = el.closest('.nav-group');
        if (group) {
            group.classList.toggle('expanded');
            console.log('New state expanded:', group.classList.contains('expanded'));
        } else {
            console.error('toggleNav: No .nav-group parent found for', el);
        }
    }
}

// Ensure UI is globally available
window.UI = UI;
