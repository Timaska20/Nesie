from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

from models import SessionLocal, User, Credit

import pandas as pd
import random
from pycaret.classification import load_model, predict_model
import numpy as np

csv_path = "credit_risk_dataset.csv"
# Загружаем модель один раз при старте
model = load_model("my_pipeline")  # замените на актуальное имя вашей модели
df = pd.read_csv(csv_path)

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


# Эндпоинты
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

# Запуск сервера
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
