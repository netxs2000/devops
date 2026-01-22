
import { Auth } from './sys_core.js';

/**
 * @file auth_guard.js
 * @description 统一权限守卫，用于页面级访问控制
 */
export const AuthGuard = {
    /**
     * 强制检查权限，如果失败则替换页面内容为无权限提示
     * @param {string} requiredPermission - 需要的权限编码 (如 'USER:MANAGE')
     */
    enforce(requiredPermission) {
        if (!Auth.isLoggedIn() || !Auth.hasPermission(requiredPermission)) {
            this.renderUnauthorized();
            throw new Error(`Access Denied: Missing permission ${requiredPermission}`);
        }
    },

    /**
     * 渲染无权限界面
     */
    renderUnauthorized() {
        // 确保 CSS 已加载 (如果是动态加载的场景)
        // 使用 Shadow DOM 或直接覆盖 Body
        const overlayHtml = `
            <div class="sys-unauthorized-overlay" style="
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: var(--sys-bg-app, #ffffff);
                display: flex; flex-direction: column; align-items: center; justify-content: center;
                z-index: 9999;">
                <div class="sys-unauthorized-icon" style="font-size: 64px; margin-bottom: 24px;">🚫</div>
                <h2 class="sys-unauthorized-title u-text-h2 u-mb-12">权限不足</h2>
                <p class="sys-unauthorized-desc u-text-dim u-mb-24">您没有访问此页面的权限。</p>
                <button class="btn-primary js-btn-reload-parent" style="
                    padding: 10px 24px; background: var(--sys-primary); color: white; border: none; border-radius: 6px; cursor: pointer;">
                    返回首页
                </button>
            </div>
        `;

        // 停止页面其他渲染
        document.body.innerHTML = overlayHtml;

        // 绑定返回按钮事件
        document.body.addEventListener('click', (e) => {
            if (e.target.classList.contains('js-btn-reload-parent')) {
                // 如果在 iframe 中，尝试刷新父页面，否则跳转回首页
                if (window.parent && window.parent !== window) {
                    window.parent.location.reload();
                } else {
                    window.location.href = '/static/index.html'; // 假设首页位置
                }
            }
        });
    }
};

export default AuthGuard;
