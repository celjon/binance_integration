from django.contrib import admin
from .models import CryptoPair, PriceUpdate


@admin.register(CryptoPair)
class CryptoPairAdmin(admin.ModelAdmin):
    """Админ-панель для модели CryptoPair"""
    list_display = ('symbol', 'created_at')
    search_fields = ('symbol',)


@admin.register(PriceUpdate)
class PriceUpdateAdmin(admin.ModelAdmin):
    """Админ-панель для модели PriceUpdate"""
    list_display = ('pair', 'price', 'timestamp', 'trade_id')
    list_filter = ('pair', 'timestamp')
    search_fields = ('pair__symbol', 'trade_id')
    date_hierarchy = 'timestamp'