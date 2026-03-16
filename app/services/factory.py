from typing import AsyncGenerator
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.deribit import DeribitClient
from app.core.config import settings
from app.db.repository import PriceRepository
from app.services.price_service import PriceService


@dataclass
class ServiceContainer:
    """
    Контейнер для управления зависимостями сервиса.
    Позволяет корректно освободить ресурсы (закрыть клиент) после использования.
    """

    service: PriceService
    client: DeribitClient


class ServiceFactory:
    """Фабрика для создания сервисов с правильными зависимостями."""

    @staticmethod
    def create_deribit_client() -> DeribitClient:
        """Создаёт клиент Deribit с настройками из config."""
        return DeribitClient(
            base_url=settings.deribit.base_url,
            timeout=settings.deribit.request_timeout,
        )

    @staticmethod
    def create_price_repository(session: AsyncSession) -> PriceRepository:
        """Создаёт репозиторий с сессией БД."""
        return PriceRepository(session=session)

    @staticmethod
    def create_service_container(session: AsyncSession) -> ServiceContainer:
        """
        Создаёт контейнер с сервисом и всеми зависимостями.

        Returns:
            ServiceContainer с сервисом и клиентом для последующего закрытия.
        """
        client = ServiceFactory.create_deribit_client()
        repository = ServiceFactory.create_price_repository(session)

        service = PriceService(
            deribit_client=client,
            repository=repository,
        )

        return ServiceContainer(service=service, client=client)


async def get_price_service(
    session: AsyncSession,
) -> AsyncGenerator[PriceService, None]:
    """
    Зависимость FastAPI для инъекции сервиса в эндпоинты.

    Гарантирует закрытие ресурсов (aiohttp сессии) после обработки запроса.
    """
    container = ServiceFactory.create_service_container(session)
    try:
        yield container.service
    finally:
        await container.client.close()
