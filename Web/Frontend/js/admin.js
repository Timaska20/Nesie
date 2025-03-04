document.addEventListener("DOMContentLoaded", function () {
    async function loadUsers() {
        const token = localStorage.getItem("access_token");
        if (!token) {
            console.error("❌ Нет токена");
            return;
        }

        try {
            const response = await fetch("api/admin/users/", {
                method: "GET",
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (!response.ok) {
                throw new Error("Ошибка загрузки пользователей");
            }

            const users = await response.json();
            const tableBody = document.querySelector("#usersTable tbody");

            // Очищаем таблицу перед добавлением новых данных
            tableBody.innerHTML = "";

            users.forEach(user => {
                const row = document.createElement("tr");

                row.innerHTML = `
                    <td>${user.id}</td>
                    <td>${user.username}</td>
                    <td>${user.is_admin ? "Администратор" : "Пользователь"}</td>
                    <td><button class="gotoUserBtn" data-id="${user.id}">Перейти</button></td>
                `;

                tableBody.appendChild(row);
            });

            // Назначаем обработчики клика для кнопок "Перейти"
            document.querySelectorAll(".gotoUserBtn").forEach(button => {
                button.addEventListener("click", function () {
                    const userId = this.getAttribute("data-id");
                    window.location.href = `/user_admin.html?user_id=${userId}`;
                });
            });

        } catch (error) {
            console.error("❌ Ошибка получения пользователей:", error);
        }
    }

    if (document.querySelector("#usersTable")) {
        loadUsers();
    }
});
