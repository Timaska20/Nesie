from models import Base, engine

# Функция для создания таблиц в базе данных
def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Таблицы успешно созданы!")

# Запуск скрипта
if __name__ == "__main__":
    create_tables()
