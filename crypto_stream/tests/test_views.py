import json
import pytest
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from crypto_stream.models import CryptoPair, PriceUpdate


class CryptoPairViewSetTests(APITestCase):
    """Тесты для CryptoPairViewSet"""

    def setUp(self):
        """Настройка тестового окружения"""
        # Создаем тестовые пары
        self.pair1 = CryptoPair.objects.create(symbol='btcusdt')
        self.pair2 = CryptoPair.objects.create(symbol='ethusdt')

        # Создаем тестовые обновления цен
        self.update1 = PriceUpdate.objects.create(
            pair=self.pair1,
            price=Decimal('50000.00'),
            timestamp=timezone.now(),
            trade_id=12345,
            quantity=Decimal('0.01')
        )

        self.update2 = PriceUpdate.objects.create(
            pair=self.pair2,
            price=Decimal('3000.00'),
            timestamp=timezone.now(),
            trade_id=12346,
            quantity=Decimal('0.1')
        )

    def test_list_pairs(self):
        """Тест получения списка пар"""
        url = reverse('cryptopair-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['symbol'], self.pair1.symbol)
        self.assertEqual(response.data[1]['symbol'], self.pair2.symbol)

    def test_retrieve_pair(self):
        """Тест получения конкретной пары"""
        url = reverse('cryptopair-detail', args=[self.pair1.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['symbol'], self.pair1.symbol)

    def test_latest_price(self):
        """Тест получения последней цены для пары"""
        url = reverse('cryptopair-latest-price', args=[self.pair1.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['symbol'], self.pair1.symbol)
        self.assertEqual(response.data['price'], '50000.00')
        self.assertEqual(response.data['trade_id'], 12345)


class PriceHistoryViewSetTests(APITestCase):
    """Тесты для PriceHistoryViewSet"""

    def setUp(self):
        """Настройка тестового окружения"""
        # Создаем тестовую пару
        self.pair = CryptoPair.objects.create(symbol='btcusdt')

        # Создаем несколько тестовых обновлений цены
        now = timezone.now()
        for i in range(10):
            PriceUpdate.objects.create(
                pair=self.pair,
                price=Decimal(f'5000{i}.00'),
                timestamp=now - timezone.timedelta(minutes=i),
                trade_id=12345 + i,
                quantity=Decimal('0.01')
            )

    def test_retrieve_history(self):
        """Тест получения истории цен для пары"""
        url = reverse('price-history-detail', args=['btcusdt'])
        response = self.client.get(url, {'limit': 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)

        # Проверяем, что история отсортирована по убыванию времени
        timestamps = [item['timestamp'] for item in response.data]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))

    def test_summary(self):
        """Тест получения сводки по всем парам"""
        # Создаем дополнительную пару с обновлениями цен
        pair2 = CryptoPair.objects.create(symbol='ethusdt')
        now = timezone.now()

        # Текущая цена
        PriceUpdate.objects.create(
            pair=pair2,
            price=Decimal('3000.00'),
            timestamp=now,
            trade_id=23456,
            quantity=Decimal('0.1')
        )

        # Цена 24 часа назад
        PriceUpdate.objects.create(
            pair=pair2,
            price=Decimal('2900.00'),
            timestamp=now - timezone.timedelta(days=1, minutes=5),
            trade_id=23455,
            quantity=Decimal('0.1')
        )

        # Создаем старую цену для btcusdt (24 часа назад)
        PriceUpdate.objects.create(
            pair=self.pair,
            price=Decimal('48000.00'),
            timestamp=now - timezone.timedelta(days=1, minutes=5),
            trade_id=12335,
            quantity=Decimal('0.01')
        )

        url = reverse('price-history-summary')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Проверяем данные для пар
        btc_data = next(item for item in response.data if item['symbol'] == 'btcusdt')
        eth_data = next(item for item in response.data if item['symbol'] == 'ethusdt')

        self.assertEqual(btc_data['current_price'], '50009.00')  # Последняя цена из setup
        self.assertIsNotNone(btc_data['price_change_24h'])
        self.assertIsNotNone(btc_data['price_change_percent_24h'])

        self.assertEqual(eth_data['current_price'], '3000.00')
        self.assertEqual(eth_data['price_change_24h'], '100.00')  # 3000 - 2900
        self.assertEqual(eth_data['price_change_percent_24h'], 3.45)  # (100 / 2900) * 100