from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

# Настройка подключения к базе данных PostgreSQL
# Изменили имя базы данных с dbname на mydb, согласно docker-compose.yml
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

    # Отношение с кредитами
    credits = relationship("Credit", back_populates="user")

# Модель кредита
class Credit(Base):
    __tablename__ = 'credits'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    loan_amount = Column(Float, nullable=False)  # Сумма кредита
    interest_rate = Column(Float, nullable=False)  # Процентная ставка
    term_months = Column(Integer, nullable=False)  # Срок в месяцах
    status = Column(String, nullable=False)  # Статус кредита (активный, погашен и т.д.)

    # Отношение с пользователем
    user = relationship("User", back_populates="credits")
