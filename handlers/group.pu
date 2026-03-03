from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from services.api_client import CryptoNewsAPIClient
from redis_cache import get_cached, set_cache
from config import GROUP_CHAT_ID
import logging

router = Router()
api_client = CryptoNewsAPIClient()
logger = logging.getLogger(__name__)

# Эта функция будет вызываться планировщиком из scheduler.py
async def publish_all_news_to_group(bot):
    """Публикует последние 3 новости в группу (раз в 30-60 минут)."""
    if not GROUP_CHAT_ID:
        logger.warning("GROUP_CHAT_ID не задан, пропускаем публикацию в группу.")
        return
    
    # Получаем последние новости
    news_list = await api_client.get_latest_news(limit=3)
    if not news_list:
        return
    
    for news in news_list:
        text = (
            f"📰 **{news['title']}**\n"
            f"📅 {news['published_at']}\n"
            f"🔗 [Читать]({news['url']})"
        )
        try:
            await bot.send_message(GROUP_CHAT_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
            await asyncio.sleep(2) # Небольшая задержка между сообщениями
        except Exception as e:
            logger.error(f"Не удалось отправить новость в группу: {e}")

@router.message(Command("latest_group"))
async def cmd_latest_group(message: Message):
    """Команда для ручного получения последних новостей в группе."""
    if str(message.chat.id) != GROUP_CHAT_ID:
        return # Работаем только в заданной группе
        
    news_list = await api_client.get_latest_news(limit=5)
    if not news_list:
        await message.answer("Не удалось получить новости.")
        return
    
    for news in news_list:
        text = f"📰 **{news['title']}**\n🔗 [Ссылка]({news['url']})"
        await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)
        await asyncio.sleep(1)
