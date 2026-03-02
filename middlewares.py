from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from database import get_db, User
from config import ADMIN_IDS

class AdminCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        # Проверяем, есть ли пользователь в списке ADMIN_IDS или в БД с флагом is_admin
        is_admin = user_id in ADMIN_IDS
        if not is_admin:
            async for session in get_db():
                user = await session.get(User, user_id)
                if user and user.is_admin:
                    is_admin = True
        data["is_admin"] = is_admin
        return await handler(event, data)
