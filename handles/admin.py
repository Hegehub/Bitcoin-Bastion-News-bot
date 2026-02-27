from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from keyboards import admin_keyboard
from database import get_db, User, News
from sqlalchemy import func

router = Router()

@router.message(Command("admin"))
async def admin_panel(message: Message, is_admin: bool):
    if not is_admin:
        await message.reply("Доступ запрещен.")
        return
    await message.answer("Админ-панель", reply_markup=admin_keyboard())

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    async for session in get_db():
        total_users = await session.scalar(select(func.count(User.id)))
        total_news = await session.scalar(select(func.count(News.id)))
        matched_news = await session.scalar(select(func.count(News.id)).where(News.matched == True))
        text = f"📊 Статистика:\nПользователей: {total_users}\nНовостей: {total_news}\nСовпадений: {matched_news}"
        await callback.message.edit_text(text)

@router.callback_query(F.data == "admin_post")
async def admin_post(callback: CallbackQuery):
    # Здесь можно реализовать диалог для отправки сообщения в канал
    await callback.message.answer("Введите текст для публикации в канал:")
    # Далее через FSM
