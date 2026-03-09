from datetime import datetime
from typing import Optional
import logging
from services.cryptorank_client import cryptorank

logger = logging.getLogger(__name__)

class PriceHistoryService:
    async def _get_session(self):
        return await cryptorank._get_session()

    async def get_price_change_percent(self, coin_symbol: str, from_time: datetime, to_time: datetime) -> Optional[float]:
        currency_id = await cryptorank.get_currency_id(coin_symbol)
        if not currency_id:
            logger.warning(f"Не найден ID для символа {coin_symbol}")
            return None
        return await cryptorank.get_price_change_percent(currency_id, from_time, to_time)

    async def get_current_price(self, coin_symbol: str) -> Optional[float]:
        if coin_symbol.upper() == "BTC":
            global_metrics = await cryptorank.get_global_metrics()
            if global_metrics and "btcPrice" in global_metrics:
                return float(global_metrics["btcPrice"])
        return None

    async def close(self):
        await cryptorank.close()

price_history = PriceHistoryService()
