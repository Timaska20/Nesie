import os
import io
import base64
import random
from datetime import datetime, date, timedelta

import httpx
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import shap

from dotenv import load_dotenv
from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from fastapi import FastAPI, HTTPException, Depends, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse

from pycaret.classification import load_model, predict_model
from scipy.special import expit
import shap

from models import SessionLocal, User, PersonalData, Credit, ExchangeRate

csv_path = "credit_risk_dataset.csv"
# Загружаем модель один раз при старте
model = load_model("my_pipeline")  # замените на актуальное имя вашей модели
catboost_model = model.named_steps['trained_model']

df = pd.read_csv(csv_path)
OPEN_EXCHANGE_APP_ID = os.getenv("OPEN_EXCHANGE_APP_ID")

# Настройка FastAPI
app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настройка токенов и безопасности
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Подключение к базе данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic-схемы
class UserCreate(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class PersonalDataCreate(BaseModel):
    person_age: int
    person_income: float
    person_home_ownership: str
    person_emp_length: int


class CreditCreate(BaseModel):
    user_id: int
    loan_amount: float
    interest_rate: float
    term_months: int
    status: str
    person_age: int
    person_income: float
    person_home_ownership: str
    person_emp_length: int
    loan_intent: str
    loan_grade: str
    loan_percent_income: float
    cb_person_default_on_file: bool
    cb_person_cred_hist_length: int


# Утилиты для работы с пользователями
def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

class CreditExplanation(BaseModel):
    person_age: int
    person_income: float
    person_home_ownership: str
    person_emp_length: int
    loan_intent: str
    loan_grade: str
    loan_amnt: float
    loan_int_rate: float
    loan_percent_income: float
    cb_person_default_on_file: bool
    cb_person_cred_hist_length: int


# Эндпоинты

@app.get("/currency-rates/")
async def get_currency_rates(db: Session = Depends(get_db)):
    today = date.today()
    existing_rate = db.query(ExchangeRate).filter(ExchangeRate.date == today).first()

    if not existing_rate:
        if not OPEN_EXCHANGE_APP_ID:
            raise HTTPException(status_code=500, detail=f"Токен не найден {OPEN_EXCHANGE_APP_ID}")

        url = f"https://openexchangerates.org/api/latest.json?app_id={OPEN_EXCHANGE_APP_ID}&symbols=USD,RUB,EUR,KZT"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                data = response.json()

            rates = data.get("rates", {})
            usd_rate = rates.get("USD", 1)
            eur_rate = rates.get("EUR")
            rub_rate = rates.get("RUB")
            kzt_rate = rates.get("KZT")

            if not all([eur_rate, rub_rate, kzt_rate]):
                raise HTTPException(status_code=500, detail="Некорректные данные от API")

            new_rate = ExchangeRate(
                date=today,
                usd=usd_rate,
                eur=eur_rate,
                rub=rub_rate,
                kzt=kzt_rate
            )
            db.add(new_rate)
            db.commit()
            existing_rate = new_rate

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка при получении курса валют: {str(e)}")

    BUY_SPREAD = 0.005  # 0.5% комиссия на покупку
    SELL_SPREAD = 0.01  # 1% комиссия на продажу

    def calculate_rate(nominal):
        buy = round((existing_rate.kzt / nominal) * (1 - BUY_SPREAD), 2)
        sell = round((existing_rate.kzt / nominal) * (1 + SELL_SPREAD), 2)
        return {"buy": buy, "sell": sell}

    return {
        "eur": calculate_rate(existing_rate.eur),
        "rub": calculate_rate(existing_rate.rub),
        "usd": calculate_rate(existing_rate.usd)
    }

@app.post("/register/", response_model=Token)
def register_user(
        username: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db)
):
    existing_user = get_user_by_username(db, username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    hashed_password = get_password_hash(password)
    new_user = User(username=username, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    # Сразу создаем токен
    access_token = create_access_token(data={"sub": new_user.username, "is_admin": new_user.is_admin})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token/", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Неверное имя пользователя или пароль")
    access_token = create_access_token(data={"sub": user.username, "is_admin": user.is_admin})
    print({"sub": user.username, "is_admin": user.is_admin})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/userinfo/")
def get_user_info(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    user = get_user_by_username(db, username)

    if not user:
        raise HTTPException(status_code=401, detail="Неавторизованный доступ")

    return {
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin
    }

@app.get("/personal-data/")
def get_personal_data(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user = get_user_by_username(db, username)

        if not user:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        personal_data = db.query(PersonalData).filter(PersonalData.user_id == user.id).first()

        if not personal_data:
            raise HTTPException(status_code=404, detail=f"Персональные данные не найдены для {username} с ID {user.id}")

        return {
            "person_age": personal_data.person_age,
            "person_income": personal_data.person_income,
            "person_home_ownership": personal_data.person_home_ownership,
            "person_emp_length": personal_data.person_emp_length
        }
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Токен истек. Выполните повторный вход.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Ошибка аутентификации")

@app.post("/personal-data/")
def add_or_update_personal_data(
    personal_data: PersonalDataCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    # Получаем текущего пользователя по токену
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    user = get_user_by_username(db, username)

    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    # Проверяем, есть ли персональные данные для этого пользователя
    existing_data = db.query(PersonalData).filter(PersonalData.user_id == user.id).first()

    if existing_data:
        # Обновляем существующие данные
        existing_data.person_age = personal_data.person_age
        existing_data.person_income = personal_data.person_income
        existing_data.person_home_ownership = personal_data.person_home_ownership
        existing_data.person_emp_length = personal_data.person_emp_length
        db.commit()
        db.refresh(existing_data)
        return {"message": "Персональные данные обновлены", "data": {
            "person_age": existing_data.person_age,
            "person_income": existing_data.person_income,
            "person_home_ownership": existing_data.person_home_ownership,
            "person_emp_length": existing_data.person_emp_length
        }}
    else:
        # Добавляем новые данные
        new_data = PersonalData(
            user_id=user.id,
            person_age=personal_data.person_age,
            person_income=personal_data.person_income,
            person_home_ownership=personal_data.person_home_ownership,
            person_emp_length=personal_data.person_emp_length
        )
        db.add(new_data)
        db.commit()
        db.refresh(new_data)
        return {"message": "Персональные данные добавлены", "data": {
            "person_age": new_data.person_age,
            "person_income": new_data.person_income,
            "person_home_ownership": new_data.person_home_ownership,
            "person_emp_length": new_data.person_emp_length
        }}
@app.post("/admin/credits/")
def add_credit_history(credit_data: CreditCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    user = get_user_by_username(db, username)
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    new_credit = Credit(**credit_data.dict())
    db.add(new_credit)
    db.commit()
    db.refresh(new_credit)
    return new_credit

@app.get("/admin/users/")
def get_all_users(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    user = get_user_by_username(db, username)

    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    users = db.query(User).all()
    return [{"id": u.id, "username": u.username, "is_admin": u.is_admin} for u in users]


@app.delete("/admin/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    user = get_user_by_username(db, username)

    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    user_to_delete = db.query(User).filter(User.id == user_id).first()

    if not user_to_delete:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    db.delete(user_to_delete)
    db.commit()

    return {"message": "Пользователь удалён"}


@app.put("/admin/users/{user_id}/make_admin")
def make_user_admin(user_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    user = get_user_by_username(db, username)

    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    user_to_promote = db.query(User).filter(User.id == user_id).first()

    if not user_to_promote:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if user_to_promote.is_admin:
        raise HTTPException(status_code=400, detail="Пользователь уже является администратором")

    user_to_promote.is_admin = True
    db.commit()

    return {"message": "Пользователь теперь администратор"}

# TODO Настроить видимость для админа и пользывателей
@app.get("/admin/credits/{user_id}")
def get_user_credits(user_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    return db.query(Credit).filter(Credit.user_id == user_id).all()

@app.put("/admin/credits/{credit_id}")
def update_credit(credit_id: int, updated_data: CreditCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credit = db.query(Credit).filter(Credit.id == credit_id).first()
    for key, value in updated_data.dict().items():
        setattr(credit, key, value)
    db.commit()
    return credit

@app.delete("/admin/credits/{credit_id}")
def delete_credit(credit_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    db.query(Credit).filter(Credit.id == credit_id).delete()
    db.commit()
    return {"message": "Кредит удалён"}


df["loan_status"] = pd.to_numeric(df["loan_status"], errors="coerce")


@app.post("/find-credits/")
def find_similar_credits(
        personal_data: PersonalDataCreate,
        db: Session = Depends(get_db),
        token: str = Depends(oauth2_scheme),
        filter_type: str = Query("ALL", regex="^(ALL|BEST)$")
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Недопустимый токен")

        latest_rate = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).first()
        if not latest_rate:
            raise HTTPException(status_code=500, detail="Нет доступных курсов валют")

        usd_to_kzt = latest_rate.kzt
        monthly_income_kzt = personal_data.person_income
        annual_income_kzt = monthly_income_kzt * 12
        annual_income_usd = annual_income_kzt / usd_to_kzt

        filtered_df = df[
            (df['loan_status'] == 0) &
            (df['person_home_ownership'] == personal_data.person_home_ownership) &
            (df['person_emp_length'].notnull()) &
            (df['person_age'].between(personal_data.person_age - 5, personal_data.person_age + 5)) &
            (df['person_income'].between(annual_income_usd * 0.8, annual_income_usd))
            ]

        if filtered_df.empty:
            return {"message": "Не найдено похожих кредитов", "total_found": 0}

        credits_list = filtered_df.replace({np.nan: None, np.inf: None, -np.inf: None}).to_dict(orient='records')

        for credit in credits_list:
            try:
                if credit.get("person_income") is not None:
                    income_kzt_annual = credit["person_income"] * usd_to_kzt
                    credit["person_income_kzt_annual"] = round(income_kzt_annual, 2)
                    credit["person_income_kzt_monthly"] = round(income_kzt_annual / 12, 2)
                else:
                    credit["person_income_kzt_annual"] = None
                    credit["person_income_kzt_monthly"] = None

                if credit.get("loan_amnt") is not None:
                    credit["loan_amnt_kzt"] = round(credit["loan_amnt"] * usd_to_kzt, 2)

                else:
                    credit["loan_amnt_kzt"] = None

                model_input = pd.DataFrame([{
                    "person_age": personal_data.person_age,
                    "person_income": annual_income_usd,
                    "person_home_ownership": personal_data.person_home_ownership,
                    "person_emp_length": personal_data.person_emp_length,
                    "loan_intent": credit.get("loan_intent", "PERSONAL"),
                    "loan_grade": credit.get("loan_grade", "C"),
                    "loan_amnt": credit.get("loan_amnt", 5000),
                    "loan_int_rate": credit.get("loan_int_rate", 15.0),
                    "loan_percent_income": credit.get("loan_amnt", 5000)/annual_income_usd,
                    "cb_person_default_on_file": "N",
                    "cb_person_cred_hist_length": credit.get("cb_person_cred_hist_length",1)
                }])

                prediction = predict_model(model, data=model_input)
                result = prediction[["prediction_label", "prediction_score"]].iloc[0].to_dict()

                credit["client_prediction"] = {
                    "prediction_label": result["prediction_label"],
                    "prediction_score": round(result["prediction_score"], 4),
                    "client_person_age": personal_data.person_age,
                    "client_person_income_usd_annual": round(annual_income_usd, 2),
                    "client_person_income_kzt_annual": round(annual_income_usd*usd_to_kzt, 2),
                    "client_person_home_ownership": personal_data.person_home_ownership,
                    "client_person_emp_length": personal_data.person_emp_length
                }

            except Exception as e:
                credit["client_prediction"] = f"Ошибка прогноза: {str(e)}"

        if filter_type == "BEST":
            best_offers = []
            seen_intents = set()

            grouped = {}
            for credit in credits_list:
                pred = credit.get("client_prediction", {})
                if isinstance(pred, dict) and pred.get("prediction_label") == 0.0 and pred.get("prediction_score",
                                                                                               0) > 0.8:
                    intent = credit.get("loan_intent")
                    if intent not in grouped:
                        grouped[intent] = []
                    grouped[intent].append(credit)

            for intent, offers in grouped.items():
                best = max(offers, key=lambda x: (
                    x.get("loan_amnt_kzt", 0),
                    -(x.get("loan_int_rate") if x.get("loan_int_rate") is not None else 1000)
                ))
                best_offers.append(best)

            credits_list = best_offers

        return {
            "client_income_tenge_month": monthly_income_kzt,
            "client_income_tenge_annual": annual_income_kzt,
            "client_income_usd_annual": round(annual_income_usd, 2),
            "total_found": len(credits_list),
            "credits": credits_list
        }

    except JWTError:
        raise HTTPException(status_code=403, detail="Ошибка аутентификации")

@app.get("/sample_credit/{loan_status}")
def get_sample_credit(loan_status: int):
    if loan_status not in [0, 1]:
        raise HTTPException(status_code=400, detail="loan_status должен быть 0 или 1")

    filtered_df = df[df["loan_status"] == loan_status]
    if filtered_df.empty:
        raise HTTPException(status_code=404, detail="Нет данных с таким loan_status")

    sample = filtered_df.sample(1).iloc[0].to_dict()

    # Преобразуем в нужные форматы
    sample["loan_amnt"] = float(sample["loan_amnt"])
    sample["loan_int_rate"] = float(sample["loan_int_rate"])
    sample["term_months"] = 36  # Стандартный срок
    sample["person_income"] = float(sample["person_income"])
    sample["person_age"] = int(sample["person_age"])

    return sample


@app.post("/predict/{user_id}")
def predict_for_user(user_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        # Проверка токена
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Недопустимый токен")

        # Получение последнего кредита по user_id
        credit = (
            db.query(Credit)
            .filter(Credit.user_id == user_id)
            .order_by(Credit.id.desc())
            .first()
        )

        if not credit:
            raise HTTPException(status_code=404, detail="Кредиты для пользователя не найдены")

        # Преобразуем объект в DataFrame
        credit_data = {
            "person_age": credit.person_age,
            "person_income": credit.person_income,
            "person_home_ownership": credit.person_home_ownership,
            "person_emp_length": credit.person_emp_length,
            "loan_intent": credit.loan_intent,
            "loan_grade": credit.loan_grade,
            "loan_amnt": credit.loan_amount,
            "loan_int_rate": credit.interest_rate,
            "loan_percent_income": credit.loan_percent_income,
            "cb_person_default_on_file": "Y" if credit.cb_person_default_on_file else "N",
            "cb_person_cred_hist_length": credit.cb_person_cred_hist_length,
        }

        df = pd.DataFrame([credit_data])

        # Признаки-инженерия
        df['loan_to_income_ratio'] = df['loan_amnt'] / df['person_income']
        df['loan_to_emp_length_ratio'] = df['loan_amnt'] / (df['person_emp_length'] + 1)
        df['int_rate_to_loan_amt_ratio'] = df['loan_int_rate'] / df['loan_amnt']
        df['adjusted_age'] = np.log1p(df['person_age'])

        # Предсказание
        prediction = predict_model(model, data=df)
        result = prediction[["prediction_label", "prediction_score"]].iloc[0].to_dict()

        return {
            "user_id": user_id,
            "credit_id": credit.id,
            "prediction": result
        }

    except JWTError:
        raise HTTPException(status_code=403, detail="Ошибка аутентификации")


@app.post("/explain")
def explain_from_input(credit_data: CreditExplanation, token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("sub"):
            raise HTTPException(status_code=403, detail="Недопустимый токен")

        loan_amnt = credit_data.loan_amnt

        raw_data = pd.DataFrame([{
            "person_age": credit_data.person_age,
            "person_income": credit_data.person_income,
            "person_home_ownership": credit_data.person_home_ownership,
            "person_emp_length": credit_data.person_emp_length,
            "loan_intent": credit_data.loan_intent,
            "loan_grade": credit_data.loan_grade,
            "loan_amnt": loan_amnt,
            "loan_int_rate": credit_data.loan_int_rate,
            "loan_percent_income": credit_data.loan_percent_income,
            "cb_person_default_on_file": "Y" if credit_data.cb_person_default_on_file else "N",
            "cb_person_cred_hist_length": credit_data.cb_person_cred_hist_length,
            "loan_to_income_ratio": loan_amnt / credit_data.person_income,
            "loan_to_emp_length_ratio": loan_amnt / (credit_data.person_emp_length + 1),
            "int_rate_to_loan_amt_ratio": credit_data.loan_int_rate / loan_amnt,
            "adjusted_age": np.log1p(credit_data.person_age)
        }])

        transformed = model.transform(raw_data)
        explainer = shap.TreeExplainer(catboost_model)
        shap_values = explainer.shap_values(transformed)

        explanation = dict(zip(transformed.columns, shap_values[0]))
        logit = explainer.expected_value + sum(shap_values[0])
        probability = round(float(expit(logit)), 4)
        label = int(probability >= 0.5)

        return {
            "prediction_logit": round(logit, 4),
            "prediction_probability": probability,
            "prediction_label": label,
            "shap_explanation": explanation
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка объяснения: {str(e)}")


@app.post("/explain/image")
def explain_image(credit_data: CreditExplanation, token: str = Depends(oauth2_scheme)):
    import shap
    import matplotlib.pyplot as plt
    import io
    import base64
    from fastapi.responses import JSONResponse

    FEATURE_TRANSLATIONS = {
        "person_age": "Возраст",
        "person_income": "Доход",
        "person_home_ownership_MORTGAGE": "Ипотека",
        "person_home_ownership_RENT": "Аренда",
        "person_home_ownership_OWN": "Собственное жильё",
        "person_home_ownership_OTHER": "Другое жильё",
        "person_emp_length": "Стаж работы",
        "loan_intent_HOMEIMPROVEMENT": "Ремонт жилья",
        "loan_intent_VENTURE": "Бизнес",
        "loan_intent_MEDICAL": "Медицина",
        "loan_intent_PERSONAL": "Личные нужды",
        "loan_intent_EDUCATION": "Образование",
        "loan_intent_DEBTCONSOLIDATION": "Погашение долгов",
        "loan_grade_A": "Класс A",
        "loan_grade_B": "Класс B",
        "loan_grade_C": "Класс C",
        "loan_grade_D": "Класс D",
        "loan_grade_E": "Класс E",
        "loan_grade_F": "Класс F",
        "loan_grade_G": "Класс G",
        "loan_amnt": "Сумма кредита",
        "loan_int_rate": "Процентная ставка",
        "loan_percent_income": "Доля от дохода",
        "cb_person_default_on_file": "Просрочка ранее",
        "cb_person_cred_hist_length": "Длина кредитной истории",
        "loan_to_income_ratio": "Кредит / Доход",
        "loan_to_emp_length_ratio": "Кредит / Стаж",
        "int_rate_to_loan_amt_ratio": "Ставка / Сумма",
        "adjusted_age": "Корректированный возраст"
    }

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("sub"):
            raise HTTPException(status_code=403, detail="Недопустимый токен")

        loan_amnt = credit_data.loan_amnt

        raw_data = pd.DataFrame([{
            "person_age": credit_data.person_age,
            "person_income": credit_data.person_income,
            "person_home_ownership": credit_data.person_home_ownership,
            "person_emp_length": credit_data.person_emp_length,
            "loan_intent": credit_data.loan_intent,
            "loan_grade": credit_data.loan_grade,
            "loan_amnt": loan_amnt,
            "loan_int_rate": credit_data.loan_int_rate,
            "loan_percent_income": credit_data.loan_percent_income,
            "cb_person_default_on_file": "Y" if credit_data.cb_person_default_on_file else "N",
            "cb_person_cred_hist_length": credit_data.cb_person_cred_hist_length,
            "loan_to_income_ratio": loan_amnt / credit_data.person_income,
            "loan_to_emp_length_ratio": loan_amnt / (credit_data.person_emp_length + 1),
            "int_rate_to_loan_amt_ratio": credit_data.loan_int_rate / loan_amnt,
            "adjusted_age": np.log1p(credit_data.person_age)
        }])

        transformed = model.transform(raw_data)
        explainer = shap.TreeExplainer(catboost_model)
        shap_values = explainer.shap_values(transformed)

        display_df = transformed.copy()
        display_df.columns = [FEATURE_TRANSLATIONS.get(col, col) for col in display_df.columns]

        plt.clf()
        shap.plots._waterfall.waterfall_legacy(
            explainer.expected_value, shap_values[0], display_df.iloc[0], show=False
        )

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        plt.close()
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()

        return JSONResponse(content={"image_base64": img_base64})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации изображения: {str(e)}")


# Запуск сервера
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
