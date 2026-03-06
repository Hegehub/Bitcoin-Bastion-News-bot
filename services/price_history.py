from datetime import datetime
from typing import Optional
import logging
from services.cryptorank_client import cryptorank
from config import TRIGGER_TIMEFRAME_MINUTES

logger = logging.getLogger(__name__)

class PriceHistoryService:
    """
    Сервис для получения исторических цен через CryptoRank.
    Полностью заменяет CoinGecko.
    """

    async def get_price_change_percent(self, coin_symbol: str, from_time: datetime, to_time: datetime) -> Optional[float]:
        """
        Возвращает изменение цены в процентах между двумя моментами времени.
        coin_symbol: например, "BTC", "ETH".
        """
        # Сначала получаем числовой ID монеты в CryptoRank
        currency_id = await cryptorank.get_currency_id(coin_symbol)
        if not currency_id:
            logger.warning(f"Не найден ID для символа {coin_symbol}")
            return None
        return await cryptorank.get_price_change_percent(currency_id, from_time, to_time)

    async def get_current_price(self, coin_symbol: str) -> Optional[float]:
        """
        Возвращает текущую цену монеты. Для простоты используем глобальные метрики (цена BTC).
        Если нужна другая монета, потребуется отдельный запрос, но пока оставим как есть.
        """
        # Упрощённо: для BTC берём из глобальных метрик
        if coin_symbol.upper() == "BTC":
            global_metrics = await cryptorank.get_global_metrics()
            if global_metrics and "btcPrice" in global_metrics:
                return float(global_metrics["btcPrice"])
        # Для других монет можно реализовать через /currencies/{id}, но пока не требуется
        return None

    async def close(self):
        await cryptorank.close()

# Глобальный экземпляр
price_history = PriceHistoryService()