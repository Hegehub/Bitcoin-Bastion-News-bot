from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from services.api_client import CryptoNewsAPIClient
from redis_cache import get_cached, set_cache
import logging

router = Router()
api_client = CryptoNewsAPIClient() # В реальном проекте внедрять зависимости через middleware
logger = logging.getLogger(__name__)

@router.message(Command("btc"))
async def cmd_btc(message: Message):
    """Показывает цену BTC, страх и жадность, доминацию."""
    # Пытаемся получить из кэша
    cached = await get_cached("market_metrics")
    if cached:
        await message.answer(cached)
        return

    metrics = await api_client.get_market_metrics()
    if not metrics or not metrics.get('btc_price'):
        await message.answer("Не удалось получить данные о рынке. Попробуйте позже.")
        return

    text = (
        f"💰 **Bitcoin (BTC)**\n"
        f"Цена: ${metrics['btc_price']:,.2f}\n\n"
        f"😨 Индекс страха и жадности: **{metrics['fear_greed']}**\n"
        f"({metrics['fear_greed_class']})\n"
        f"📊 Доминация BTC: {metrics['btc_dominance']:.2f}%\n"
        f"📊 Доминация ETH: {metrics['eth_dominance']:.2f}%"
    )
    
    await set_cache("market_metrics", text, ttl=300) # Кэш на 5 минут
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("whales"))
async def cmd_whales(message: Message):
    """Показывает последние китовые транзакции."""
    whales = await api_client.get_whale_transactions(limit=3)
    if not whales:
        await message.answer("Не удалось получить данные о китовых транзакциях.")
        return
    
    text = "🐋 **Последние китовые транзакции:**\n\n"
    for tx in whales:
        text += (
            f"• {tx['amount']:.2f} {tx['coin']} (${tx['value_usd']:,.0f})\n"
            f"  From: {tx['from'][:6]}... → To: {tx['to'][:6]}...\n"
            f"  [Смотреть]({tx['tx_url']})\n\n"
        )
    await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)

@router.message(Command("liquidations"))
async def cmd_liquidations(message: Message):
    """Показывает последние ликвидации."""
    liqs = await api_client.get_liquidations(limit=5)
    if not liqs:
        await message.answer("Не удалось получить данные о ликвидациях.")
        return
    
    text = "💥 **Последние ликвидации:**\n\n"
    for liq in liqs:
        emoji = "🟢" if liq['side'] == 'long' else "🔴"
        text += f"{emoji} {liq['side'].upper()} {liq['amount_usd']:,.0f}$ на {liq['pair']}\n"
    await message.answer(text)

@router.message(Command("funding"))
async def cmd_funding(message: Message):
    """Показывает ставки фандинга."""
    rates = await api_client.get_funding_rates()
    if not rates:
        await message.answer("Не удалось получить фандинг рейты.")
        return
    
    text = "💰 **Funding Rates (8h):**\n\n"
    for rate in rates[:10]:
        emoji = "🟢" if rate['rate'] > 0 else "🔴" if rate['rate'] < 0 else "⚪"
        text += f"{emoji} {rate['pair']}: {rate['rate']*100:.4f}%\n"
    await message.answer(text)
