from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
import config
from config import ADMIN_IDS, TRIGGER_PRICE_CHANGE_PERCENT, TRIGGER_TIMEFRAME_MINUTES
from database import async_session, User, News, select, func
from keyboards import admin_keyboard
from services.api_client import api_client
import logging
import asyncio
from datetime import datetime

router = Router()
logger = logging.getLogger(__name__)

class AdminSettings(StatesGroup):
    waiting_for_price_change = State()
    waiting_for_timeframe = State()
    waiting_for_broadcast = State()
    waiting_for_channel_post = State()

# Проверка прав администратора
async def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    if user_id in ADMIN_IDS:
        return True
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        return user.is_admin if user else False

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Панель администратора."""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен.")
        return
        
    text = (
        "🔐 **Панель администратора**\n\n"
        "**Текущие настройки триггера:**\n"
        f"• Изменение цены: {config.TRIGGER_PRICE_CHANGE_PERCENT}%\n"
        f"• Таймфрейм: {config.TRIGGER_TIMEFRAME_MINUTES} мин.\n\n"
        "**Доступные команды:**\n"
        "/api_status — проверить состояние API\n"
        "/stats — статистика бота\n"
        "/set_trigger_price — изменить порог цены\n"
        "/set_trigger_time — изменить таймфрейм\n"
        "/broadcast — рассылка всем пользователям\n"
        "/channel_post — отправить в канал"
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

@router.message(Command("api_status"))
async def cmd_api_status(message: Message):
    """Проверка состояния API (только для админов)."""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен.")
        return
    
    status_message = await message.answer("🔍 Проверяем подключение к API...")
    
    # Тестируем разные эндпоинты
    results = []
    
    # 1. Проверка основного API новостей
    try:
        start_time = datetime.now()
        news = await api_client.get_latest_news(limit=1)
        response_time = (datetime.now() - start_time).total_seconds()
        
        if news:
            results.append(f"✅ **News API**: OK ({response_time:.2f}с)")
            if news and len(news) > 0:
                results.append(f"   📰 Пример: {news[0]['title'][:100]}...")
        else:
            results.append(f"❌ **News API**: Не отвечает")
    except Exception as e:
        results.append(f"❌ **News API**: Ошибка - {str(e)[:50]}")
    
    # 2. Проверка AI sentiment
    try:
        start_time = datetime.now()
        sentiment = await api_client.get_ai_sentiment(asset="BTC")
        response_time = (datetime.now() - start_time).total_seconds()
        
        if sentiment:
            results.append(f"✅ **AI Sentiment**: OK ({response_time:.2f}с)")
            results.append(f"   🧠 Тональность BTC: {sentiment.get('label', 'N/A')}")
        else:
            results.append(f"❌ **AI Sentiment**: Не отвечает")
    except Exception as e:
        results.append(f"❌ **AI Sentiment**: Ошибка - {str(e)[:50]}")
    
    # 3. Проверка рыночных данных
    try:
        start_time = datetime.now()
        metrics = await api_client.get_market_metrics()
        response_time = (datetime.now() - start_time).total_seconds()
        
        if metrics and metrics.get('btc_price'):
            results.append(f"✅ **Market Data**: OK ({response_time:.2f}с)")
            results.append(f"   💰 BTC: ${metrics['btc_price']:,.2f}")
        else:
            results.append(f"❌ **Market Data**: Не отвечает")
    except Exception as e:
        results.append(f"❌ **Market Data**: Ошибка - {str(e)[:50]}")
    
    # 4. Проверка CoinGecko (для исторических цен)
    try:
        start_time = datetime.now()
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.coingecko.com/api/v3/ping") as resp:
                response_time = (datetime.now() - start_time).total_seconds()
                if resp.status == 200:
                    results.append(f"✅ **CoinGecko API**: OK ({response_time:.2f}с)")
                else:
                    results.append(f"❌ **CoinGecko API**: Статус {resp.status}")
    except Exception as e:
        results.append(f"❌ **CoinGecko API**: Ошибка - {str(e)[:50]}")
    
    # Формируем итоговый отчет
    report = "📡 **Статус API подключений**\n\n" + "\n".join(results)
    
    await status_message.edit_text(report, parse_mode=ParseMode.MARKDOWN)

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Показывает статистику бота (только для админов)."""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен.")
        return
        
    async with async_session() as session:
        users_count = await session.scalar(select(func.count(User.id)))
        news_count = await session.scalar(select(func.count(News.id)))
        triggered_count = await session.scalar(select(func.count(News.id)).where(News.triggered == True))
    
    # Получаем время последней проверки из планировщика
    from scheduler import scheduler
    next_check = None
    for job in scheduler.get_jobs():
        if job.id == "check_triggers":
            next_check = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "не запланировано"
    
    text = (
        f"📊 **Статистика бота**\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"📰 Всего новостей в БД: {news_count}\n"
        f"⚡ Триггерных новостей: {triggered_count}\n"
        f"📈 Порог триггера: {config.TRIGGER_PRICE_CHANGE_PERCENT}% за {config.TRIGGER_TIMEFRAME_MINUTES} мин.\n"
        f"⏰ Следующая проверка: {next_check or 'не active'}\n\n"
        f"📡 Для проверки API используй /api_status"
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

@router.message(Command("set_trigger_price"))
async def cmd_set_price(message: Message, state: FSMContext):
    """Установка порога изменения цены."""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен.")
        return
    await message.answer("Введите новое значение процента изменения цены (например: 2.5):")
    await state.set_state(AdminSettings.waiting_for_price_change)

@router.message(AdminSettings.waiting_for_price_change)
async def process_price_change(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен.")
        await state.clear()
        return
    try:
        new_value = float(message.text)
        config.TRIGGER_PRICE_CHANGE_PERCENT = new_value
        await message.answer(f"✅ Порог изменения цены установлен: {new_value}%")
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число.")
    finally:
        await state.clear()

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    """Рассылка сообщения всем пользователям."""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен.")
        return
    await message.answer("Введите сообщение для рассылки всем пользователям:")
    await state.set_state(AdminSettings.waiting_for_broadcast)

@router.message(AdminSettings.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен.")
        await state.clear()
        return
    from bot import bot
    text = message.text
    async with async_session() as session:
        users = await session.execute(select(User.telegram_id))
        user_ids = [row[0] for row in users]
    
    sent = 0
    status_msg = await message.answer(f"📤 Начинаю рассылку {len(user_ids)} пользователям...")
    
    for i, uid in enumerate(user_ids):
        try:
            await bot.send_message(uid, f"📢 **Объявление:**\n{text}", parse_mode=ParseMode.MARKDOWN)
            sent += 1
            if i % 10 == 0:  # Обновляем статус каждые 10 сообщений
                await status_msg.edit_text(f"📤 Прогресс: {i}/{len(user_ids)} отправлено...")
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение {uid}: {e}")
    
    await status_msg.edit_text(f"✅ Рассылка завершена. Отправлено {sent} из {len(user_ids)} пользователям.")
    await state.clear()

@router.message(Command("channel_post"))
async def cmd_channel_post(message: Message, state: FSMContext):
    """Отправка сообщения в канал."""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен.")
        return
    await message.answer("Введите сообщение для публикации в канал:")
    await state.set_state(AdminSettings.waiting_for_channel_post)

@router.message(AdminSettings.waiting_for_channel_post)
async def process_channel_post(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен.")
        await state.clear()
        return
    from bot import bot
    from config import CHANNEL_ID
    if not CHANNEL_ID:
        await message.answer("❌ CHANNEL_ID не задан в .env")
        return
    try:
        await bot.send_message(CHANNEL_ID, message.text, parse_mode=ParseMode.MARKDOWN)
        await message.answer("✅ Сообщение опубликовано в канале.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    await state.clear()