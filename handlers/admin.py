from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from sqlalchemy import func
from middlewares import AdminCheckMiddleware
import config
from config import ADMIN_IDS, TRIGGER_PRICE_CHANGE_PERCENT, TRIGGER_TIMEFRAME_MINUTES
from database import async_session, User, News, select
from keyboards import admin_keyboard
from services.trigger_detector import trigger_detector
from services.price_history import price_history
from utils import escape_html
import logging
import asyncio

router = Router()
router.message.middleware(AdminCheckMiddleware())
router.callback_query.middleware(AdminCheckMiddleware())

logger = logging.getLogger(__name__)

class AdminSettings(StatesGroup):
    waiting_for_price_change = State()
    waiting_for_timeframe = State()
    waiting_for_broadcast = State()

async def get_user_language(user_id: int) -> str:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        return user.language if user else 'en'

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    text = (
        "🔐 <b>Admin Panel</b>\n\n"
        "<b>Current trigger settings:</b>\n"
        f"• Price change: {config.TRIGGER_PRICE_CHANGE_PERCENT}%\n"
        f"• Timeframe: {config.TRIGGER_TIMEFRAME_MINUTES} min.\n\n"
        "<b>Actions:</b>"
        if lang == 'en' else
        "🔐 <b>Панель администратора</b>\n\n"
        "<b>Текущие настройки триггера:</b>\n"
        f"• Изменение цены: {config.TRIGGER_PRICE_CHANGE_PERCENT}%\n"
        f"• Таймфрейм: {config.TRIGGER_TIMEFRAME_MINUTES} мин.\n\n"
        "<b>Действия:</b>"
    )
    await message.answer(text, reply_markup=admin_keyboard(lang), parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    async with async_session() as session:
        users_count = await session.scalar(select(func.count(User.id)))
        news_count = await session.scalar(select(func.count(News.id)))
        triggered_count = await session.scalar(select(func.count(News.id)).where(News.triggered == True))
    trigger_stats = await trigger_detector.analyze_historical_news(days=7)
    text = (
        f"📊 <b>Bot Statistics</b>\n\n"
        f"👥 Users: {users_count}\n"
        f"📰 Total news in DB: {news_count}\n"
        f"⚡ Triggered news: {triggered_count}\n\n"
        f"<b>Last 7 days analysis:</b>\n"
        f"• Analyzed: {trigger_stats['total_analyzed']}\n"
        f"• Triggered: {trigger_stats['triggered']}\n"
        f"• Accuracy: {trigger_stats['accuracy']:.1f}%\n"
        f"• By coin: {', '.join([f'{k}: {v}' for k, v in trigger_stats['by_coin'].items()])}"
        if lang == 'en' else
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"📰 Всего новостей в БД: {news_count}\n"
        f"⚡ Триггерных новостей: {triggered_count}\n\n"
        f"<b>Анализ за 7 дней:</b>\n"
        f"• Проанализировано: {trigger_stats['total_analyzed']}\n"
        f"• Триггерных: {trigger_stats['triggered']}\n"
        f"• Точность: {trigger_stats['accuracy']:.1f}%\n"
        f"• По монетам: {', '.join([f'{k}: {v}' for k, v in trigger_stats['by_coin'].items()])}"
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML)
    await callback.answer()

@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await callback.message.edit_text(
        "Enter new price change threshold (in %, e.g., 2.5):" if lang == 'en'
        else "Введите новый порог изменения цены (в %, например 2.5):"
    )
    await state.set_state(AdminSettings.waiting_for_price_change)
    await callback.answer()

@router.message(AdminSettings.waiting_for_price_change)
async def process_price_change(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    try:
        new_value = float(message.text)
        config.TRIGGER_PRICE_CHANGE_PERCENT = new_value
        await message.answer(
            f"✅ Price change threshold set to: {new_value}%" if lang == 'en'
            else f"✅ Порог изменения цены установлен: {new_value}%"
        )
    except ValueError:
        await message.answer(
            "❌ Please enter a number." if lang == 'en'
            else "❌ Пожалуйста, введите число."
        )
    finally:
        await state.clear()

@router.callback_query(F.data == "admin_backtest")
async def admin_backtest(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await callback.message.edit_text(
        "Running backtest for last 30 days... (this may take a moment)" if lang == 'en'
        else "Запуск бэктеста за последние 30 дней... (это может занять некоторое время)"
    )
    stats = await trigger_detector.analyze_historical_news(days=30)
    # Получить историю цен BTC (опционально)
    btc_price_info = "N/A"
    # Можно через cryptorank.get_sparkline, но для простоты опустим
    text = (
        f"📊 <b>Backtest Results (30 days)</b>\n\n"
        f"Total news analyzed: {stats['total_analyzed']}\n"
        f"Triggered events: {stats['triggered']}\n"
        f"Accuracy: {stats['accuracy']:.1f}%\n\n"
        f"<b>Breakdown by coin:</b>\n" +
        "\n".join([f"• {coin}: {count}" for coin, count in stats['by_coin'].items()])
        if lang == 'en' else
        f"📊 <b>Результаты бэктеста (30 дней)</b>\n\n"
        f"Всего новостей: {stats['total_analyzed']}\n"
        f"Триггерных событий: {stats['triggered']}\n"
        f"Точность: {stats['accuracy']:.1f}%\n\n"
        f"<b>По монетам:</b>\n" +
        "\n".join([f"• {coin}: {count}" for coin, count in stats['by_coin'].items()])
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML)
    await callback.answer()

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await callback.message.edit_text(
        "Enter message to broadcast to all users:" if lang == 'en'
        else "Введите сообщение для рассылки всем пользователям:"
    )
    await state.set_state(AdminSettings.waiting_for_broadcast)
    await callback.answer()

@router.message(AdminSettings.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    from bot import bot
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    async with async_session() as session:
        users = await session.execute(select(User.telegram_id))
        user_ids = [row[0] for row in users]
    text = message.text
    sent = 0
    for uid in user_ids:
        try:
            await bot.send_message(
                uid,
                f"📢 <b>Announcement:</b>\n{escape_html(text)}\n\n<b>#BitcoinBastion</b>" if lang == 'en'
                else f"📢 <b>Объявление:</b>\n{escape_html(text)}\n\n<b>#BitcoinBastion</b>",
                parse_mode='HTML'
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Failed to send to {uid}: {e}")
    await message.answer(
        f"✅ Broadcast completed. Sent to {sent} users." if lang == 'en'
        else f"✅ Рассылка завершена. Отправлено {sent} пользователям."
    )
    await state.clear()
