FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Порт для Django
EXPOSE 8000

# Запуск приложения
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]