import json
import pytest
from decimal import Decimal
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from django.test import TestCase
from django.urls import re_path
from django.utils import timezone

from crypto_stream.models import CryptoPair, PriceUpdate
from crypto_stream.consumers import CryptoConsumer


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_crypto_consumer_connect():
    """Тест подключения к WebSocket-потребителю"""
    # Создаем тестовую пару
    pair = await CryptoPair.objects.acreate(symbol='btcusdt')

    # Создаем тестовое обновление цены
    price_update = await PriceUpdate.objects.acreate(
        pair=pair,
        price=Decimal('50000.00'),
        timestamp=timezone.now(),
        trade_id=12345,
        quantity=Decimal('0.01')
    )

    # Создаем тестовый коммуникатор
    application = URLRouter([
        re_path(r'ws/crypto/(?P<symbol>\w+)/$', CryptoConsumer.as_asgi()),
    ])
    communicator = WebsocketCommunicator(application, "/ws/crypto/btcusdt/")

    # Подключаемся
    connected, _ = await communicator.connect()
    assert connected

    # Ожидаем сообщение с последней ценой
    response = await communicator.receive_json_from()
    assert response['symbol'] == 'btcusdt'
    assert response['price'] == '50000.00'
    assert 'timestamp' in response
    assert response['trade_id'] == 12345

    # Отключаемся
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_crypto_consumer_receive_history():
    """Тест получения истории цен через WebSocket"""
    # Создаем тестовую пару
    pair = await CryptoPair.objects.acreate(symbol='btcusdt')

    # Создаем несколько тестовых обновлений цены
    now = timezone.now()
    for i in range(10):
        await PriceUpdate.objects.acreate(
            pair=pair,
            price=Decimal(f'5000{i}.00'),
            timestamp=now - timezone.timedelta(minutes=i),
            trade_id=12345 + i,
            quantity=Decimal('0.01')
        )

    # Создаем тестовый коммуникатор
    application = URLRouter([
        re_path(r'ws/crypto/(?P<symbol>\w+)/$', CryptoConsumer.as_asgi()),
    ])
    communicator = WebsocketCommunicator(application, "/ws/crypto/btcusdt/")

    # Подключаемся
    connected, _ = await communicator.connect()
    assert connected

    # Пропускаем первое сообщение (последняя цена)
    await communicator.receive_json_from()

    # Отправляем запрос на получение истории
    await communicator.send_json_to({
        'type': 'history',
        'limit': 5
    })

    # Получаем ответ
    response = await communicator.receive_json_from()
    assert response['type'] == 'history'
    assert len(response['data']) == 5

    # Проверяем, что история отсортирована по убыванию времени
    timestamps = [item['timestamp'] for item in response['data']]
    assert timestamps == sorted(timestamps, reverse=True)

    # Отключаемся
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_crypto_consumer_send_price_update():
    """Тест отправки обновления цены через WebSocket"""
    # Создаем тестовую пару
    pair = await CryptoPair.objects.acreate(symbol='btcusdt')

    # Создаем тестовое обновление цены для инициализации
    await PriceUpdate.objects.acreate(
        pair=pair,
        price=Decimal('50000.00'),
        timestamp=timezone.now(),
        trade_id=12345,
        quantity=Decimal('0.01')
    )

    # Создаем тестовый коммуникатор
    application = URLRouter([
        re_path(r'ws/crypto/(?P<symbol>\w+)/$', CryptoConsumer.as_asgi()),
    ])
    communicator = WebsocketCommunicator(application, "/ws/crypto/btcusdt/")

    # Подключаемся
    connected, _ = await communicator.connect()
    assert connected

    # Пропускаем первое сообщение (последняя цена)
    await communicator.receive_json_from()

    # Отправляем сообщение в группу (как если бы оно пришло от Binance)
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        'crypto_btcusdt',
        {
            'type': 'send_price_update',
            'symbol': 'btcusdt',
            'price': '51000.00',
            'timestamp': timezone.now().isoformat(),
            'trade_id': 12346,
            'quantity': '0.02'
        }
    )

    # Получаем ответ
    response = await communicator.receive_json_from()
    assert response['type'] == 'price_update'
    assert response['symbol'] == 'btcusdt'
    assert response['price'] == '51000.00'
    assert 'timestamp' in response
    assert response['trade_id'] == 12346
    assert response['quantity'] == '0.02'

    # Отключаемся
    await communicator.disconnect()