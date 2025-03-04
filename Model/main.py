from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

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
    loan_amount: float
    interest_rate: float
    term_months: int
    status: str


# Утилиты для работы с пользователями
def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


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

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/credits/")
def create_credit(credit: CreditCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user = get_user_by_username(db, username)
        if user is None:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        new_credit = Credit(
            user_id=user.id,
            loan_amount=credit.loan_amount,
            interest_rate=credit.interest_rate,
            term_months=credit.term_months,
            status=credit.status
        )
        db.add(new_credit)
        db.commit()
        db.refresh(new_credit)
        return new_credit
    except JWTError:
        raise HTTPException(status_code=403, detail="Недействительный токен")


@app.get("/credits/")
def read_credits(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user = get_user_by_username(db, username)
        if user is None:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        credits = db.query(Credit).filter(Credit.user_id == user.id).all()
        return credits
    except JWTError:
        raise HTTPException(status_code=403, detail="Недействительный токен")


# Запуск сервера
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
