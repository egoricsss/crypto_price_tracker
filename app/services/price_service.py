import logging
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from app.clients.deribit import DeribitClient, DeribitClientError
from app.db.repository import PriceRepository
from app.models.price import Price
from app.core.logging import get_logger


class PriceServiceError(Exception):
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class PriceService:
    """
    Сервис для управления операциями с ценами криптовалют.

    Координирует работу между DeribitClient (получение данных)
    и PriceRepository (сохранение/чтение из БД).

    Принципы:
    - Зависимости инжектируются через __init__ (для тестируемости)
    - Нет глобальных переменных
    - Логирование всех операций
    - Обработка ошибок с сохранением контекста
    """

    # Поддерживаемые тикеры (из требования задания)
    SUPPORTED_TICKERS = ["BTC_USD", "ETH_USD"]

    def __init__(
        self,
        deribit_client: DeribitClient,
        repository: PriceRepository,
    ) -> None:
        """
        Инициализация сервиса.

        Args:
            deribit_client: Клиент для запросов к бирже Deribit.
            repository: Репозиторий для операций с БД.
        """
        self.deribit_client = deribit_client
        self.repository = repository
        self.logger = get_logger(__name__)

    async def fetch_and_save_prices(self) -> Dict[str, Optional[float]]:
        """
        Получает текущие цены всех поддерживаемых валют и сохраняет их в БД.

        Используется в Celery-задаче для периодического сбора данных.

        Returns:
            Словарь с результатами: {'BTC_USD': 45000.5, 'ETH_USD': 3200.1}

        Raises:
            PriceServiceError: При критической ошибке сохранения в БД.
        """
        self.logger.info("Starting price fetch and save operation")
        results = {}
        prices_to_save: List[Price] = []

        try:
            # Получаем все цены параллельно через клиент
            fetched_prices = await self.deribit_client.get_prices_batch()

            for ticker, price in fetched_prices.items():
                if price is not None:
                    price_model = Price.from_api_data(
                        ticker=ticker,
                        price=price,
                        timestamp=int(datetime.now().timestamp()),
                    )
                    prices_to_save.append(price_model)
                    results[ticker] = price
                    self.logger.info(f"Fetched {ticker}: ${price}")
                else:
                    self.logger.warning(f"Failed to fetch price for {ticker}")
                    results[ticker] = None

            # Сохраняем все цены одной транзакцией (оптимизация)
            if prices_to_save:
                await self.repository.create_batch(prices_to_save)
                self.logger.info(
                    f"Successfully saved {len(prices_to_save)} prices to DB"
                )

            return results

        except DeribitClientError as e:
            self.logger.error(f"Deribit client error: {e}", exc_info=True)
            raise PriceServiceError(
                f"Failed to fetch prices from Deribit: {e}", original_error=e
            )
        except Exception as e:
            self.logger.error(
                f"Unexpected error during fetch and save: {e}", exc_info=True
            )
            raise PriceServiceError(
                f"Failed to save prices to database: {e}", original_error=e
            )

    async def get_last_price(self, ticker: str) -> Optional[Dict[str, any]]:
        """
        Получает последнюю сохранённую цену для указанного тикера.

        Args:
            ticker: Название валюты (BTC_USD, ETH_USD).

        Returns:
            Словарь с данными цены или None, если данных нет.
            Формат: {'ticker': str, 'price': float, 'timestamp': int}

        Raises:
            PriceServiceError: При ошибке валидации тикера.
        """
        self._validate_ticker(ticker)
        self.logger.debug(f"Getting last price for {ticker}")

        try:
            price_model = await self.repository.get_last_price(ticker)

            if price_model is None:
                self.logger.warning(f"No price data found for {ticker}")
                return None

            return self._model_to_dict(price_model)

        except Exception as e:
            self.logger.error(
                f"Error getting last price for {ticker}: {e}", exc_info=True
            )
            raise PriceServiceError(f"Failed to get last price: {e}", original_error=e)

    async def get_all_prices(
        self, ticker: str, limit: int = 100
    ) -> List[Dict[str, any]]:
        """
        Получает все сохранённые цены для указанного тикера.

        Args:
            ticker: Название валюты.
            limit: Максимальное количество записей (защита от перегрузки).

        Returns:
            Список словарей с данными цен.

        Raises:
            PriceServiceError: При ошибке валидации тикера.
        """
        self._validate_ticker(ticker)
        self.logger.debug(f"Getting all prices for {ticker} (limit: {limit})")

        try:
            price_models = await self.repository.get_by_ticker(ticker, limit=limit)
            return [self._model_to_dict(model) for model in price_models]

        except Exception as e:
            self.logger.error(
                f"Error getting all prices for {ticker}: {e}", exc_info=True
            )
            raise PriceServiceError(f"Failed to get all prices: {e}", original_error=e)

    async def get_prices_by_date_range(
        self,
        ticker: str,
        start_timestamp: int,
        end_timestamp: int,
    ) -> List[Dict[str, any]]:
        """
        Получает цены за указанный диапазон времени.

        Args:
            ticker: Название валюты.
            start_timestamp: Начало диапазона (UNIX timestamp).
            end_timestamp: Конец диапазона (UNIX timestamp).

        Returns:
            Список словарей с данными цен за период.

        Raises:
            PriceServiceError: При ошибке валидации или некорректном диапазоне.
        """
        self._validate_ticker(ticker)
        self.logger.debug(
            f"Getting prices for {ticker} from {start_timestamp} to {end_timestamp}"
        )

        # Валидация диапазона
        if start_timestamp > end_timestamp:
            raise PriceServiceError(
                "start_timestamp cannot be greater than end_timestamp"
            )

        try:
            price_models = await self.repository.get_by_ticker_and_date_range(
                ticker=ticker,
                start_ts=start_timestamp,
                end_ts=end_timestamp,
            )
            return [self._model_to_dict(model) for model in price_models]

        except Exception as e:
            self.logger.error(
                f"Error getting prices by date range for {ticker}: {e}", exc_info=True
            )
            raise PriceServiceError(
                f"Failed to get prices by date range: {e}", original_error=e
            )

    def _validate_ticker(self, ticker: str) -> None:
        """
        Валидирует тикер на наличие в списке поддерживаемых.

        Args:
            ticker: Название валюты для проверки.

        Raises:
            PriceServiceError: Если тикер не поддерживается.
        """
        normalized_ticker = ticker.upper()
        if normalized_ticker not in self.SUPPORTED_TICKERS:
            raise PriceServiceError(
                f"Unsupported ticker: {ticker}. Supported: {self.SUPPORTED_TICKERS}"
            )

    def _model_to_dict(self, price_model: Price) -> Dict[str, any]:
        """
        Преобразует SQLAlchemy модель в словарь для API-ответа.

        Args:
            price_model: Модель Price из БД.

        Returns:
            Словарь с сериализуемыми данными.
        """
        return {
            "ticker": price_model.ticker,
            "price": price_model.price,
            "timestamp": price_model.timestamp,
            "created_at": (
                price_model.created_at.isoformat() if price_model.created_at else None
            ),
        }
