// Функция для регистрации пользователя
document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('register_username').value;
    const password = document.getElementById('register_password').value;

    try {
        const response = await fetch('/api/register/', {  // Обязательно с `/` в конце!
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка регистрации');
        }

        const data = await response.json();
        alert(`Пользователь ${data.username} успешно зарегистрирован!`);
    } catch (error) {
        alert(`Ошибка регистрации: ${error.message}`);
    }
});

// Функция для входа пользователя
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('login_username').value;
    const password = document.getElementById('login_password').value;

    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    try {
        const response = await fetch('/api/token/', {  // Обязательно с `/` в конце!
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Ошибка входа: ${errorText}`);
        }

        const data = await response.json();
        alert(`Успешный вход. Токен: ${data.access_token}`);

        localStorage.setItem('access_token', data.access_token);

        // Показываем панели пользователя и администратора
        document.getElementById('userPanel').style.display = 'block';
        document.getElementById('adminPanel').style.display = 'block';
    } catch (error) {
        alert(error.message);
    }
});
