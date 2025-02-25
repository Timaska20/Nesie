let accessToken = "";

// Регистрация
document.getElementById("registerForm").addEventListener("submit", async (e) => {
  e.preventDefault(); // Предотвращаем перезагрузку страницы

  const data = {
    username: document.getElementById("register_username").value,
    full_name: document.getElementById("register_fullname").value,
    password: document.getElementById("register_password").value,
  };

  try {
    const response = await fetch("http://localhost:8000/register/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (response.ok) {
      alert("Регистрация прошла успешно. Теперь войдите в систему.");
    } else {
      const result = await response.json();
      alert("Ошибка регистрации: " + result.detail);
    }
  } catch (error) {
    console.error("Ошибка регистрации:", error);
  }
});

// Вход
document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault(); // Предотвращаем перезагрузку страницы

  const formData = new URLSearchParams();
  formData.append("username", document.getElementById("login_username").value);
  formData.append("password", document.getElementById("login_password").value);

  try {
    const response = await fetch("http://localhost:8000/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    });

    if (response.ok) {
      const result = await response.json();
      accessToken = result.access_token;
      alert("Вход выполнен успешно!");
      document.getElementById("predictionSection").style.display = "block";
    } else {
      alert("Ошибка входа: Неверное имя пользователя или пароль.");
    }
  } catch (error) {
    console.error("Ошибка входа:", error);
  }
});

// Предсказание
document.getElementById("predictionForm").addEventListener("submit", async (e) => {
  e.preventDefault(); // Предотвращаем перезагрузку страницы

  const formData = new FormData(e.target);
  const data = Object.fromEntries(formData.entries());

  try {
    const response = await fetch("http://localhost:8000/predict/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify([data]),
    });

    if (response.ok) {
      const result = await response.json();
      document.getElementById("result").innerText = JSON.stringify(result.predictions, null, 2);
    } else {
      alert("Ошибка при выполнении предсказания");
    }
  } catch (error) {
    console.error("Ошибка предсказания:", error);
  }
});
