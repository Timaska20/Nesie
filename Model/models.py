from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

# Настройка подключения к базе данных PostgreSQL
DATABASE_URL = "postgresql://user:password@db:5432/mydb"

# Базовый класс для создания моделей
Base = declarative_base()

# Создание подключения к базе данных
engine = create_engine(DATABASE_URL, echo=True)  # echo=True для отладки
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#Курсы валют
class ExchangeRate(Base):
    __tablename__ = 'exchange_rates'
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True, nullable=False)
    usd = Column(Float, nullable=False)
    eur = Column(Float, nullable=False)
    rub = Column(Float, nullable=False)
    kzt = Column(Float, nullable=False)

# Модель пользователя
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    email = Column(String, nullable=True)
    email_confirmed = Column(Boolean, default=False)

    personal_data = relationship(
        "PersonalData",
        back_populates="user",
        cascade="all, delete",
        uselist=False
    )

    credits = relationship("Credit", back_populates="user")

class PersonalData(Base):
    __tablename__ = 'personal_data'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)

    person_age = Column(Integer, nullable=False)
    person_income = Column(Float, nullable=False)
    person_home_ownership = Column(String, nullable=False)
    person_emp_length = Column(Integer, nullable=False)

    user = relationship("User", back_populates="personal_data")

# Модель кредита
class Credit(Base):
    __tablename__ = "credits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    loan_amount = Column(Float)
    interest_rate = Column(Float)
    term_months = Column(Integer)
    status = Column(String, default="на рассмотрении")
    hash = Column(String, unique=True, index=True, nullable=False)

    user = relationship("User", back_populates="credits")

# Функция для создания таблиц в базе данных
def init_db():
    print("Пересоздание таблиц...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Таблицы успешно пересозданы!")

if __name__ == "__main__":
    init_db()
