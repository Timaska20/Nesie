from models import Base, engine, SessionLocal, User
from sqlalchemy.orm import Session
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Функция для хеширования пароля
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Функция для создания таблиц в базе данных
def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Таблицы успешно созданы!")

# Функция для добавления администратора
def create_admin():
    session = SessionLocal()
    admin = session.query(User).filter_by(username="admin").first()

    if not admin:
        hashed_password = hash_password("admin")
        admin = admin = User(
            username="admin",
            password=hashed_password,
            is_admin=True,
            email="admin@example.com",
            email_confirmed=True
        )
        session.add(admin)
        session.commit()
        print("Администратор успешно создан!")
    else:
        print("Администратор уже существует!")

    session.close()

# Запуск скрипта
if __name__ == "__main__":
    create_tables()
    create_admin()
