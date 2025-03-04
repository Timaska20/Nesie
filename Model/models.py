from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

# Настройка подключения к базе данных PostgreSQL
DATABASE_URL = "postgresql://user:password@db:5432/mydb"

# Базовый класс для создания моделей
Base = declarative_base()

# Создание подключения к базе данных
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Модель пользователя
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)  # Новый столбец для админа

    # Отношение с кредитами
    credits = relationship("Credit", back_populates="user")

# Модель кредита
class Credit(Base):
    __tablename__ = 'credits'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # Сделали user_id обязательным
    loan_amount = Column(Float, nullable=False)  # Сумма кредита
    interest_rate = Column(Float, nullable=False)  # Процентная ставка
    term_months = Column(Integer, nullable=False)  # Срок в месяцах
    status = Column(String, nullable=False)  # Статус кредита (активный, погашен и т.д.)

    # Новые поля для кредитной истории
    person_age = Column(Integer, nullable=False)  # Возраст
    person_income = Column(Float, nullable=False)  # Доход
    person_home_ownership = Column(String, nullable=False)  # Владение жильем
    person_emp_length = Column(Integer, nullable=False)  # Стаж работы
    loan_intent = Column(String, nullable=False)  # Цель кредита
    loan_grade = Column(String, nullable=False)  # Класс кредита
    loan_percent_income = Column(Float, nullable=False)  # Процент дохода на кредит
    cb_person_default_on_file = Column(Boolean, nullable=False)  # Наличие дефолта
    cb_person_cred_hist_length = Column(Integer, nullable=False)  # Длина кредитной истории

    # Отношение с пользователем
    user = relationship("User", back_populates="credits")

# Функция для создания таблиц в базе данных
def init_db():
    print("Создание таблиц...")
    Base.metadata.create_all(bind=engine)
    print("Таблицы успешно созданы!")

if __name__ == "__main__":
    init_db()
