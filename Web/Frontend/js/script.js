document.addEventListener("DOMContentLoaded", function () {
    const loginForm = document.getElementById("loginForm");
    const registerForm = document.getElementById("registerForm");
    const userPanel = document.getElementById("userPanel");
    const adminPanel = document.getElementById("adminPanel");
    const usernameDisplay = document.getElementById("usernameDisplay");
    const logoutButton = document.getElementById("logoutButton");

    function saveToken(token) {
        localStorage.setItem("access_token", token);
    }

    function getToken() {
        return localStorage.getItem("access_token");
    }

    async function getUserRole() {
        const token = getToken();
        if (!token) return null;

        try {
            const response = await fetch("/api/userinfo/", {
                method: "GET",
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (!response.ok) throw new Error("Ошибка авторизации");

            return await response.json();
        } catch (error) {
            console.error("Ошибка получения информации о пользователе:", error);
            return null;
        }
    }

    if (registerForm) {
        registerForm.addEventListener("submit", async function (event) {
            event.preventDefault();
            const username = document.getElementById("register_username").value;
            const password = document.getElementById("register_password").value;

            const response = await fetch("/api/register/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });

            if (response.ok) {
                alert("Регистрация успешна! Войдите в систему.");
            } else {
                alert("Ошибка регистрации.");
            }
        });
    }

    if (loginForm) {
        loginForm.addEventListener("submit", async function (event) {
            event.preventDefault();
            const username = document.getElementById("login_username").value;
            const password = document.getElementById("login_password").value;

            const formData = new URLSearchParams();
            formData.append("username", username);
            formData.append("password", password);

            const response = await fetch("/api/token/", {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                saveToken(data.access_token);

                const user = await getUserRole();
                if (user) {
                    window.location.href = user.is_admin ? "admin.html" : "user.html";
                }
            } else {
                alert("Ошибка входа. Проверьте логин и пароль.");
            }
        });
    }

    async function displayUserPanel() {
        const token = getToken();
        if (!token) return;

        const user = await getUserRole();
        if (!user) return;

        usernameDisplay.textContent = user.username;
        if (userPanel) userPanel.style.display = "block";
        if (user.is_admin && adminPanel) adminPanel.style.display = "block";
    }

    if (logoutButton) {
        logoutButton.addEventListener("click", function () {
            localStorage.removeItem("access_token");
            window.location.href = "index.html";
        });
    }

    displayUserPanel();
});