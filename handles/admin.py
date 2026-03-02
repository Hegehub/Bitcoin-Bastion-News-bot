from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import func
from database import get_db, User, News
from config import CHANNEL_ID
import logging

router = Router()
logger = logging.getLogger(__name__)

class PostState(StatesGroup):
    waiting_for_text = State()

@router.message(Command("admin"))
async def admin_panel(message: Message, is_admin: bool):
    if not is_admin:
        await message.reply("Доступ запрещён.")
        return
    from keyboards import admin_keyboard
    await message.answer("Админ-панель:", reply_markup=admin_keyboard())

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        await callback.answer("Нет доступа")
        return
    async for session in get_db():
        total_users = await session.scalar(select(func.count(User.id)))
        total_news = await session.scalar(select(func.count(News.id)))
        matched_news = await session.scalar(select(func.count(News.id)).where(News.matched == True))
        text = f"📊 <b>Статистика бота:</b>\n\nПользователей: {total_users}\nНовостей в БД: {total_news}\nСовпадений (1ч): {matched_news}"
        await callback.message.edit_text(text, reply_markup=admin_keyboard())

@router.callback_query(F.data == "admin_post")
async def admin_post(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer("Нет доступа")
        return
    await callback.message.edit_text("Введите текст для публикации в канал:")
    await state.set_state(PostState.waiting_for_text)

@router.message(PostState.waiting_for_text)
async def post_to_channel(message: Message, state: FSMContext, bot):
    text = message.text
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=text)
        await message.answer("Сообщение отправлено в канал.")
    except Exception as e:
        logger.error(f"Failed to post to channel: {e}")
        await message.answer("Ошибка при отправке.")
    await state.clear()
