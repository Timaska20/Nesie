document.addEventListener("DOMContentLoaded", function () {
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get("user_id");

    if (!userId) {
        alert("Ошибка: пользователь не найден!");
        window.location.href = "/admin.html";
        return;
    }

    loadUserDetails(userId);

    document.getElementById("makeAdminButton").addEventListener("click", function () {
        makeUserAdmin(userId);
    });

    document.getElementById("deleteUserButton").addEventListener("click", function () {
        deleteUser(userId);
    });
});

async function loadUserDetails(userId) {
    const token = localStorage.getItem("access_token");

    try {
        const response = await fetch(`/api/admin/users/`, {
            method: "GET",
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!response.ok) {
            throw new Error("Ошибка загрузки пользователя");
        }

        const users = await response.json();
        const user = users.find(u => u.id == userId);

        if (!user) {
            alert("Пользователь не найден!");
            window.location.href = "/admin.html";
            return;
        }

        document.getElementById("userId").textContent = user.id;
        document.getElementById("username").textContent = user.username;
        document.getElementById("userRole").textContent = user.is_admin ? "Администратор" : "Пользователь";

    } catch (error) {
        console.error("❌ Ошибка получения данных о пользователе:", error);
    }
}

async function deleteUser(userId) {
    if (!confirm("Вы уверены, что хотите удалить пользователя?")) return;

    const token = localStorage.getItem("access_token");

    try {
        const response = await fetch(`/api/admin/users/${userId}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (response.ok) {
            alert("Пользователь удалён");
            window.location.href = "/admin.html";
        } else {
            const errorData = await response.json();
            alert("Ошибка: " + errorData.detail);
        }
    } catch (error) {
        console.error("❌ Ошибка при удалении пользователя:", error);
    }
}

async function makeUserAdmin(userId) {
    if (!confirm("Вы уверены, что хотите сделать пользователя администратором?")) return;

    const token = localStorage.getItem("access_token");

    try {
        const response = await fetch(`/api/admin/users/${userId}/make_admin`, {
            method: "PUT",
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (response.ok) {
            alert("Пользователь теперь администратор");
            window.location.reload();
        } else {
            const errorData = await response.json();
            alert("Ошибка: " + errorData.detail);
        }
    } catch (error) {
        console.error("❌ Ошибка при изменении прав пользователя:", error);
    }
}
