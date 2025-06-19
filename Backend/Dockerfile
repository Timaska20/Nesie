# Используем официальный образ Python
FROM python:3.10-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY . .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Открываем порт для FastAPI
EXPOSE 8000

# Запуск скрипта инициализации и сервера FastAPI
CMD ["bash", "-c", "python db_init.py && uvicorn main:app --host 0.0.0.0 --port 8000"]
