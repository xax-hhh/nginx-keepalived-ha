document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const messageEl = document.getElementById('message');

    function showMessage(text, type) {
        if (!messageEl) return;
        messageEl.textContent = text;
        messageEl.className = `message ${type}`;
        messageEl.style.display = 'block';
    }

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            try {
                const data = await api.post('/auth/login', { username, password });
                localStorage.setItem('token', data.token);
                localStorage.setItem('username', data.username);
                window.location.href = '/index.html';
            } catch (err) {
                showMessage(err.message, 'error');
            }
        });
    }

    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value.trim();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            try {
                await api.post('/auth/register', { username, email, password });
                showMessage('注册成功！即将跳转到登录页...', 'success');
                setTimeout(() => {
                    window.location.href = '/login.html';
                }, 1500);
            } catch (err) {
                showMessage(err.message, 'error');
            }
        });
    }
});
