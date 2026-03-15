from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, Float, String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Price(Base):
    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    ticker: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Instrument name (BTC_USD, ETH_USD)"
    )

    price: Mapped[float] = mapped_column(Float, nullable=False, comment="price in USD")

    timestamp: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment="UNIX timestamp"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    def __repr__(self) -> str:
        return f"<Price(ticker={self.ticker}, price={self.price}, ts={self.timestamp})>"

    @classmethod
    def from_api_data(
        cls, ticker: str, price: float, timestamp: Optional[int] = None
    ) -> "Price":
        """
        Фабричный метод для создания модели из данных API.

        Args:
            ticker: Название валюты.
            price: Цена.
            timestamp: Опциональный UNIX timestamp из API (если нет - берется текущий).
        """
        return cls(
            ticker=ticker.upper(),
            price=price,
            timestamp=timestamp or int(datetime.now().timestamp()),
        )
