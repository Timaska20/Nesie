document.addEventListener("DOMContentLoaded", async () => {
  const userPanel = document.getElementById("userPanel");
  const adminPanel = document.getElementById("adminPanel");
  const usernameDisplay = document.getElementById("usernameDisplay");
  const logoutButton = document.getElementById("logoutButton");
  const predictButton = document.getElementById("predictButton");
  const predictResult = document.getElementById("predictResult");

  function saveToken(token) {
    localStorage.setItem("access_token", token);
  }

  function getToken() {
    return localStorage.getItem("access_token");
  }

  async function getUserInfo() {
    const token = getToken();
    if (!token || !token.includes(".")) {
      console.warn("Некорректный или отсутствующий токен");
      return null;
    }

    try {
      const response = await fetch("/api/userinfo/", {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error("Ошибка авторизации");
      }

      return await response.json();
    } catch (error) {
      console.error("Ошибка получения информации о пользователе:", error);
      return null;
    }
  }

  async function displayUserPanel() {
    const user = await getUserInfo();
    if (!user) return;

    usernameDisplay.textContent = user.username;
    if (userPanel) userPanel.style.display = "block";
    if (user.is_admin && adminPanel) adminPanel.style.display = "block";
  }

  if (logoutButton) {
    logoutButton.addEventListener("click", () => {
      localStorage.removeItem("access_token");
      window.location.href = "index.html";
    });
  }

  if (predictButton && predictResult) {
    predictButton.addEventListener("click", async () => {
      const token = getToken();
      const user = await getUserInfo();

      if (!user || !user.user_id) {
        predictResult.textContent = "Ошибка: пользователь не найден";
        predictResult.style.color = "gray";
        return;
      }

      predictResult.textContent = "Обработка запроса...";
      predictResult.style.color = "black";

      try {
        const res = await fetch(`/api/predict/${user.user_id}`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`
          }
        });

        const data = await res.json();

        if (data.prediction && data.prediction.prediction_label === 1) {
          predictResult.textContent = "Кредит одобрен ✅";
          predictResult.style.color = "green";
        } else {
          predictResult.textContent = "Кредит не одобрен ❌";
          predictResult.style.color = "red";
        }
      } catch (err) {
        console.error("Ошибка при получении предсказания:", err);
        predictResult.textContent = "Ошибка при получении предсказания";
        predictResult.style.color = "gray";
      }
    });
  }

  // Запуск при загрузке
  displayUserPanel();
});
