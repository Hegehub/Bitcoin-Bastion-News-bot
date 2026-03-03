from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from middlewares import AdminMiddleware
from config import TRIGGER_PRICE_CHANGE_PERCENT, TRIGGER_TIMEFRAME_MINUTES
import config
import logging

router = Router()
router.message.middleware(AdminMiddleware())
router.callback_query.middleware(AdminMiddleware())

logger = logging.getLogger(__name__)

class AdminSettings(StatesGroup):
    waiting_for_price_change = State()
    waiting_for_timeframe = State()

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Панель администратора."""
    text = (
        "🔐 **Панель администратора**\n\n"
        "**Текущие настройки триггера:**\n"
        f"• Изменение цены: {config.TRIGGER_PRICE_CHANGE_PERCENT}%\n"
        f"• Таймфрейм: {config.TRIGGER_TIMEFRAME_MINUTES} мин.\n\n"
        "**Действия:**\n"
        "/set_trigger_price — установить % изменения цены\n"
        "/set_trigger_time — установить таймфрейм (мин)\n"
        "/stats — статистика бота\n"
        "/broadcast — разослать сообщение всем пользователям\n"
        "/check_news — ручной поиск триггерных новостей за последний час"
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("set_trigger_price"))
async def cmd_set_price(message: Message, state: FSMContext):
    await message.answer("Введите новое значение процента изменения цены (например: 2.5):")
    await state.set_state(AdminSettings.waiting_for_price_change)

@router.message(AdminSettings.waiting_for_price_change)
async def process_price_change(message: Message, state: FSMContext):
    try:
        new_value = float(message.text)
        # В реальном проекте здесь обновление config или запись в БД
        config.TRIGGER_PRICE_CHANGE_PERCENT = new_value
        await message.answer(f"✅ Порог изменения цены установлен: {new_value}%")
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число.")
    finally:
        await state.clear()

# Аналогично для /set_trigger_time

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Показывает статистику использования API и базы данных."""
    # Здесь запросы к БД (кол-во юзеров, новостей) и к API (лимиты, если есть)
    from database import async_session, User, News
    from services.api_client import CryptoNewsAPIClient
    
    api_client = CryptoNewsAPIClient()
    # Пример: получаем статистику от API (если есть такой эндпоинт)
    # api_stats = await api_client.get_stats()
    
    async with async_session() as session:
        users_count = await session.scalar(select(func.count(User.id)))
        news_count = await session.scalar(select(func.count(News.id)))
        triggered_count = await session.scalar(select(func.count(News.id)).where(News.triggered == True))
    
    text = (
        f"📊 **Статистика бота**\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"📰 Всего новостей в БД: {news_count}\n"
        f"⚡ Триггерных новостей: {triggered_count}\n"
        f"📈 Текущий порог триггера: {config.TRIGGER_PRICE_CHANGE_PERCENT}% за {config.TRIGGER_TIMEFRAME_MINUTES} мин."
    )
    await message.answer(text, parse_mode="Markdown")
