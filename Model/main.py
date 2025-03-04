from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

from models import SessionLocal, User, Credit

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
@app.post("/register/", response_model=UserCreate)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = get_user_by_username(db, user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/token/", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Неверное имя пользователя или пароль")
    access_token = create_access_token(data={"sub": user.username, "is_admin": user.is_admin})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/userinfo/")
def get_user_info(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    user = get_user_by_username(db, username)

    if not user:
        raise HTTPException(status_code=401, detail="Неавторизованный доступ")

    return {"username": user.username, "is_admin": user.is_admin}


@app.post("/admin/credits/")
def add_credit_history(credit_data: CreditCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    user = get_user_by_username(db, username)
    if user is None or user.username != "admin":
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


@app.get("/admin/credits/")
def get_all_credits(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    is_admin = payload.get("is_admin", False)  # Получаем флаг админа
    user = get_user_by_username(db, username)
    if user is None or not is_admin:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    return db.query(Credit).all()


# Запуск сервера
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
