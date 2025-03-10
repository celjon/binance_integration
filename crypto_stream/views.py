from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from datetime import timedelta

from .models import CryptoPair, PriceUpdate
from .serializers import CryptoPairSerializer, PriceUpdateSerializer, PriceHistorySerializer


class CryptoPairViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для просмотра информации о парах криптовалют"""
    queryset = CryptoPair.objects.all()
    serializer_class = CryptoPairSerializer

    @action(detail=True, methods=['get'])
    def latest_price(self, request, pk=None):
        """Получение последней цены для пары криптовалют"""
        pair = self.get_object()
        latest_price = PriceUpdate.objects.filter(pair=pair).order_by('-timestamp').first()

        if latest_price:
            serializer = PriceUpdateSerializer(latest_price)
            return Response(serializer.data)
        else:
            return Response(
                {"detail": "No price data available for this pair."},
                status=status.HTTP_404_NOT_FOUND
            )


class PriceHistoryViewSet(viewsets.ViewSet):
    """ViewSet для получения истории цен"""

    def list(self, request):
        """Получение списка всех доступных пар криптовалют"""
        pairs = CryptoPair.objects.all()
        serializer = CryptoPairSerializer(pairs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Получение истории цен для конкретной пары"""
        # Валидация параметров запроса
        request_serializer = PriceHistorySerializer(data={
            'symbol': pk,
            **request.query_params
        })

        if not request_serializer.is_valid():
            return Response(
                request_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Получение параметров запроса
        data = request_serializer.validated_data
        symbol = data['symbol'].lower()
        start_time = data.get('start_time', timezone.now() - timedelta(days=1))
        end_time = data.get('end_time', timezone.now())
        limit = data.get('limit', 100)

        # Получение пары криптовалют
        pair = get_object_or_404(CryptoPair, symbol=symbol)

        # Получение истории цен
        price_history = PriceUpdate.objects.filter(
            pair=pair,
            timestamp__gte=start_time,
            timestamp__lte=end_time
        ).order_by('-timestamp')[:limit]

        # Сериализация результатов
        serializer = PriceUpdateSerializer(price_history, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Получение сводки по всем парам криптовалют"""
        pairs = CryptoPair.objects.all()
        result = []

        for pair in pairs:
            latest = PriceUpdate.objects.filter(pair=pair).order_by('-timestamp').first()
            if latest:
                # Получение цены от 24 часов назад для расчета изменения
                day_ago = timezone.now() - timedelta(days=1)
                old_price = PriceUpdate.objects.filter(
                    pair=pair,
                    timestamp__lte=day_ago
                ).order_by('-timestamp').first()

                # Расчет изменения цены
                price_change = None
                price_change_percent = None

                if old_price:
                    price_change = latest.price - old_price.price
                    price_change_percent = (price_change / old_price.price) * 100

                result.append({
                    'symbol': pair.symbol,
                    'current_price': str(latest.price),
                    'last_update': latest.timestamp.isoformat(),
                    'price_change_24h': str(price_change) if price_change is not None else None,
                    'price_change_percent_24h': round(price_change_percent,
                                                      2) if price_change_percent is not None else None
                })

        return Response(result)