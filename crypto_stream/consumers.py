import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import CryptoPair, PriceUpdate

logger = logging.getLogger(__name__)


class CryptoConsumer(AsyncWebsocketConsumer):
    """WebSocket потребитель для работы с данными криптовалют"""

    async def connect(self):
        """Обработка подключения клиента к WebSocket"""
        self.symbol = self.scope['url_route']['kwargs']['symbol'].lower()
        self.group_name = f"crypto_{self.symbol}"

        # Проверяем существование запрошенной пары
        if not await self.pair_exists(self.symbol):
            logger.warning(f"Client attempted to connect to non-existing pair: {self.symbol}")
            await self.close()
            return

        # Добавляем клиента в группу
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"Client connected to WebSocket for {self.symbol}")

        # Отправляем последнее обновление цены клиенту
        latest_price = await self.get_latest_price(self.symbol)
        if latest_price:
            await self.send(text_data=json.dumps(latest_price))

    async def disconnect(self, close_code):
        """Обработка отключения клиента"""
        # Удаляем клиента из группы
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        logger.info(f"Client disconnected from WebSocket for {self.symbol}")

    async def receive(self, text_data):
        """Обработка сообщений от клиента"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            # Обработка запроса на получение истории цен
            if message_type == 'history':
                limit = data.get('limit', 50)  # Количество записей (по умолчанию 50)
                history = await self.get_price_history(self.symbol, limit)
                await self.send(text_data=json.dumps({
                    'type': 'history',
                    'data': history
                }))
        except json.JSONDecodeError:
            logger.error(f"Failed to parse message from client: {text_data}")
        except Exception as e:
            logger.error(f"Error processing message from client: {e}")

    @database_sync_to_async
    def pair_exists(self, symbol):
        """Проверка существования пары криптовалют"""
        return CryptoPair.objects.filter(symbol=symbol).exists()

    @database_sync_to_async
    def get_latest_price(self, symbol):
        """Получение последнего обновления цены для пары"""
        try:
            pair = CryptoPair.objects.get(symbol=symbol)
            latest = PriceUpdate.objects.filter(pair=pair).order_by('-timestamp').first()

            if latest:
                return {
                    'type': 'price_update',
                    'symbol': symbol,
                    'price': str(latest.price),
                    'timestamp': latest.timestamp.isoformat(),
                    'trade_id': latest.trade_id,
                    'quantity': str(latest.quantity) if latest.quantity else None
                }
            return None
        except CryptoPair.DoesNotExist:
            return None

    @database_sync_to_async
    def get_price_history(self, symbol, limit=50):
        """Получение истории цен для пары"""
        try:
            pair = CryptoPair.objects.get(symbol=symbol)
            history = PriceUpdate.objects.filter(pair=pair).order_by('-timestamp')[:limit]

            return [
                {
                    'price': str(update.price),
                    'timestamp': update.timestamp.isoformat(),
                    'trade_id': update.trade_id,
                    'quantity': str(update.quantity) if update.quantity else None
                }
                for update in history
            ]
        except CryptoPair.DoesNotExist:
            return []

    async def send_price_update(self, event):
        """Отправка обновления цены клиенту"""
        # Исключаем поле 'type', которое используется для маршрутизации события
        message = {k: v for k, v in event.items() if k != 'type'}
        message['type'] = 'price_update'

        # Отправка сообщения клиенту
        await self.send(text_data=json.dumps(message))