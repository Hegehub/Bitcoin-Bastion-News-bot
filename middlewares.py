from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from config import ADMIN_IDS
from database import async_session, User, select

class AdminCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        if user_id in ADMIN_IDS:
            data['is_admin'] = True
        else:
            async with async_session() as session:
                user = await session.scalar(select(User).where(User.telegram_id == user_id))
                data['is_admin'] = user.is_admin if user else False
        return await handler(event, data)