/**
 * 认证与登录/注册逻辑。
 */
(function () {
    'use strict';

    /**
     * 要求已登录，否则跳转到登录页。
     * 返回 token；如果未登录则跳转并抛出错误。
     */
    window.requireAuth = function () {
        const token = localStorage.getItem('token');
        if (!token) {
            window.location.href = '/login.html';
            throw new Error('未登录');
        }
        return token;
    };

    /**
     * 退出登录 — 清除本地状态并跳转到登录页。
     */
    window.logout = function () {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        window.location.href = '/login.html';
    };

    document.addEventListener('DOMContentLoaded', function () {
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');
        const messageEl = document.getElementById('message');

        function showMessage(text, type) {
            if (!messageEl) return;
            messageEl.textContent = text;
            messageEl.className = 'message ' + type;
            messageEl.style.display = 'block';
        }

        // ── 登录表单 ──
        if (loginForm) {
            loginForm.addEventListener('submit', async function (e) {
                e.preventDefault();
                const btn = loginForm.querySelector('button[type="submit"]');
                const username = document.getElementById('username').value.trim();
                const password = document.getElementById('password').value;
                try {
                    btn.disabled = true;
                    btn.textContent = '登录中...';
                    const data = await api.post('/auth/login', { username: username, password: password });
                    localStorage.setItem('token', data.token);
                    localStorage.setItem('username', data.username);
                    window.location.href = '/index.html';
                } catch (err) {
                    showMessage(err.message, 'error');
                    btn.disabled = false;
                    btn.textContent = '登 录';
                }
            });
        }

        // ── 注册表单 ──
        if (registerForm) {
            registerForm.addEventListener('submit', async function (e) {
                e.preventDefault();
                const btn = registerForm.querySelector('button[type="submit"]');
                const username = document.getElementById('username').value.trim();
                const email = document.getElementById('email').value.trim();
                const password = document.getElementById('password').value;
                try {
                    btn.disabled = true;
                    btn.textContent = '注册中...';
                    await api.post('/auth/register', { username: username, email: email, password: password });
                    showMessage('注册成功！即将跳转到登录页...', 'success');
                    setTimeout(function () {
                        window.location.href = '/login.html';
                    }, 1500);
                } catch (err) {
                    showMessage(err.message, 'error');
                    btn.disabled = false;
                    btn.textContent = '注 册';
                }
            });
        }
    });
})();
