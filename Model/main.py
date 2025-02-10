from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pycaret.classification import load_model, predict_model
import pandas as pd
from typing import Optional
import catboost
import numpy as np

app = FastAPI()

# Загрузка модели
pipeline = load_model('my_pipeline')

# Определение структуры входных данных с примерами для Swagger
class InputData(BaseModel):
    person_age: int = Field(..., example=25)
    person_income: float = Field(..., example=66000)
    person_home_ownership: str = Field(..., example="MORTGAGE")
    person_emp_length: Optional[float] = Field(None, example=4.0)
    loan_intent: str = Field(..., example="HOMEIMPROVEMENT")
    loan_grade: str = Field(..., example="C")
    loan_amnt: float = Field(..., example=15000)
    loan_int_rate: Optional[float] = Field(None, example=14.35)
    loan_percent_income: float = Field(..., example=0.23)
    cb_person_default_on_file: str = Field(..., example="N")
    cb_person_cred_hist_length: int = Field(..., example=4)

@app.post("/predict/")
def predict(data: list[InputData]):
    try:
        # Преобразование данных в DataFrame
        new_data = pd.DataFrame([item.dict() for item in data])

        # Обработка пропусков
        new_data['person_emp_length'].fillna(new_data['person_emp_length'].mean(), inplace=True)
        new_data['loan_int_rate'].fillna(new_data['loan_int_rate'].mean(), inplace=True)

        # Вычисление дополнительных признаков
        new_data['loan_to_income_ratio'] = new_data['loan_amnt'] / new_data['person_income']
        new_data['loan_to_emp_length_ratio'] = new_data['loan_amnt'] / (new_data['person_emp_length'] + 1)
        new_data['int_rate_to_loan_amt_ratio'] = new_data['loan_int_rate'] / new_data['loan_amnt']
        new_data['adjusted_age'] = np.log1p(new_data['person_age'])

        # Выполнение предсказания
        predictions = predict_model(pipeline, data=new_data)

        # Форматирование результатов
        result = predictions[['person_age', 'person_income', 'prediction_label', 'prediction_score']].to_dict(orient='records')

        return {"status": "success", "predictions": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
