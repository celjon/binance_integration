from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Создание роутера для API
router = DefaultRouter()
router.register(r'pairs', views.CryptoPairViewSet)
router.register(r'history', views.PriceHistoryViewSet, basename='price-history')

urlpatterns = [
    path('', include(router.urls)),
]