import json
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal
from django.utils import timezone
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async

from crypto_stream.services.binance_client import BinanceWebsocketClient
from crypto_stream.models import CryptoPair, PriceUpdate


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_initialize_pairs():
    """Тест инициализации пар криптовалют"""
    client = BinanceWebsocketClient()
    client.pairs = ['btcusdt', 'ethusdt']

    await client.initialize_pairs()

    # Проверяем, что пары были созданы в БД
    pairs = await sync_to_async(list)(CryptoPair.objects.all())
    assert len(pairs) == 2
    assert pairs[0].symbol in client.pairs
    assert pairs[1].symbol in client.pairs


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_process_message():
    """Тест обработки сообщения от Binance"""
    # Создаем тестовое сообщение
    test_message = json.dumps({
        "e": "trade",
        "s": "BTCUSDT",
        "p": "50000.00",
        "q": "0.01",
        "T": int(timezone.now().timestamp() * 1000),
        "t": 12345,
        "b": 98765,
        "a": 54321,
        "m": True
    })

    # Создаем экземпляр клиента
    client = BinanceWebsocketClient()
    client.channel_layer = get_channel_layer()

    # Создаем пару в БД
    pair = await sync_to_async(CryptoPair.objects.create)(symbol='btcusdt')

    # Мокаем метод group_send
    with patch.object(client.channel_layer, 'group_send', new=AsyncMock()) as mock_group_send:
        # Обрабатываем сообщение
        await client.process_message(test_message)

        # Проверяем, что сообщение было отправлено в группу
        mock_group_send.assert_called_once()
        args, kwargs = mock_group_send.call_args
        assert args[0] == 'crypto_btcusdt'

        # Проверяем, что данные были добавлены в буфер
        assert 'btcusdt' in client.price_buffer
        assert len(client.price_buffer['btcusdt']) == 1
        assert client.price_buffer['btcusdt'][0]['price'] == Decimal('50000.00')


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_save_price_updates():
    """Тест сохранения обновлений цен в БД"""
    # Создаем экземпляр клиента
    client = BinanceWebsocketClient()

    # Создаем пару в БД
    pair = await sync_to_async(CryptoPair.objects.create)(symbol='btcusdt')

    # Заполняем буфер тестовыми данными
    test_time = timezone.now()
    client.price_buffer = {
        'btcusdt': [
            {
                'price': Decimal('50000.00'),
                'timestamp': test_time,
                'trade_id': 12345,
                'quantity': Decimal('0.01'),
                'buyer_order_id': 98765,
                'seller_order_id': 54321,
                'is_buyer_maker': True
            },
            {
                'price': Decimal('50100.00'),
                'timestamp': test_time + timezone.timedelta(seconds=5),
                'trade_id': 12346,
                'quantity': Decimal('0.02'),
                'buyer_order_id': 98766,
                'seller_order_id': 54322,
                'is_buyer_maker': False
            }
        ]
    }

    # Сохраняем данные
    await client.save_price_updates()

    # Проверяем, что данные были сохранены в БД
    updates = await sync_to_async(list)(PriceUpdate.objects.all())
    assert len(updates) == 2
    assert updates[0].price in [Decimal('50000.00'), Decimal('50100.00')]
    assert updates[1].price in [Decimal('50000.00'), Decimal('50100.00')]

    # Проверяем, что буфер был очищен
    assert client.price_buffer == {}


@pytest.mark.asyncio
async def test_connect():
    """Тест подключения к WebSocket API Binance"""
    client = BinanceWebsocketClient()
    client.pairs = ['btcusdt']

    # Мокаем websockets.connect
    with patch('websockets.connect', new=AsyncMock()) as mock_connect:
        mock_connect.return_value = AsyncMock()

        # Вызываем метод connect
        result = await client.connect()

        # Проверяем, что подключение было успешным
        assert result is True
        assert client.is_running is True

        # Проверяем, что websockets.connect был вызван с правильным URL
        mock_connect.assert_called_once()
        args, kwargs = mock_connect.call_args
        assert args[0] == 'wss://stream.binance.com:9443/ws/btcusdt@trade'