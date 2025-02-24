document.getElementById('predictionForm').addEventListener('submit', function(event) {
  event.preventDefault();

  // Получаем значения из формы
  const person_age = parseFloat(document.getElementById('person_age').value);
  const person_income = parseFloat(document.getElementById('person_income').value);
  const person_home_ownership = document.getElementById('person_home_ownership').value;
  const person_emp_length_value = document.getElementById('person_emp_length').value;
  const person_emp_length = person_emp_length_value ? parseFloat(person_emp_length_value) : 0;
  const loan_intent = document.getElementById('loan_intent').value;
  const loan_grade = document.getElementById('loan_grade').value;
  const loan_amnt = parseFloat(document.getElementById('loan_amnt').value);
  const loan_int_rate_value = document.getElementById('loan_int_rate').value;
  const loan_int_rate = loan_int_rate_value ? parseFloat(loan_int_rate_value) : 0;
  const cb_person_default_on_file = document.getElementById('cb_person_default_on_file').value;
  const cb_person_cred_hist_length = parseFloat(document.getElementById('cb_person_cred_hist_length').value);

  // Вычисляем поле "Доля кредита от дохода" с округлением до двух знаков
  const loan_percent_income = Number((loan_amnt / person_income).toFixed(2));

  // Формируем объект данных, передаваемый на сервер
  const formData = {
    person_age,
    person_income,
    person_home_ownership,
    person_emp_length,
    loan_intent,
    loan_grade,
    loan_amnt,
    loan_int_rate,
    loan_percent_income,  // рассчитываемое поле
    cb_person_default_on_file,
    cb_person_cred_hist_length
  };

  // Отправляем данные на сервер по указанному адресу
  fetch('http://localhost:8000/predict/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify([formData])
  })
  .then(response => response.json())
  .then(data => {
    const resultDiv = document.getElementById('result');
    if (data.status === "success") {
      let html = '<h3>Результаты предсказания:</h3>';
      data.predictions.forEach(item => {
        // Если prediction_label равен 0, значит платежеспособность - "ДА", иначе "НЕТ"
        const paymentAbility = item.prediction_label === 0 ? "ДА" : "НЕТ";
        html += `<p>Возраст: ${item.person_age}, Доход: ${item.person_income}, Платежеспособность: ${paymentAbility}, Балл: ${item.prediction_score.toFixed(2)}</p>`;
      });
      resultDiv.innerHTML = html;
    } else {
      resultDiv.innerHTML = `<p>Ошибка: ${data.detail}</p>`;
    }
  })
  .catch(error => {
    document.getElementById('result').innerHTML = `<p>Произошла ошибка: ${error}</p>`;
  });
});
