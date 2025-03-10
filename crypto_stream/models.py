from django.db import models
from django.utils import timezone


class CryptoPair(models.Model):
    """Модель для хранения информации о паре криптовалют"""
    symbol = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.symbol


class PriceUpdate(models.Model):
    """Модель для хранения обновлений цен"""
    pair = models.ForeignKey(CryptoPair, on_delete=models.CASCADE, related_name='price_updates')
    price = models.DecimalField(max_digits=20, decimal_places=8)
    timestamp = models.DateTimeField(default=timezone.now)
    trade_id = models.BigIntegerField(blank=True, null=True)
    quantity = models.DecimalField(max_digits=30, decimal_places=8, blank=True, null=True)
    buyer_order_id = models.BigIntegerField(blank=True, null=True)
    seller_order_id = models.BigIntegerField(blank=True, null=True)
    is_buyer_maker = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['pair', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.pair.symbol} - {self.price} - {self.timestamp}"