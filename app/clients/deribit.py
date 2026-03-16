import logging
from typing import Any, Dict, Optional, List
from aiohttp import ClientSession, ClientError, ClientTimeout

from app.core.logging import get_logger


class DeribitClientError(Exception):
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class DeribitClient:

    ENDPOINT_INDEX_PRICE = "/api/v2/public/get_index_price"
    SUPPORTED_INSTRUMENTS = ["BTC_USD", "ETH_USD"]

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        session: Optional[ClientSession] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = ClientTimeout(total=timeout)
        self._external_session = session
        self._session: Optional[ClientSession] = None
        self.logger = get_logger(__name__)

    async def _get_session(self) -> ClientSession:
        if self._external_session:
            return self._external_session

        if self._session is None or self._session.closed:
            self._session = ClientSession(timeout=self.timeout)
            self.logger.debug("Created new aiohttp session")

        return self._session

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Базовый метод для выполнения HTTP-запроса.

        Args:
            method: HTTP метод (GET, POST).
            endpoint: Путь эндпоинта (например, '/api/v2/public/get_index_price').
            params: Query параметры запроса.

        Returns:
            Словарь с данными из поля 'result' ответа API.

        Raises:
            DeribitClientError: При ошибке запроса или валидации ответа.
        """
        url = f"{self.base_url}{endpoint}"
        self.logger.debug(f"🌐 HTTP {method.upper()} {url} | params={params}")
        session = await self._get_session()

        self.logger.debug(f"Request: {method.upper()} {url} with params {params}")

        try:
            async with session.request(
                method=method,
                url=url,
                params=params,
                headers={"Content-Type": "application/json"},
            ) as response:
                self.logger.debug(f"📥 Response status: {response.status}")

                response.raise_for_status()
                data = await response.json()

                # Deribit использует JSON-RPC формат
                # Проверяем наличие поля 'result'
                if "error" in data:
                    error_msg = data.get("error", {}).get(
                        "message", "Unknown API error"
                    )
                    self.logger.error(f"API Error: {error_msg}")
                    raise DeribitClientError(f"Deribit API error: {error_msg}")

                if "result" not in data:
                    self.logger.error(f"Unexpected response format: {data}")
                    raise DeribitClientError(
                        "Invalid response format: missing 'result' field"
                    )

                return data["result"]

        except ClientError as e:
            self.logger.error(f"HTTP client error: {e}", exc_info=True)
            raise DeribitClientError(f"Request failed: {e}", original_error=e)
        except Exception as e:
            self.logger.error(f"Unexpected error during request: {e}", exc_info=True)
            raise DeribitClientError(f"Unexpected error: {e}", original_error=e)

    async def get_index_price(self, instrument_name: str) -> Optional[float]:
        """
        Получает индексную цену для указанного инструмента.

        Args:
            instrument_name: Название инструмента (например, 'BTC_USD', 'ETH_USD').

        Returns:
            Цена в виде float или None, если цена не найдена.
        """
        # Нормализуем название инструмента к формату API (нижний регистр)
        index_name = instrument_name.lower()

        try:
            result = await self._request(
                method="GET",
                endpoint=self.ENDPOINT_INDEX_PRICE,
                params={"index_name": index_name},
            )

            price = result.get("price")
            if price is None:
                self.logger.warning(f"No price found for {instrument_name}")
                return None

            return float(price)

        except DeribitClientError as e:
            self.logger.error(f"Failed to get price for {instrument_name}: {e}")
            raise  # Пробрасываем исключение выше для обработки в сервисе

    async def get_btc_price(self) -> Optional[float]:
        """
        Получает текущую индексную цену BTC.

        Returns:
            Цена BTC в USD.
        """
        return await self.get_index_price("BTC_USD")

    async def get_eth_price(self) -> Optional[float]:
        """
        Получает текущую индексную цену ETH.

        Returns:
            Цена ETH в USD.
        """
        return await self.get_index_price("ETH_USD")

    async def get_prices_batch(self) -> Dict[str, Optional[float]]:
        """
        Получает цены для всех отслеживаемых валют (BTC, ETH) параллельно.

        Returns:
            Словарь вида {'BTC_USD': 123.45, 'ETH_USD': 67.89}.
        """
        import asyncio

        results = {}
        tasks = []

        for instrument in self.SUPPORTED_INSTRUMENTS:
            task = self.get_index_price(instrument)
            tasks.append((instrument, task))

        # Выполняем запросы параллельно
        completed = await asyncio.gather(
            *(task for _, task in tasks), return_exceptions=True
        )

        for (instrument, _), result in zip(tasks, completed):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to fetch {instrument}: {result}")
                results[instrument] = None
            else:
                results[instrument] = result

        return results

    async def close(self) -> None:
        """
        Закрывает сессию aiohttp, если она была создана внутри клиента.
        """
        if self._session and not self._session.closed and not self._external_session:
            await self._session.close()
            self.logger.debug("Closed internal aiohttp session")

    async def __aenter__(self) -> "DeribitClient":
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
