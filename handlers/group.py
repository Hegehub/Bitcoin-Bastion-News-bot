from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from services.api_client import api_client
from config import GROUP_CHAT_ID
from keyboards import reaction_keyboard
from utils import escape_html
import logging
import asyncio

router = Router()
logger = logging.getLogger(__name__)

async def publish_all_news_to_group(bot):
    if not GROUP_CHAT_ID:
        return
    news_list = await api_client.get_latest_news(limit=3)
    if not news_list:
        return
    for news in news_list:
        title = escape_html(news['title'])
        time_ago = escape_html(news.get('time_ago', 'just now'))
        summary = escape_html(news.get('summary', ''))
        url = escape_html(news['url'])
        source = escape_html(news.get('source', 'unknown'))
        tickers = ','.join(news.get('tickers', ['BTC']))
        news_id = hash(url) % 1000000
        text = (
            f"📰 <b>{title}</b>\n"
            f"<i>{source} • {time_ago}</i>\n\n"
            f"<blockquote>{summary}</blockquote>\n\n"
            f"🔗 <a href='{url}'>Read</a>  <code>#{tickers}</code>  <b>#BitcoinBastion</b>"
        )
        try:
            await bot.send_message(
                GROUP_CHAT_ID,
                text,
                parse_mode='HTML',
                disable_web_page_preview=True,
                reply_markup=reaction_keyboard(news_id)
            )
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Failed to send news to group: {e}")

@router.message(Command("latest_group"))
async def cmd_latest_group(message: Message):
    if str(message.chat.id) != str(GROUP_CHAT_ID):
        return
    news_list = await api_client.get_latest_news(limit=5)
    if not news_list:
        await message.answer("No news.")
        return
    for news in news_list:
        title = escape_html(news['title'])
        url = escape_html(news['url'])
        tickers = ','.join(news.get('tickers', ['BTC']))
        text = f"📰 <b>{title}</b>\n🔗 <a href='{url}'>Read</a>  <code>#{tickers}</code>  <b>#BitcoinBastion</b>"
        await message.answer(text, parse_mode='HTML', disable_web_page_preview=True)
        await asyncio.sleep(1)