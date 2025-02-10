FROM python:3.9-slim

WORKDIR /app

# Устанавливаем все необходимые зависимости и добавляем инструменты для работы с репозиториями
RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-utils \
    software-properties-common \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libgomp1 \
    libc-dev \
    libpq-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Удаление ненужных пакетов для уменьшения размера образа
RUN apt-get purge -y --auto-remove build-essential gcc g++ libc-dev

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
