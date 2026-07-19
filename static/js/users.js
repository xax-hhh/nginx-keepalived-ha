document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.getElementById('userTableBody');
    const userForm = document.getElementById('userForm');
    const messageEl = document.getElementById('message');
    const formTitle = document.getElementById('formTitle');
    const userIdInput = document.getElementById('userId');
    const cancelEditBtn = document.getElementById('cancelEdit');
    const userCountEl = document.getElementById('userCount');

    function showMessage(text, type) {
        if (!messageEl) return;
        messageEl.textContent = text;
        messageEl.className = `message ${type}`;
        messageEl.style.display = 'block';
        setTimeout(() => { messageEl.style.display = 'none'; }, 3000);
    }

    async function loadUsers() {
        try {
            const users = await api.get('/users');
            if (tableBody) {
                tableBody.innerHTML = users.length === 0
                    ? '<tr><td colspan="5" style="text-align:center;color:#999;">暂无用户数据</td></tr>'
                    : users.map(u => `
                        <tr>
                            <td>${u.id}</td>
                            <td>${escapeHtml(u.username)}</td>
                            <td>${escapeHtml(u.email)}</td>
                            <td>${new Date(u.createdAt).toLocaleString('zh-CN')}</td>
                            <td>
                                <div class="actions">
                                    <button class="btn btn-primary" onclick="editUser(${u.id}, '${escapeHtml(u.username)}', '${escapeHtml(u.email)}')">编辑</button>
                                    <button class="btn btn-danger" onclick="deleteUser(${u.id})">删除</button>
                                </div>
                            </td>
                        </tr>
                    `).join('');
            }
            if (userCountEl) userCountEl.textContent = users.length;
        } catch (err) {
            showMessage('加载用户列表失败: ' + err.message, 'error');
        }
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function resetForm() {
        userForm.reset();
        userIdInput.value = '';
        formTitle.textContent = '添加用户';
        cancelEditBtn.style.display = 'none';
    }

    window.editUser = async function(id, username, email) {
        document.getElementById('username').value = username;
        document.getElementById('email').value = email;
        document.getElementById('password').value = '';
        document.getElementById('password').placeholder = '留空则不修改密码';
        userIdInput.value = id;
        formTitle.textContent = '编辑用户';
        cancelEditBtn.style.display = 'inline-block';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    window.deleteUser = async function(id) {
        if (!confirm('确定要删除该用户吗？')) return;
        try {
            await api.delete(`/users/${id}`);
            showMessage('用户已删除', 'success');
            loadUsers();
        } catch (err) {
            showMessage('删除失败: ' + err.message, 'error');
        }
    };

    if (cancelEditBtn) {
        cancelEditBtn.addEventListener('click', resetForm);
    }

    if (userForm) {
        userForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value.trim();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const id = userIdInput.value;
            const body = { username, email, password };
            try {
                if (id) {
                    await api.put(`/users/${id}`, body);
                    showMessage('用户已更新', 'success');
                } else {
                    await api.post('/users', body);
                    showMessage('用户已创建', 'success');
                }
                resetForm();
                loadUsers();
            } catch (err) {
                showMessage('操作失败: ' + err.message, 'error');
            }
        });
    }

    loadUsers();
});
