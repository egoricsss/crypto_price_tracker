import asyncio
from typing import Dict, Optional

from app.clients.deribit import DeribitClient
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import Database
from app.db.repository import PriceRepository
from app.services.price_service import PriceService
from app.workers.celery_app import celery_app

logger = get_logger(__name__)

# Глобальный экземпляр БД (конфигурация, не состояние)
database = Database(
    database_url=settings.db.database_url_sync,
    echo=settings.app.debug,
)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def fetch_prices_task(self) -> Dict[str, Optional[float]]:
    """
    Периодическая задача для сбора цен криптовалют с биржи Deribit.
    
    Запускается каждую минуту через Celery Beat.
    
    Логика:
    1. Создаёт асинхронную сессию БД
    2. Создаёт клиент Deribit и сервис
    3. Получает цены BTC и ETH
    4. Сохраняет в PostgreSQL
    
    Returns:
        Словарь с ценами: {'BTC_USD': 45000.5, 'ETH_USD': 3200.1}
        
    Raises:
        Celery Retry: При ошибке пытается повторить до 3 раз с задержкой.
    """
    logger.info("Starting fetch_prices_task")
    
    try:
        # Запускаем асинхронный код внутри синхронной задачи Celery
        result = asyncio.run(_fetch_prices_async())
        logger.info(f"fetch_prices_task completed successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"fetch_prices_task failed: {e}", exc_info=True)
        
        # Экспоненциальная задержка перед повтором (60s, 120s, 240s)
        retry_delay = 60 * (2 ** self.request.retries)
        
        # Пробрасываем исключение для retry
        raise self.retry(
            exc=e,
            countdown=retry_delay,
            max_retries=3,
        )


async def _fetch_prices_async() -> Dict[str, Optional[float]]:
    """
    Асинхронная обёртка для бизнес-логики.
    
    Выделяется в отдельную функцию для корректной работы с asyncio.run().
    """
    # Создаём сессию БД
    database.create_session_maker()
    
    async with database._session_maker() as session:
        # Создаём клиент Deribit
        client = DeribitClient(
            base_url=settings.deribit.base_url,
            timeout=settings.deribit.request_timeout,
        )
        
        # Создаём репозиторий и сервис
        repository = PriceRepository(session=session)
        service = PriceService(
            deribit_client=client,
            repository=repository,
        )
        
        try:
            # Выполняем бизнес-логику
            result = await service.fetch_and_save_prices()
            return result
        finally:
            # Закрываем клиент после использования
            await client.close()