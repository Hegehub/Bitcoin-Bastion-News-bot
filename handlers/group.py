from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
from services.api_client import api_client
from services.btc_service import top_btc_articles
from config import GROUP_CHAT_ID
import logging
import asyncio

router = Router()
logger = logging.getLogger(__name__)

async def publish_all_news_to_group(bot):
    """Публикует последние 3 новости в группу (вызывается из планировщика)."""
    if not GROUP_CHAT_ID:
        return
    news_list = await api_client.get_bitcoin_news(limit=8)
    news_list = top_btc_articles(news_list or [], limit=3)
    if not news_list:
        return
    for news in news_list:
        text = (
            f"📰 **{news['title']}**\n"
            f"📅 {news['published_at']}\n"
            f"🔗 [Читать]({news['url']})"
        )
        try:
            await bot.send_message(GROUP_CHAT_ID, text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Не удалось отправить новость в группу: {e}")

@router.message(Command("latest_group"))
async def cmd_latest_group(message: Message):
    """Ручная команда для получения последних новостей в группе."""
    if str(message.chat.id) != str(GROUP_CHAT_ID):
        return
    news_list = await api_client.get_bitcoin_news(limit=10)
    news_list = top_btc_articles(news_list or [], limit=5)
    if not news_list:
        await message.answer("Не удалось получить новости.")
        return
    for news in news_list:
        text = f"📰 **{news['title']}**\n🔗 [Ссылка]({news['url']})"
        await message.answer(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        await asyncio.sleep(1)