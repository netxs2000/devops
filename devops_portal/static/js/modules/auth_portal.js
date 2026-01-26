/**
 * @file auth_portal.js
 * @description 身份认证与注册门户逻辑 (Auth Domain)
 * @author Antigravity
 */

import { Auth } from './sys_core.js';

const AuthPortal = {
    init() {
        console.log("Auth Portal Initialized.");
        this.bindEvents();
        this.checkInitialState();
    },

    bindEvents() {
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }

        const registerForm = document.getElementById('registerForm');
        if (registerForm) {
            registerForm.addEventListener('submit', (e) => this.handleRegister(e));
        }
    },

    checkInitialState() {
        // 如果已登录且在登录/注册页，直接跳转首页
        if (Auth.isLoggedIn() && (location.pathname.includes('login') || location.pathname.includes('register'))) {
            location.href = 'index.html';
        }
    },

    async handleLogin(e) {
        e.preventDefault();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        const btn = document.getElementById('loginBtn');

        if (!email || !password) {
            this.showAlert('请填写账号和密码', 'error');
            return;
        }

        this.setLoading(btn, true, '登录中...');

        try {
            const formData = new URLSearchParams();
            formData.append('username', email);
            formData.append('password', password);

            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                this.showAlert('登录成功！正在跳转...', 'success');
                Auth.setToken(result.access_token);
                localStorage.removeItem('sd_user');
                setTimeout(() => location.href = '/index.html', 800);
            } else {
                this.showAlert(`Error: ${result.detail || '用户名或密码错误'}`, 'error');
                this.setLoading(btn, false, '登 录');
            }
        } catch (err) {
            this.showAlert('网络错误，请检查连接', 'error');
            this.setLoading(btn, false, '登 录');
        }
    },

    async handleRegister(e) {
        e.preventDefault();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        const fullName = document.getElementById('fullName').value.trim();
        const employeeId = document.getElementById('employeeId').value.trim();
        const deptCode = document.getElementById('departmentCode').value.trim();
        const btn = document.getElementById('registerBtn');

        // 校验
        const allowedDomains = ['tjhq.com', 'mofit.com.cn', 'szlongtu.com'];
        const domain = email.split('@')[1]?.toLowerCase();
        if (!allowedDomains.includes(domain)) {
            this.showAlert(`仅支持公司邮箱注册: ${allowedDomains.join(', ')}`, 'error');
            return;
        }

        this.setLoading(btn, true, '注册中...');

        try {
            const payload = {
                email, password, full_name: fullName,
                employee_id: employeeId || null,
                department_code: deptCode || null
            };

            const response = await fetch('/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (response.ok) {
                this.showAlert('注册成功！请使用新账号登录', 'success');
                const form = document.getElementById('registerForm');
                form.reset();
                form.classList.add('u-hide');

                const successAction = document.createElement('div');
                successAction.className = 'u-text-center u-mt-32';

                const link = document.createElement('a');
                link.href = 'index.html';
                link.className = 'btn-primary u-inline-block u-no-underline';
                link.textContent = '前往登录页面';

                successAction.appendChild(link);
                document.querySelector('.g-card').appendChild(successAction);
            } else {
                this.showAlert(`Error: ${result.detail || '注册失败'}`, 'error');
                this.setLoading(btn, false, '注册账号');
            }
        } catch (err) {
            this.showAlert('网络错误，请稍后重试', 'error');
            this.setLoading(btn, false, '注册账号');
        }
    },

    showAlert(message, type) {
        const alertBox = document.getElementById('alertBox');
        if (!alertBox) return;
        alertBox.textContent = message;
        alertBox.className = `alert ${type} show`;
        window.scrollTo({ top: 0, behavior: 'smooth' });
        if (type === 'error') {
            setTimeout(() => alertBox.classList.remove('show'), 5000);
        }
    },

    setLoading(btn, isLoading, text) {
        if (!btn) return;
        btn.disabled = isLoading;
        btn.textContent = text;
    }
};

AuthPortal.init();
export default AuthPortal;
