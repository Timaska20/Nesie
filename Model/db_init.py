from sqlalchemy import create_engine, Column, String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, relationship
from passlib.context import CryptContext
from main import Base, User, DATABASE_URL
from datetime import datetime

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Создание подключения к базе данных
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Модель для хранения данных по кредиту с привязкой к пользователю
class CreditData(Base):
    __tablename__ = "credit_data"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.username"), nullable=False)
    person_age = Column(Integer, nullable=False)
    person_income = Column(Float, nullable=False)
    person_home_ownership = Column(String, nullable=False)
    person_emp_length = Column(Float, nullable=True)
    loan_intent = Column(String, nullable=False)
    loan_grade = Column(String, nullable=False)
    loan_amnt = Column(Float, nullable=False)
    loan_int_rate = Column(Float, nullable=True)
    loan_percent_income = Column(Float, nullable=False)
    cb_person_default_on_file = Column(String, nullable=False)
    cb_person_cred_hist_length = Column(Integer, nullable=False)
    request_date = Column(DateTime, default=datetime.utcnow)  # Дата запроса

    # Установка связи с пользователем
    user = relationship("User", back_populates="credits")


# Добавляем связь в модель User
User.credits = relationship("CreditData", back_populates="user", cascade="all, delete")


# Функция для создания таблиц в базе данных
def create_tables():
    Base.metadata.create_all(bind=engine)


# Функция для добавления пользователя в базу данных
def create_user(db, username: str, full_name: str, password: str, disabled: bool = False):
    hashed_password = pwd_context.hash(password)
    user = User(
        username=username,
        full_name=full_name,
        hashed_password=hashed_password,
        disabled=disabled
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# Функция для добавления данных по кредиту
def add_credit_data(db, user_id, credit_data):
    new_credit_data = CreditData(user_id=user_id, **credit_data)
    db.add(new_credit_data)
    db.commit()
    db.refresh(new_credit_data)
    return new_credit_data


# Инициализация базы данных и добавление тестового пользователя
if __name__ == "__main__":
    create_tables()
    db = SessionLocal()
    existing_user = db.query(User).filter(User.username == "testuser").first()
    if not existing_user:
        create_user(db, "testuser", "Test User", "password123")
        print("Тестовый пользователь создан.")
    else:
        print("Пользователь уже существует.")
    db.close()
авторизацию