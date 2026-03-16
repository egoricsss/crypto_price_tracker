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
    database_url=settings.db.database_url,
    echo=settings.app.debug,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_prices_task(self) -> Dict[str, Optional[float]]:
    task_id = self.request.id
    logger.info(
        f"Task started | task_id={task_id} | attempt={self.request.retries + 1}"
    )

    try:
        result = asyncio.run(_fetch_prices_async())

        success_count = sum(1 for v in result.values() if v is not None)
        logger.info(
            f"Task completed | task_id={task_id} | "
            f"success={success_count}/{len(result)} | "
            f"results={result}"
        )
        return result

    except Exception as e:
        logger.error(f"Task failed | task_id={task_id} | error={e}", exc_info=True)
        raise self.retry(exc=e, countdown=60 * (2**self.request.retries))


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
