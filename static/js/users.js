/**
 * 用户管理页面逻辑。
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        const tableBody = document.getElementById('userTableBody');
        const userForm = document.getElementById('userForm');
        const messageEl = document.getElementById('message');
        const formTitle = document.getElementById('formTitle');
        const userIdInput = document.getElementById('userId');
        const cancelEditBtn = document.getElementById('cancelEdit');
        const userCountEl = document.getElementById('userCount');

        // 缓存已加载的用户数据，避免在 HTML 属性中嵌入敏感值
        let userCache = {};

        function showMessage(text, type) {
            if (!messageEl) return;
            messageEl.textContent = text;
            messageEl.className = 'message ' + type;
            messageEl.style.display = 'block';
            setTimeout(function () { messageEl.style.display = 'none'; }, 3000);
        }

        async function loadUsers() {
            try {
                const users = await api.get('/users');
                // 缓存用户数据供编辑/删除使用
                userCache = {};
                users.forEach(function (u) { userCache[u.id] = u; });

                if (tableBody) {
                    tableBody.innerHTML = users.length === 0
                        ? '<tr><td colspan="5" style="text-align:center;color:#999;">暂无用户数据</td></tr>'
                        : users.map(function (u) {
                            return '<tr>' +
                                '<td>' + u.id + '</td>' +
                                '<td>' + escapeHtml(u.username) + '</td>' +
                                '<td>' + escapeHtml(u.email) + '</td>' +
                                '<td>' + new Date(u.createdAt).toLocaleString('zh-CN') + '</td>' +
                                '<td>' +
                                    '<div class="actions">' +
                                        '<button class="btn btn-primary js-edit" data-user-id="' + u.id + '">编辑</button>' +
                                        '<button class="btn btn-danger js-delete" data-user-id="' + u.id + '">删除</button>' +
                                    '</div>' +
                                '</td>' +
                            '</tr>';
                        }).join('');
                }
                if (userCountEl) userCountEl.textContent = users.length;
            } catch (err) {
                showMessage('加载用户列表失败: ' + err.message, 'error');
            }
        }

        // 事件委托：编辑和删除按钮
        if (tableBody) {
            tableBody.addEventListener('click', function (e) {
                const editBtn = e.target.closest('.js-edit');
                const deleteBtn = e.target.closest('.js-delete');

                if (editBtn) {
                    const userId = parseInt(editBtn.dataset.userId, 10);
                    const user = userCache[userId];
                    if (user) {
                        fillEditForm(user.id, user.username, user.email);
                    }
                }

                if (deleteBtn) {
                    const userId = parseInt(deleteBtn.dataset.userId, 10);
                    deleteUser(userId);
                }
            });
        }

        function escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        function fillEditForm(id, username, email) {
            document.getElementById('username').value = username;
            document.getElementById('email').value = email;
            const pwdField = document.getElementById('password');
            pwdField.value = '';
            pwdField.placeholder = '留空则不修改密码';
            pwdField.removeAttribute('required');
            userIdInput.value = id;
            formTitle.textContent = '编辑用户';
            cancelEditBtn.style.display = 'inline-block';
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        function resetForm() {
            userForm.reset();
            userIdInput.value = '';
            document.getElementById('password').setAttribute('required', '');
            formTitle.textContent = '添加用户';
            cancelEditBtn.style.display = 'none';
            // 恢复提交按钮状态
            const submitBtn = userForm.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = '提 交';
            }
        }

        async function deleteUser(id) {
            if (!confirm('确定要删除该用户吗？')) return;
            try {
                await api.delete('/users/' + id);
                showMessage('用户已删除', 'success');
                loadUsers();
            } catch (err) {
                showMessage('删除失败: ' + err.message, 'error');
            }
        }

        if (cancelEditBtn) {
            cancelEditBtn.addEventListener('click', resetForm);
        }

        if (userForm) {
            userForm.addEventListener('submit', async function (e) {
                e.preventDefault();

                const submitBtn = userForm.querySelector('button[type="submit"]');
                // 防重复提交
                if (submitBtn.disabled) return;
                submitBtn.disabled = true;
                submitBtn.textContent = '提交中...';

                const username = document.getElementById('username').value.trim();
                const email = document.getElementById('email').value.trim();
                const password = document.getElementById('password').value;
                const id = userIdInput.value;
                const body = { username: username, email: email };
                if (password) body.password = password;  // 编辑时空密码=不修改密码

                try {
                    if (id) {
                        await api.put('/users/' + id, body);
                        showMessage('用户已更新', 'success');
                    } else {
                        await api.post('/users', body);
                        showMessage('用户已创建', 'success');
                    }
                    resetForm();
                    loadUsers();
                } catch (err) {
                    showMessage('操作失败: ' + err.message, 'error');
                    submitBtn.disabled = false;
                    submitBtn.textContent = '提 交';
                }
            });
        }

        loadUsers();
    });
})();
