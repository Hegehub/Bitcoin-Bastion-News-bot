from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.enums import ParseMode
from services.api_client import api_client
from redis_cache import get_cache, set_cache
from database import add_user
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def cmd_start(message: Message):
    await add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    text = (
        "👋 Привет! Я бот крипто-аналитики.\n\n"
        "Я получаю новости в реальном времени и определяю, какие из них вызвали движение цены. "
        "Такие новости публикуются в канале.\n\n"
        "📊 Доступные команды:\n"
        "/btc — цена BTC, страх/жадность, доминация\n"
        "/whales — последние китовые транзакции\n"
        "/liquidations — последние ликвидации\n"
        "/funding — ставки фандинга\n"
        "/latest — последние 5 новостей\n"
        "/feargreed — индекс страха и жадности\n"
        "/dominance — доминация BTC и ETH\n"
        "/subscribe — управление подписками (киты, ликвидации, триггерные новости)"
    )
    await message.answer(text)

@router.message(Command("btc"))
async def cmd_btc(message: Message):
    cached = await get_cache("market_metrics")
    if cached:
        await message.answer(cached, parse_mode=ParseMode.MARKDOWN)
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
    await set_cache("market_metrics", text, ttl=300)
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

@router.message(Command("whales"))
async def cmd_whales(message: Message):
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
    await message.answer(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

@router.message(Command("liquidations"))
async def cmd_liquidations(message: Message):
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
    rates = await api_client.get_funding_rates()
    if not rates:
        await message.answer("Не удалось получить фандинг рейты.")
        return

    text = "💰 **Funding Rates (8h):**\n\n"
    for rate in rates[:10]:
        emoji = "🟢" if rate['rate'] > 0 else "🔴" if rate['rate'] < 0 else "⚪"
        text += f"{emoji} {rate['pair']}: {rate['rate']*100:.4f}%\n"
    await message.answer(text)

@router.message(Command("latest"))
async def cmd_latest(message: Message):
    news = await api_client.get_latest_news(limit=5)
    if not news:
        await message.answer("Новостей пока нет.")
        return
    text = "📰 **Последние новости:**\n\n"
    for item in news:
        text += f"• [{item['title']}]({item['url']}) — {item['source']}\n"
    await message.answer(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

@router.message(Command("feargreed"))
async def cmd_feargreed(message: Message):
    cached = await get_cache("fear_greed")
    if cached:
        await message.answer(cached)
        return
    fg = await api_client._make_request("/api/market/fear-greed")
    if not fg:
        await message.answer("Не удалось получить индекс.")
        return
    text = f"😨 Индекс страха и жадности: **{fg['value']}** — {fg['classification']}"
    await set_cache("fear_greed", text, ttl=600)
    await message.answer(text)

@router.message(Command("dominance"))
async def cmd_dominance(message: Message):
    cached = await get_cache("dominance")
    if cached:
        await message.answer(cached)
        return
    dom = await api_client._make_request("/api/dominance")
    if not dom:
        await message.answer("Не удалось получить доминацию.")
        return
    text = f"📊 Доминация BTC: {dom['btc_dominance']:.2f}%\n📊 Доминация ETH: {dom['eth_dominance']:.2f}%"
    await set_cache("dominance", text, ttl=600)
    await message.answer(text)

@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    from database import async_session, User, select
    from keyboards import subscription_keyboard
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
        if not user:
            user = User(telegram_id=message.from_user.id)
            session.add(user)
            await session.commit()
        await message.answer("Управление подписками:", reply_markup=subscription_keyboard(user))

@router.callback_query(F.data.startswith("sub_"))
async def process_subscription(callback: CallbackQuery):
    from database import async_session, User, select
    sub_type = callback.data.split("_")[1]
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == callback.from_user.id))
        if user:
            if sub_type == "whales":
                user.subscribed_whales = not user.subscribed_whales
            elif sub_type == "liquidations":
                user.subscribed_liquidations = not user.subscribed_liquidations
            elif sub_type == "triggered":
                user.subscribed_triggered = not user.subscribed_triggered
            await session.commit()
        await callback.message.edit_reply_markup(reply_markup=subscription_keyboard(user))
    await callback.answer("Настройки сохранены")
