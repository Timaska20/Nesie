document.addEventListener("DOMContentLoaded", async function () {
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get("id") || urlParams.get("user_id"); // подстраховка
    const token = localStorage.getItem("access_token");

    const headers = {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
    };

    if (!token) {
        alert("Вы не авторизованы!");
        window.location.href = "/index.html";
        return;
    }

    if (!userId) {
        alert("user_id не найден в URL");
        return;
    }

    document.getElementById("user_id").value = userId;

    // --- Загрузка и отображение информации о пользователе ---
    try {
        const res = await fetch("/api/admin/users/", { headers });
        const users = await res.json();
        const user = users.find(u => u.id == userId);

        if (!user) {
            alert("Пользователь не найден");
            return;
        }

        document.getElementById("userId").textContent = user.id;
        document.getElementById("username").textContent = user.username;
        document.getElementById("userRole").textContent = user.is_admin ? "Админ" : "Пользователь";

        if (user.is_admin) {
            document.getElementById("makeAdminButton").style.display = "none";
        }
    } catch (err) {
        console.error("Ошибка при загрузке пользователя:", err);
    }

    // --- Назначение админом ---
    document.getElementById("makeAdminButton").addEventListener("click", async () => {
        try {
            const res = await fetch(`/api/admin/users/${userId}/make_admin`, {
                method: "PUT",
                headers
            });
            const data = await res.json();

            if (!res.ok) throw new Error(data.detail || "Ошибка назначения");

            alert(data.message);
            location.reload();
        } catch (err) {
            alert("Ошибка: " + err.message);
        }
    });

    // --- Удаление пользователя ---
    document.getElementById("deleteUserButton").addEventListener("click", async () => {
        if (!confirm("Удалить пользователя?")) return;

        try {
            const res = await fetch(`/api/admin/users/${userId}`, {
                method: "DELETE",
                headers
            });
            const data = await res.json();

            if (!res.ok) throw new Error(data.detail || "Ошибка удаления");

            alert(data.message);
            window.location.href = "/admin.html";
        } catch (err) {
            alert("Ошибка: " + err.message);
        }
    });

    // --- Загрузка кредитов пользователя ---
    try {
        const res = await fetch(`/api/admin/credits/${userId}`, { headers });
        const credits = await res.json();

        const tableBody = document.querySelector("#creditsTable tbody");
        const noCreditsMessage = document.getElementById("noCreditsMessage");

        if (credits.length === 0) {
            noCreditsMessage.style.display = "block";
        } else {
            credits.forEach(credit => {
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>${credit.id}</td>
                    <td>${credit.loan_amount}</td>
                    <td>${credit.interest_rate}</td>
                    <td>${credit.term_months}</td>
                    <td>${credit.status}</td>
                    <td>${credit.person_income}</td>
                    <td>${credit.person_age}</td>
                    <td><button class="deleteCreditButton" data-id="${credit.id}">Удалить</button></td>
                `;
                tableBody.appendChild(row);
            });

            document.querySelectorAll(".deleteCreditButton").forEach(button => {
                button.addEventListener("click", async () => {
                    const creditId = button.dataset.id;
                    if (!confirm("Удалить кредит?")) return;

                    try {
                        const res = await fetch(`/api/admin/credits/${creditId}`, {
                            method: "DELETE",
                            headers
                        });
                        const data = await res.json();
                        if (!res.ok) throw new Error(data.detail || "Ошибка удаления кредита");

                        alert(data.message);
                        location.reload();
                    } catch (err) {
                        alert("Ошибка: " + err.message);
                    }
                });
            });
        }
    } catch (err) {
        console.error("Ошибка при загрузке кредитов:", err);
    }

    // --- Автозаполнение формы ---
    const autoFillButton = document.getElementById("autoFillButton");
    autoFillButton.addEventListener("click", async () => {
        const loanStatus = Math.random() > 0.5 ? 1 : 0;

        try {
            const res = await fetch(`/api/sample_credit/${loanStatus}`, { headers });
            const data = await res.json();

            if (!res.ok) throw new Error("Не удалось получить пример кредита");

            document.getElementById("loan_amount").value = data.loan_amnt;
            document.getElementById("interest_rate").value = data.loan_int_rate;
            document.getElementById("term_months").value = data.term_months;
            document.getElementById("status").value = loanStatus === 1 ? "активный" : "не выдан";
            document.getElementById("person_age").value = data.person_age;
            document.getElementById("person_income").value = data.person_income;
            document.getElementById("person_home_ownership").value = data.person_home_ownership || "Собственное";
            document.getElementById("person_emp_length").value = data.person_emp_length || 5;
            document.getElementById("loan_intent").value = data.loan_intent || "Образование";
            document.getElementById("loan_grade").value = data.loan_grade || "A";
            document.getElementById("loan_percent_income").value = data.loan_percent_income;
            document.getElementById("cb_person_default_on_file").checked = data.cb_person_default_on_file;
            document.getElementById("cb_person_cred_hist_length").value = data.cb_person_cred_hist_length;

            alert("Форма заполнена!");
        } catch (err) {
            console.error("Ошибка при автозаполнении:", err);
            alert("Ошибка автозаполнения");
        }
    });

    // --- Обработка формы добавления кредита ---
    document.getElementById("addCreditForm").addEventListener("submit", async function (event) {
        event.preventDefault();

        const formData = new FormData(this);
        let creditData = {};

        formData.forEach((value, key) => {
            if (key === "cb_person_default_on_file") {
                creditData[key] = document.getElementById("cb_person_default_on_file").checked;
            } else if (["loan_amount", "interest_rate", "person_income", "loan_percent_income"].includes(key)) {
                creditData[key] = parseFloat(value);
            } else if (["term_months", "person_age", "person_emp_length", "cb_person_cred_hist_length"].includes(key)) {
                creditData[key] = parseInt(value);
            } else {
                creditData[key] = value;
            }
        });

        creditData["user_id"] = parseInt(userId);

        try {
            const res = await fetch("/api/admin/credits/", {
                method: "POST",
                headers,
                body: JSON.stringify(creditData)
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || "Ошибка добавления кредита");
            }

            alert("Кредит успешно добавлен!");
            location.reload();
        } catch (err) {
            console.error("Ошибка:", err);
            alert(err.message);
        }
    });
});
