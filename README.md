# Интеграция Django с WebSocket API Binance

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Django](https://img.shields.io/badge/Django-4.2-green)
![Channels](https://img.shields.io/badge/Django_Channels-4.0-brightgreen)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14-orange)
![Redis](https://img.shields.io/badge/Redis-7-red)

Django-приложение с интеграцией WebSocket API Binance для отслеживания цен криптовалют в реальном времени, сохранения данных в PostgreSQL и трансляции обновлений клиентам через WebSocket.

## 🚀 Возможности

- **Интеграция с Binance API**: Подключение к WebSocket API Binance для получения данных о торгах в реальном времени
- **Хранение данных**: Сохранение обновлений цен в базе данных PostgreSQL с оптимизированной схемой
- **REST API**: Полноценный API для доступа к историческим данным с возможностями фильтрации
- **WebSocket трансляция**: Передача обновлений клиентам в реальном времени с использованием Django Channels
- **Масштабируемая архитектура**: Использование Redis для слоев каналов с поддержкой масштабирования
- **Полный набор тестов**: Модульные тесты для всех компонентов системы

## 📋 Архитектура системы

```
                           ┌───────────────┐
                           │  Binance API  │
                           └───────┬───────┘
                                   │
                                   ▼
                           ┌───────────────┐
                           │Binance WebSocket│
                           │    Client     │
                           └───┬───────┬───┘
                               │       │
                 ┌─────────────┘       └─────────────┐
                 │                                   │
                 ▼                                   ▼
        ┌─────────────────┐                  ┌──────────────┐
        │   PostgreSQL    │                  │Django Channels│
        │    Database     │                  │Channel Layer  │
        └────────┬────────┘                  └───────┬──────┘
                 │                                   │
        ┌────────┘                                   └────────┐
        │                                                     │
        ▼                                                     ▼
┌───────────────┐                                   ┌──────────────────┐
│    REST API   │                                   │WebSocket Consumers│
└───────┬───────┘                                   └─────────┬────────┘
        │                                                     │
        └─────────────┐                             ┌─────────┘
                      │                             │
                      ▼                             ▼
               ┌─────────────────────────────────────────┐
               │              Web Clients                │
               └─────────────────────────────────────────┘
```

Приложение следует модульной архитектуре:

1. **Клиент Binance WebSocket**: Подключается к API Binance и обрабатывает получение данных
2. **Django Models**: Определяют схему базы данных для пар криптовалют и обновлений цен
3. **Django Channels Consumers**: Управляют WebSocket-соединениями с клиентами
4. **REST API ViewSets**: Предоставляют доступ к историческим данным

## ⚙️ Установка

### Использование Docker (рекомендуется)

```bash
# Клонирование репозитория
git clone https://github.com/celjon/binance_integration.git
cd binance_integration

# Запуск контейнеров
docker-compose up -d

# Применение миграций
docker-compose exec web python manage.py migrate
```

### Ручная установка

```bash
# Клонирование репозитория
git clone https://github.com/celjon/binance_integration.git
cd binance_integration

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка PostgreSQL и Redis
# (Настройте config/settings.py с вашими данными подключения)

# Применение миграций
python manage.py migrate

# Запуск сервера
python manage.py runserver
```

## 🔌 API Эндпоинты

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/api/pairs/` | GET | Список всех пар криптовалют |
| `/api/pairs/{id}/` | GET | Получение информации о конкретной паре |
| `/api/pairs/{id}/latest_price/` | GET | Получение последней цены для пары |
| `/api/history/{symbol}/` | GET | Получение истории цен для пары |
| `/api/history/summary/` | GET | Получение сводки по всем парам |

### Параметры запроса для истории цен

- `start_time`: Фильтр по времени начала (формат ISO)
- `end_time`: Фильтр по времени окончания (формат ISO)
- `limit`: Максимальное количество записей для возврата (по умолчанию: 100)

## 📡 WebSocket-соединения

Подключитесь к WebSocket-эндпоинту для получения обновлений в реальном времени:

```javascript
// Пример кода клиента
const socket = new WebSocket('ws://localhost:8000/ws/crypto/btcusdt/');

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log(`${data.symbol}: ${data.price}`);
};

// Запрос исторических данных
socket.send(JSON.stringify({
    type: 'history',
    limit: 50
}));
```

## 🧪 Тестирование

Запустите тесты, чтобы убедиться, что всё работает правильно:

```bash
# Через Docker
docker-compose exec web pytest

# Вручную
pytest
```

## 🔧 Конфигурация

Основные настройки можно изменить в файле `config/settings.py`:

- `CRYPTO_PAIRS`: Список пар криптовалют для отслеживания
- `DATA_SAVE_INTERVAL`: Интервал в секундах для сохранения данных в базу
- `BINANCE_WEBSOCKET_URI`: WebSocket URI для API Binance

## 📊 Планы по улучшению

- Реализация аутентификации пользователей для доступа к API
- Добавление панели визуализации данных
- Поддержка большего количества криптовалютных бирж
- Реализация системы оповещений для пороговых значений цен
- Добавление агрегации данных для различных временных интервалов