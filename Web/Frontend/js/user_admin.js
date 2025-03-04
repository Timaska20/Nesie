document.addEventListener("DOMContentLoaded", function () {
    const addCreditForm = document.getElementById("addCreditForm");
    const autoFillButton = document.getElementById("autoFillButton");

    // Получаем ID пользователя из URL
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get("user_id");

    if (userId) {
        document.getElementById("user_id").value = userId;
    } else {
        console.error("Ошибка: user_id не найден в URL!");
    }

    // Проверяем токен перед отправкой
    const token = localStorage.getItem("access_token");
    if (!token) {
        console.error("Ошибка: Токен не найден в localStorage!");
    }

    addCreditForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        // Собираем данные формы
        const formData = new FormData(this);
        let creditData = {};

        formData.forEach((value, key) => {
            if (key === "cb_person_default_on_file") {
                creditData[key] = value === "on"; // Преобразование чекбокса в true/false
            } else {
                if (["loan_amount", "interest_rate", "person_income", "loan_percent_income"].includes(key)) {
                    creditData[key] = parseFloat(value);
                } else if (["term_months", "person_age", "person_emp_length", "cb_person_cred_hist_length"].includes(key)) {
                    creditData[key] = parseInt(value);
                } else {
                    creditData[key] = value;
                }
            }
        });

        creditData["user_id"] = parseInt(userId); // Устанавливаем user_id

        console.log("Отправляемые данные:", creditData);

        try {
            const response = await fetch("/api/admin/credits/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(creditData)
            });

            const data = await response.json();
            console.log("Ответ сервера:", data);

            if (!response.ok) {
                throw new Error(`Ошибка при добавлении кредита: ${data.detail || response.statusText}`);
            }

            alert("Кредит успешно добавлен!");
            location.reload();
        } catch (error) {
            console.error("Ошибка:", error);
            alert(error.message);
        }
    });

    // Обработчик для кнопки "Автозаполнение"
    autoFillButton.addEventListener("click", async function () {
        const loanStatus = Math.random() > 0.5 ? 1 : 0; // Случайный выбор между 0 и 1

        try {
            const response = await fetch(`/api/sample_credit/${loanStatus}`, {
                method: "GET",
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error("Ошибка при получении данных");
            }

            const sampleCredit = await response.json();
            console.log("Полученные данные для автозаполнения:", sampleCredit);

            // Заполняем форму
            document.getElementById("loan_amount").value = sampleCredit.loan_amnt;
            document.getElementById("interest_rate").value = sampleCredit.loan_int_rate;
            document.getElementById("term_months").value = sampleCredit.term_months;
            document.getElementById("status").value = loanStatus
            document.getElementById("person_age").value = sampleCredit.person_age;
            document.getElementById("person_income").value = sampleCredit.person_income;
            document.getElementById("person_home_ownership").value = sampleCredit.person_home_ownership || "Собственное";
            document.getElementById("person_emp_length").value = sampleCredit.person_emp_length || 5;
            document.getElementById("loan_intent").value = sampleCredit.loan_intent || "Образование";
            document.getElementById("loan_grade").value = sampleCredit.loan_grade || "A";
            document.getElementById("loan_percent_income").value = sampleCredit.loan_percent_income;
            document.getElementById("cb_person_default_on_file").checked = sampleCredit.cb_person_default_on_file;
            document.getElementById("cb_person_cred_hist_length").value = sampleCredit.cb_person_cred_hist_length;

            alert("Форма заполнена автоматически!");
        } catch (error) {
            console.error("Ошибка:", error);
            alert("Ошибка при автозаполнении!");
        }
    });
});
