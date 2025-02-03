# Первый этап: Сборка зависимостей
FROM python:3.9-slim AS builder

WORKDIR /app

# Установка необходимых библиотек и зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas-dev liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Установка Python-зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Второй этап: Минимизированный финальный контейнер
FROM python:3.9-alpine

WORKDIR /app

# Копируем только необходимые файлы из builder-образа
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копирование основного кода приложения
COPY main.py .
COPY my_pipeline.pkl .

# Открытие порта для Flask
EXPOSE 5000

# Команда для запуска приложения
CMD ["python", "main.py"]
