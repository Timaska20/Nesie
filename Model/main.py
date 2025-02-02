from flask import Flask, request, jsonify
from pycaret.classification import load_model, predict_model
import pandas as pd

# Инициализация Flask
app = Flask(__name__)

# Загрузка модели PyCaret
pipeline = load_model('my_pipeline')

# Маршрут для предсказания
@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Получение данных из запроса
        input_data = request.json

        # Преобразование данных в DataFrame
        new_data = pd.DataFrame(input_data)

        # Выполнение предсказаний
        predictions = predict_model(pipeline, data=new_data)

        # Форматирование результатов
        result = predictions[['person_age', 'person_income', 'prediction_label', 'prediction_score']].to_dict(orient='records')

        return jsonify({'status': 'success', 'predictions': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

# Запуск сервера
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
