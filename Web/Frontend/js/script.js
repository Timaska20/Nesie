document.addEventListener("DOMContentLoaded", function () {
    const loginForm = document.getElementById("loginForm");
    const registerForm = document.getElementById("registerForm");
    const adminPanel = document.getElementById("adminPanel");
    const userPanel = document.getElementById("userPanel");
    const loginSection = document.getElementById("login");
    const registerSection = document.getElementById("registration");

    // Элемент для отображения ошибок
    function showError(message) {
        let errorDiv = document.getElementById("errorMessage");
        if (!errorDiv) {
            errorDiv = document.createElement("div");
            errorDiv.id = "errorMessage";
            errorDiv.style.color = "red";
            errorDiv.style.marginTop = "10px";
            registerForm.appendChild(errorDiv);
        }
        errorDiv.innerText = message;
    }

    // Проверяем, есть ли сохраненный токен
    const token = localStorage.getItem("authToken");
    const username = localStorage.getItem("username");

    if (token && username) {
        showUserInterface(username);
    }

    function showUserInterface(username) {
        loginSection.style.display = "none";
        registerSection.style.display = "none";

        if (username === "admin") {
            adminPanel.style.display = "block";
        } else {
            userPanel.style.display = "block";
        }

        addLogoutButton();
    }

    async function loginUser(username, password) {
        const formData = new URLSearchParams();
        formData.append("username", username);
        formData.append("password", password);

        const response = await fetch("/api/token/", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: formData,
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem("authToken", data.access_token);
            localStorage.setItem("username", username);

            showUserInterface(username);
        } else {
            alert("Ошибка входа. Проверьте логин и пароль.");
        }
    }

    async function registerUser(username, password) {
        const response = await fetch("/api/register/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ username, password }),
        });

        const data = await response.json();
        if (response.ok) {
            alert("Регистрация успешна! Теперь войдите в систему.");
        } else {
            showError(data.detail || "Ошибка регистрации.");
        }
    }

    function logout() {
        localStorage.removeItem("authToken");
        localStorage.removeItem("username");
        location.reload();
    }

    function addLogoutButton() {
        if (!document.getElementById("logoutButton")) {
            const logoutButton = document.createElement("button");
            logoutButton.id = "logoutButton";
            logoutButton.innerText = "Выйти";
            logoutButton.style.marginTop = "20px";
            logoutButton.addEventListener("click", logout);

            if (adminPanel.style.display === "block") {
                adminPanel.appendChild(logoutButton);
            } else if (userPanel.style.display === "block") {
                userPanel.appendChild(logoutButton);
            }
        }
    }

    if (loginForm) {
        loginForm.addEventListener("submit", function (event) {
            event.preventDefault();
            const username = document.getElementById("login_username").value;
            const password = document.getElementById("login_password").value;
            loginUser(username, password);
        });
    }

    if (registerForm) {
        registerForm.addEventListener("submit", function (event) {
            event.preventDefault();
            const username = document.getElementById("register_username").value;
            const password = document.getElementById("register_password").value;
            registerUser(username, password);
        });
    }
});
