import json
import asyncio
import logging
import websockets
from decimal import Decimal
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async

from crypto_stream.models import CryptoPair, PriceUpdate

logger = logging.getLogger(__name__)


class BinanceWebsocketClient:
    """Клиент для взаимодействия с Binance WebSocket API"""

    def __init__(self):
        self.base_url = settings.BINANCE_WEBSOCKET_URI
        self.pairs = settings.CRYPTO_PAIRS
        self.websocket = None
        self.is_running = False
        self.last_save_time = timezone.now()
        self.channel_layer = get_channel_layer()
        self.price_buffer = {}  # Буфер для хранения цен перед записью в БД

    async def connect(self):
        """Подключение к WebSocket API Binance"""
        # Формируем URL для подключения к нескольким стримам
        streams = "/".join([f"{pair}@trade" for pair in self.pairs])
        websocket_url = f"{self.base_url}/{streams}"

        try:
            self.websocket = await websockets.connect(websocket_url)
            self.is_running = True
            logger.info(f"Connected to Binance WebSocket API: {websocket_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Binance WebSocket: {e}")
            return False

    async def disconnect(self):
        """Отключение от WebSocket API"""
        if self.websocket:
            await self.websocket.close()
            self.is_running = False
            logger.info("Disconnected from Binance WebSocket API")

    @sync_to_async
    def get_or_create_pair(self, symbol):
        """Получение или создание объекта пары криптовалют"""
        pair, created = CryptoPair.objects.get_or_create(symbol=symbol)
        return pair

    @sync_to_async
    def save_price_updates(self):
        """Сохранение накопленных обновлений цен в базу данных"""
        updates_to_create = []

        for symbol, data in self.price_buffer.items():
            try:
                pair = CryptoPair.objects.get(symbol=symbol)

                for update_data in data:
                    updates_to_create.append(PriceUpdate(
                        pair=pair,
                        price=update_data['price'],
                        timestamp=update_data['timestamp'],
                        trade_id=update_data.get('trade_id'),
                        quantity=update_data.get('quantity'),
                        buyer_order_id=update_data.get('buyer_order_id'),
                        seller_order_id=update_data.get('seller_order_id'),
                        is_buyer_maker=update_data.get('is_buyer_maker', False)
                    ))

            except CryptoPair.DoesNotExist:
                logger.error(f"Crypto pair {symbol} does not exist")

        if updates_to_create:
            PriceUpdate.objects.bulk_create(updates_to_create)
            logger.info(f"Saved {len(updates_to_create)} price updates to database")

        # Очищаем буфер после сохранения
        self.price_buffer = {}
        self.last_save_time = timezone.now()

    async def process_message(self, message):
        """Обработка сообщения, полученного от Binance"""
        try:
            data = json.loads(message)

            # Проверяем, что сообщение содержит информацию о сделке
            if 'e' in data and data['e'] == 'trade':
                symbol = data['s'].lower()  # Символ пары в нижнем регистре
                price = Decimal(data['p'])  # Цена
                trade_time = datetime.fromtimestamp(data['T'] / 1000, tz=timezone.utc)  # Время сделки

                # Дополнительные данные
                trade_id = data['t']
                quantity = Decimal(data['q'])
                buyer_order_id = data['b']
                seller_order_id = data['a']
                is_buyer_maker = data['m']

                # Добавляем данные в буфер
                if symbol not in self.price_buffer:
                    self.price_buffer[symbol] = []

                self.price_buffer[symbol].append({
                    'price': price,
                    'timestamp': trade_time,
                    'trade_id': trade_id,
                    'quantity': quantity,
                    'buyer_order_id': buyer_order_id,
                    'seller_order_id': seller_order_id,
                    'is_buyer_maker': is_buyer_maker
                })

                # Отправляем обновление клиентам через WebSocket
                await self.channel_layer.group_send(
                    f"crypto_{symbol}",
                    {
                        "type": "send_price_update",
                        "symbol": symbol,
                        "price": str(price),
                        "timestamp": trade_time.isoformat(),
                        "trade_id": trade_id,
                        "quantity": str(quantity)
                    }
                )

                # Проверяем, нужно ли сохранить данные в БД
                time_since_last_save = (timezone.now() - self.last_save_time).total_seconds()
                if time_since_last_save >= settings.DATA_SAVE_INTERVAL:
                    await self.save_price_updates()

        except json.JSONDecodeError:
            logger.error(f"Failed to parse message: {message}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def initialize_pairs(self):
        """Инициализация пар криптовалют в базе данных"""
        for pair in self.pairs:
            await self.get_or_create_pair(pair)
        logger.info(f"Initialized {len(self.pairs)} crypto pairs")

    async def listen(self):
        """Основной метод для прослушивания WebSocket"""
        if not self.websocket:
            connected = await self.connect()
            if not connected:
                return

        # Инициализируем пары в базе данных
        await self.initialize_pairs()

        try:
            while self.is_running:
                try:
                    message = await self.websocket.recv()
                    await self.process_message(message)
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed, reconnecting...")
                    await asyncio.sleep(5)
                    await self.connect()
        finally:
            # Сохраняем все оставшиеся данные перед выходом
            if self.price_buffer:
                await self.save_price_updates()
            await self.disconnect()

    async def start(self):
        """Запуск клиента Binance WebSocket"""
        self.is_running = True
        await self.listen()

    async def stop(self):
        """Остановка клиента"""
        self.is_running = False
        await self.disconnect()