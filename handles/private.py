from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from database import get_db, User, News
from bibabot_client import BibabotAPIClient
from keyboards import main_menu_keyboard, subscription_keyboard, admin_keyboard
from redis_cache import get_cached_fear_greed, set_cached_fear_greed
import logging

router = Router()
client = BibabotAPIClient()
logger = logging.getLogger(__name__)

class AnalyzeState(StatesGroup):
    waiting_for_url = State()

class SearchState(StatesGroup):
    waiting_for_query = State()

@router.message(Command("start"))
async def cmd_start(message: Message, is_admin: bool):
    user_id = message.from_user.id
    async for session in get_db():
        user = await session.get(User, user_id)
        if not user:
            user = User(
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                is_admin=is_admin
            )
            session.add(user)
            await session.commit()
    await message.answer(
        "Добро пожаловать в Crypto Analytics Bot!\nВыберите действие:",
        reply_markup=main_menu_keyboard(is_admin)
    )

@router.callback_query(F.data == "latest")
async def latest_news(callback: CallbackQuery):
    news = await client.get_latest_news(limit=5)
    if not news:
        await callback.message.edit_text("Нет новостей.")
        return
    text = "📰 <b>Последние новости о Bitcoin:</b>\n\n"
    for article in news:
        text += f"• <a href='{article['url']}'>{article['title']}</a> ({article['source']})\n"
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard())

@router.callback_query(F.data == "btc")
async def btc_info(callback: CallbackQuery):
    # Получаем цену из кэша или напрямую
    price = await get_cached_price() or await client.get_btc_price_coindesk()
    fear_greed = await get_cached_fear_greed() or await client.get_fear_greed()
    dominance = await client.get_btc_dominance()

    text = f"💰 <b>Bitcoin (BTC)</b>\n"
    if price:
        text += f"Цена: ${price:,.0f}\n"
    if fear_greed:
        text += f"Страх и жадность: {fear_greed['value']} — {fear_greed['value_classification']}\n"
    if dominance:
        text += f"Доминация BTC: {dominance:.2f}%\n"
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard())

@router.callback_query(F.data == "feargreed")
async def fear_greed_cmd(callback: CallbackQuery):
    fg = await client.get_fear_greed()
    if fg:
        text = f"😨 <b>Индекс страха и жадности:</b>\nЗначение: {fg['value']}\nКлассификация: {fg['value_classification']}"
    else:
        text = "Не удалось получить данные."
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard())

@router.callback_query(F.data == "dominance")
async def dominance_cmd(callback: CallbackQuery):
    dom = await client.get_btc_dominance()
    if dom:
        text = f"📊 <b>Доминация Bitcoin:</b> {dom:.2f}%"
    else:
        text = "Не удалось получить данные."
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard())

@router.callback_query(F.data == "liquidations")
async def liquidations_cmd(callback: CallbackQuery):
    liqs = await client.get_liquidations()
    if liqs:
        text = "💧 <b>Последние ликвидации:</b>\n"
        for liq in liqs[:5]:
            text += f"• {liq['amount_usd']} USD ({liq['symbol']}) — {liq['side']}\n"
    else:
        text = "Нет данных о ликвидациях."
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard())

@router.callback_query(F.data == "whales")
async def whales_cmd(callback: CallbackQuery):
    whales = await client.get_whales()
    if whales:
        text = "🐋 <b>Китовые транзакции:</b>\n"
        for w in whales[:5]:
            text += f"• {w['amount_usd']} USD ({w['symbol']}) — {w.get('exchange', 'N/A')}\n"
    else:
        text = "Нет данных о китах."
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard())

@router.callback_query(F.data == "analyze")
async def analyze_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Отправьте ссылку на новость для анализа:")
    await state.set_state(AnalyzeState.waiting_for_url)

@router.message(AnalyzeState.waiting_for_url)
async def analyze_url(message: Message, state: FSMContext):
    url = message.text.strip()
    await message.answer("Анализирую...")
    sentiment = await client.get_sentiment(url)
    summary = await client.summarize(url, style="paragraph")
    if sentiment or summary:
        text = ""
        if sentiment:
            text += f"<b>Тональность:</b> {sentiment['label']} ({sentiment['score']:.2f})\n"
        if summary:
            text += f"<b>Кратко:</b> {summary}\n"
        await message.answer(text)
    else:
        await message.answer("Не удалось проанализировать новость.")
    await state.clear()

@router.callback_query(F.data == "search")
async def search_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите поисковый запрос:")
    await state.set_state(SearchState.waiting_for_query)

@router.message(SearchState.waiting_for_query)
async def search_results(message: Message, state: FSMContext):
    query = message.text.strip()
    await message.answer("Ищу...")
    news = await client.search_news(query, limit=5)
    if news:
        text = f"🔍 <b>Результаты поиска по запросу '{query}':</b>\n\n"
        for article in news:
            text += f"• <a href='{article['url']}'>{article['title']}</a> ({article['source']})\n"
        await message.answer(text)
    else:
        await message.answer("Ничего не найдено.")
    await state.clear()

@router.callback_query(F.data == "subscriptions")
async def subscriptions_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Управление подписками:",
        reply_markup=subscription_keyboard()
    )

@router.callback_query(F.data.startswith("sub_"))
async def toggle_subscription(callback: CallbackQuery):
    sub_type = callback.data.split("_")[1]  # whales, liquidations, news
    user_id = callback.from_user.id
    async for session in get_db():
        user = await session.get(User, user_id)
        if user:
            if sub_type == "whales":
                user.subscribed_whales = not user.subscribed_whales
                status = "включена" if user.subscribed_whales else "отключена"
            elif sub_type == "liquidations":
                user.subscribed_liquidations = not user.subscribed_liquidations
                status = "включена" if user.subscribed_liquidations else "отключена"
            elif sub_type == "news":
                user.subscribed_high_sentiment = not user.subscribed_high_sentiment
                status = "включена" if user.subscribed_high_sentiment else "отключена"
            await session.commit()
            await callback.answer(f"Подписка {status}", show_alert=True)
        else:
            await callback.answer("Пользователь не найден", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=subscription_keyboard())

@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery, is_admin: bool):
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=main_menu_keyboard(is_admin)
    )
