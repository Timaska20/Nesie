from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from pycaret.classification import load_model, predict_model
from sqlalchemy import create_engine, Column, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Optional, List

# Настройки подключения к базе данных
DATABASE_URL = "postgresql+psycopg2://user:password@db:5432/mydb"

# Подключение к базе данных
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Конфигурация JWT
SECRET_KEY = "super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Настройка OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Определение модели пользователя
class User(Base):
    __tablename__ = "users"
    username = Column(String, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    disabled = Column(Boolean, default=False)


# Создание таблиц
Base.metadata.create_all(bind=engine)

# Создание экземпляра FastAPI
app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Подключение к базе данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Утилиты для аутентификации
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str):
    return pwd_context.hash(password)


def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Модель для регистрации пользователя
class UserCreate(BaseModel):
    username: str
    full_name: str
    password: str


# Регистрация пользователя
@app.post("/register/")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user(db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")

    hashed_password = hash_password(user.password)
    new_user = User(
        username=user.username,
        full_name=user.full_name,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "Пользователь успешно зарегистрирован"}


# Аутентификация пользователя и выдача токена
@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Неверное имя пользователя или пароль")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# Загрузка модели
pipeline = load_model('my_pipeline')


# Модель для входных данных предсказания
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


# Маршрут для предсказания
@app.post("/predict/")
def predict(data: List[InputData], token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=403, detail="Недопустимый токен")

        new_data = pd.DataFrame([item.dict() for item in data])
        new_data['person_emp_length'].fillna(new_data['person_emp_length'].mean(), inplace=True)
        new_data['loan_int_rate'].fillna(new_data['loan_int_rate'].mean(), inplace=True)

        # Добавление новых признаков
        new_data['loan_to_income_ratio'] = new_data['loan_amnt'] / new_data['person_income']
        new_data['loan_to_emp_length_ratio'] = new_data['loan_amnt'] / (new_data['person_emp_length'] + 1)
        new_data['int_rate_to_loan_amt_ratio'] = new_data['loan_int_rate'] / new_data['loan_amnt']
        new_data['adjusted_age'] = np.log1p(new_data['person_age'])

        predictions = predict_model(pipeline, data=new_data)
        result = predictions[['person_age', 'person_income', 'prediction_label', 'prediction_score']].to_dict(
            orient='records'
        )

        return {"status": "success", "predictions": result}
    except JWTError:
        raise HTTPException(status_code=403, detail="Ошибка аутентификации")
