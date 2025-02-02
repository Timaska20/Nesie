# Базовый образ Python
FROM python:3.9-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование необходимых файлов
COPY main.py .
COPY my_pipeline.pkl .
COPY requirements.txt .

# Установка Python-зависимостей
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Открытие порта для Flask
EXPOSE 5000

# Команда для запуска приложения
CMD ["python", "main.py"]
