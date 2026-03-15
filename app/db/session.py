from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import AsyncIterator

from app.core.config import settings

from app.db.base import Base


class Database:
    def __init__(self, database_url: str, echo: bool = False):
        self.database_url = database_url
        self.echo = echo
        self._engine = None
        self._session_maker = None

    def create_engine(self) -> None:
        if self._engine is None:
            self._engine = create_async_engine(
                self.database_url, echo=self.echo, future=True, pool_pre_ping=True
            )

    def create_session_maker(self) -> None:
        if self._engine is None:
            self.create_engine()

        self._session_maker = async_sessionmaker(
            bind=self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def get_session(self) -> AsyncIterator[AsyncSession]:
        if self._session_maker is None:
            self.create_session_maker()
        async with self._session_maker() as session:
            yield session

    async def init_db(self) -> None:
        if self._engine is None:
            self.create_engine()
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()


database = Database(database_url=settings.db.database_url, echo=settings.app.debug)
