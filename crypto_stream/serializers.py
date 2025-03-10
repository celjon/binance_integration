from rest_framework import serializers
from .models import CryptoPair, PriceUpdate


class CryptoPairSerializer(serializers.ModelSerializer):
    """Сериализатор для модели CryptoPair"""

    class Meta:
        model = CryptoPair
        fields = ['id', 'symbol', 'created_at']


class PriceUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для модели PriceUpdate"""
    symbol = serializers.CharField(source='pair.symbol', read_only=True)

    class Meta:
        model = PriceUpdate
        fields = [
            'id', 'symbol', 'price', 'timestamp',
            'trade_id', 'quantity', 'buyer_order_id',
            'seller_order_id', 'is_buyer_maker'
        ]


class PriceHistorySerializer(serializers.Serializer):
    """Сериализатор для запроса истории цен"""
    symbol = serializers.CharField(required=True)
    start_time = serializers.DateTimeField(required=False)
    end_time = serializers.DateTimeField(required=False)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=1000, default=100)