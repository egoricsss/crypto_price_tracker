from typing import List, Optional, Sequence
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price import Price


class PriceRepository:
    """
    Репозиторий для операций CRUD с моделью Price.
    
    Инкапсулирует все SQL-запросы. Бизнес-логика не должна знать о SQLAlchemy.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, price: Price) -> Price:
        """Сохраняет новую запись о цене."""
        self.session.add(price)
        await self.session.commit()
        await self.session.refresh(price)
        return price

    async def create_batch(self, prices: List[Price]) -> Sequence[Price]:
        """Сохраняет несколько записей за один раз (оптимизация для Celery)."""
        self.session.add_all(prices)
        await self.session.commit()
        return prices

    async def get_by_ticker(self, ticker: str, limit: int = 100) -> Sequence[Price]:
        """
        Получает последние записи по указанному тикеру.
        
        Args:
            ticker: Название валюты.
            limit: Максимальное количество записей.
        """
        query = (
            select(Price)
            .where(Price.ticker == ticker.upper())
            .order_by(desc(Price.timestamp))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_last_price(self, ticker: str) -> Optional[Price]:
        """Получает последнюю записанную цену для тикера."""
        query = (
            select(Price)
            .where(Price.ticker == ticker.upper())
            .order_by(desc(Price.timestamp))
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_ticker_and_date_range(
        self, 
        ticker: str, 
        start_ts: int, 
        end_ts: int
    ) -> Sequence[Price]:
        """
        Получает цены за указанный диапазон времени.
        
        Args:
            ticker: Название валюты.
            start_ts: Начало диапазона (UNIX timestamp).
            end_ts: Конец диапазона (UNIX timestamp).
        """
        query = (
            select(Price)
            .where(
                Price.ticker == ticker.upper(),
                Price.timestamp >= start_ts,
                Price.timestamp <= end_ts
            )
            .order_by(Price.timestamp)
        )
        result = await self.session.execute(query)
        return result.scalars().all()