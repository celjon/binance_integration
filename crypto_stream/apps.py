import os
import asyncio
import threading
from django.apps import AppConfig
from django.conf import settings


class CryptoStreamConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crypto_stream'

    def ready(self):
        # Проверяем, что это не вызвано командой migrate или другими командами Django
        if os.environ.get('RUN_MAIN', None) != 'true':
            return

        # Импортируем здесь, чтобы избежать циклических импортов
        from .services import BinanceWebsocketClient

        # Создаем и запускаем клиент в отдельном потоке
        def start_binance_client():
            # Создаем новый цикл событий для потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Создаем и запускаем клиент
            client = BinanceWebsocketClient()
            try:
                loop.run_until_complete(client.start())
            except Exception as e:
                print(f"Error starting Binance client: {e}")
            finally:
                loop.close()

        # Запускаем клиент в отдельном потоке, если это не тест
        if not settings.DEBUG or os.environ.get('DJANGO_SETTINGS_MODULE') == 'config.settings':
            client_thread = threading.Thread(target=start_binance_client)
            client_thread.daemon = True  # Поток завершится при завершении основного потока
            client_thread.start()