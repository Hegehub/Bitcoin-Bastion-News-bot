from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from services.api_client import api_client
from services.price_history import price_history
from services.trigger_detector import trigger_detector
from services.btc_service import top_btc_articles, is_btc_related
from redis_cache import get_cache, set_cache
from database import add_user, async_session, User, select
from keyboards import (
    main_menu_keyboard, subscription_keyboard, language_keyboard,
    ai_menu_keyboard, market_menu_keyboard, research_menu_keyboard,
    international_languages_keyboard
)
import logging
from fluent.runtime import FluentLocalization, FluentResourceLoader
import os

router = Router()
logger = logging.getLogger(__name__)

# Система локализации
loader = FluentResourceLoader("locales/{locale}")
l10n = {}

async def get_user_language(user_id: int) -> str:
    """Получает язык пользователя из БД"""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        if user and hasattr(user, 'language'):
            return user.language
    return 'en'  # По умолчанию английский

async def set_user_language(user_id: int, language: str):
    """Устанавливает язык пользователя"""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        if user:
            user.language = language
        else:
            user = User(telegram_id=user_id, language=language)
            session.add(user)
        await session.commit()

def get_text(msg_id: str, lang: str = 'en', **kwargs) -> str:
    """Получает локализованный текст"""
    try:
        l10n = FluentLocalization([lang], ["messages.ftl"], loader)
        return l10n.format_value(msg_id, kwargs)
    except:
        # Fallback на английский
        l10n_en = FluentLocalization(['en'], ["messages.ftl"], loader)
        return l10n_en.format_value(msg_id, kwargs)

# FSM состояния для AI функций
class AIStates(StatesGroup):
    waiting_for_question = State()
    waiting_for_url = State()
    waiting_for_factcheck = State()
    waiting_for_entities = State()
    waiting_for_coin = State()
    waiting_for_historical_ticker = State()
    waiting_for_orderbook_pair = State()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    await add_user(user_id, message.from_user.username, message.from_user.first_name)
    lang = await get_user_language(user_id)
    
    text = get_text("start_message", lang)
    await message.answer(text, reply_markup=main_menu_keyboard(lang))

@router.message(Command("language"))
async def cmd_language(message: Message):
    await message.answer("Choose language / Выберите язык:", reply_markup=language_keyboard())

@router.callback_query(F.data.startswith("lang_"))
async def process_language(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    await set_user_language(callback.from_user.id, lang)
    
    text = get_text("language_selected", lang)
    await callback.message.edit_text(text)
    await callback.answer()

@router.message(Command("btc"))
async def cmd_btc(message: Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    cached = await get_cache("market_metrics")
    if cached:
        await message.answer(cached, parse_mode=ParseMode.MARKDOWN)
        return

    metrics = await api_client.get_market_metrics()
    if not metrics or not metrics.get('btc_price'):
        await message.answer(get_text("no_data", lang))
        return

    text = get_text("btc_price", lang,
                   price=metrics['btc_price'],
                   fear=metrics['fear_greed'],
                   fear_class=metrics['fear_greed_class'],
                   btc_dom=metrics['btc_dominance'],
                   eth_dom=metrics['eth_dominance'])
    
    await set_cache("market_metrics", text, ttl=300)
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

@router.message(Command("whales"))
async def cmd_whales(message: Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    whales = await api_client.get_whale_transactions(limit=3)
    if not whales:
        await message.answer(get_text("no_data", lang))
        return

    text = get_text("whales_title", lang)
    for tx in whales:
        text += get_text("whale_entry", lang,
                        amount=tx['amount'],
                        coin=tx['coin'],
                        value=tx['value_usd'],
                        from_addr=tx['from'][:6] + "...",
                        to_addr=tx['to'][:6] + "...",
                        url=tx['tx_url'])
    
    await message.answer(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

@router.message(Command("liquidations"))
async def cmd_liquidations(message: Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    liqs = await api_client.get_liquidations(limit=5)
    if not liqs:
        await message.answer(get_text("no_data", lang))
        return

    text = get_text("liquidations_title", lang)
    for liq in liqs:
        emoji = "🟢" if liq['side'] == 'long' else "🔴"
        text += get_text("liquidation_entry", lang,
                        emoji=emoji,
                        side=liq['side'].upper(),
                        amount=liq['amount_usd'],
                        pair=liq['pair'])
    
    await message.answer(text)

@router.message(Command("funding"))
async def cmd_funding(message: Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    rates = await api_client.get_funding_rates()
    if not rates:
        await message.answer(get_text("no_data", lang))
        return

    text = get_text("funding_title", lang)
    for rate in rates[:10]:
        emoji = "🟢" if rate['rate'] > 0 else "🔴" if rate['rate'] < 0 else "⚪"
        text += get_text("funding_entry", lang,
                        emoji=emoji,
                        pair=rate['pair'],
                        rate=round(rate['rate']*100, 4))
    
    await message.answer(text)

@router.message(Command("latest"))
async def cmd_latest(message: Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    news = await api_client.get_bitcoin_news(limit=10)
    news = top_btc_articles(news or [], limit=5)
    if not news:
        await message.answer(get_text("no_data", lang))
        return
    
    text = get_text("latest_news_title", lang)
    for item in news:
        text += get_text("news_entry", lang,
                        title=item['title'],
                        url=item['url'],
                        source=item['source'])
    
    await message.answer(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

@router.message(Command("historical"))
async def cmd_historical(message: Message, command: CommandObject):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    if not command.args:
        await message.answer("Usage: /historical BTC")
        return
    
    ticker = command.args.upper()
    if ticker != "BTC":
        await message.answer("BTC-only mode: use /historical BTC")
        return
    news = await api_client.get_historical_archive(ticker=ticker, limit=10)
    
    if not news:
        await message.answer(get_text("no_data", lang))
        return
    
    text = get_text("historical_news_title", lang, ticker=ticker)
    for item in news:
        text += f"• {item['published_at'][:10]}: [{item['title']}]({item['url']})\n"
    
    await message.answer(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

@router.message(Command("international"))
async def cmd_international(message: Message, command: CommandObject):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    if not command.args:
        # Показываем клавиатуру выбора языка
        await message.answer("Select language:", reply_markup=international_languages_keyboard())
        return
    
    lang_code = command.args.lower()
    news = await api_client.get_international_news(language=lang_code, limit=5)
    
    if not news:
        await message.answer(get_text("no_data", lang))
        return
    
    lang_names = {'ko': 'Korean', 'zh': 'Chinese', 'ja': 'Japanese', 'es': 'Spanish'}
    lang_name = lang_names.get(lang_code, lang_code)
    
    text = get_text("international_news_title", lang, lang=lang_name)
    for item in news:
        text += f"• [{item['title']}]({item['url']}) — {item['source']}\n"
        if item.get('translated_title'):
            text += f"  🔄 {item['translated_title']}\n"
    
    await message.answer(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

@router.message(Command("ask"))
async def cmd_ask(message: Message, command: CommandObject, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    if not command.args:
        await state.set_state(AIStates.waiting_for_question)
        await message.answer("What would you like to ask about crypto?" if lang == 'en' 
                            else "Что вы хотите спросить о криптовалютах?")
        return
    
    response = await api_client.ask_ai(command.args)
    if not response:
        await message.answer(get_text("no_data", lang))
        return
    
    text = get_text("ask_response", lang, response=response)
    await message.answer(text)

@router.message(AIStates.waiting_for_question)
async def process_ask(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    response = await api_client.ask_ai(message.text)
    if not response:
        await message.answer(get_text("no_data", lang))
    else:
        text = get_text("ask_response", lang, response=response)
        await message.answer(text)
    
    await state.clear()

@router.message(Command("summarize"))
async def cmd_summarize(message: Message, command: CommandObject, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    if not command.args:
        await state.set_state(AIStates.waiting_for_url)
        await message.answer("Send me a news URL to summarize:" if lang == 'en' 
                            else "Отправьте URL новости для краткого содержания:")
        return
    
    summary = await api_client.summarize_news(command.args)
    if not summary:
        await message.answer(get_text("no_data", lang))
        return
    
    text = get_text("summary_result", lang, summary=summary)
    await message.answer(text)

@router.message(AIStates.waiting_for_url)
async def process_summarize(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    summary = await api_client.summarize_news(message.text)
    if not summary:
        await message.answer(get_text("no_data", lang))
    else:
        text = get_text("summary_result", lang, summary=summary)
        await message.answer(text)
    
    await state.clear()

@router.message(Command("factcheck"))
async def cmd_factcheck(message: Message, command: CommandObject, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    if not command.args:
        await state.set_state(AIStates.waiting_for_factcheck)
        await message.answer("Send me a claim to fact-check:" if lang == 'en' 
                            else "Отправьте утверждение для проверки фактов:")
        return
    
    result = await api_client.fact_check(command.args)
    if not result:
        await message.answer(get_text("no_data", lang))
        return
    
    text = get_text("factcheck_result", lang, result=result.get('result', 'No result'))
    await message.answer(text)

@router.message(AIStates.waiting_for_factcheck)
async def process_factcheck(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    result = await api_client.fact_check(message.text)
    if not result:
        await message.answer(get_text("no_data", lang))
    else:
        text = get_text("factcheck_result", lang, result=result.get('result', 'No result'))
        await message.answer(text)
    
    await state.clear()

@router.message(Command("entities"))
async def cmd_entities(message: Message, command: CommandObject, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    if not command.args:
        await state.set_state(AIStates.waiting_for_entities)
        await message.answer("Send me text to extract entities from:" if lang == 'en' 
                            else "Отправьте текст для извлечения сущностей:")
        return
    
    entities = await api_client.extract_entities(command.args)
    if not entities:
        await message.answer(get_text("no_data", lang))
        return
    
    text = get_text("entities_result", lang, entities=str(entities))
    await message.answer(text)

@router.message(AIStates.waiting_for_entities)
async def process_entities(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    entities = await api_client.extract_entities(message.text)
    if not entities:
        await message.answer(get_text("no_data", lang))
    else:
        text = get_text("entities_result", lang, entities=str(entities))
        await message.answer(text)
    
    await state.clear()

@router.message(Command("gainers"))
async def cmd_gainers(message: Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    movers = await api_client.get_market_movers(type='gainers', limit=10)
    if not movers:
        await message.answer(get_text("no_data", lang))
        return
    
    text = get_text("movers_title", lang, type='Gainers')
    for item in movers:
        text += get_text("mover_entry", lang,
                        emoji="📈",
                        symbol=item['symbol'],
                        change=item['price_change_percentage_24h'],
                        price=item['current_price'])
    
    await message.answer(text)

@router.message(Command("losers"))
async def cmd_losers(message: Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    movers = await api_client.get_market_movers(type='losers', limit=10)
    if not movers:
        await message.answer(get_text("no_data", lang))
        return
    
    text = get_text("movers_title", lang, type='Losers')
    for item in movers:
        text += get_text("mover_entry", lang,
                        emoji="📉",
                        symbol=item['symbol'],
                        change=item['price_change_percentage_24h'],
                        price=item['current_price'])
    
    await message.answer(text)

@router.message(Command("coin"))
async def cmd_coin(message: Message, command: CommandObject, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    if not command.args:
        await state.set_state(AIStates.waiting_for_coin)
        await message.answer("BTC-only mode. Type: bitcoin" if lang == 'en' else "Режим только BTC. Введите: bitcoin")
        return
    
    coin_id = command.args.lower().strip()
    if coin_id != "bitcoin":
        await message.answer("BTC-only mode: /coin bitcoin")
        return
    coin_data = await api_client.get_coin_details(coin_id)
    
    if not coin_data:
        await message.answer(get_text("no_data", lang))
        return
    
    text = get_text("coin_info", lang,
                   name=coin_data.get('name', 'Unknown'),
                   symbol=coin_data.get('symbol', '').upper(),
                   price=coin_data.get('market_data', {}).get('current_price', {}).get('usd', 0),
                   market_cap=coin_data.get('market_data', {}).get('market_cap', {}).get('usd', 0),
                   volume=coin_data.get('market_data', {}).get('total_volume', {}).get('usd', 0),
                   circulating_supply=coin_data.get('market_data', {}).get('circulating_supply', 0),
                   rank=coin_data.get('market_cap_rank', 0),
                   description=coin_data.get('description', {}).get('en', '')[:200] + '...')
    
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

@router.message(AIStates.waiting_for_coin)
async def process_coin(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    coin_id = message.text.lower().strip()
    if coin_id != "bitcoin":
        await message.answer("BTC-only mode: bitcoin")
        await state.clear()
        return
    coin_data = await api_client.get_coin_details(coin_id)
    
    if not coin_data:
        await message.answer(get_text("no_data", lang))
    else:
        text = get_text("coin_info", lang,
                       name=coin_data.get('name', 'Unknown'),
                       symbol=coin_data.get('symbol', '').upper(),
                       price=coin_data.get('market_data', {}).get('current_price', {}).get('usd', 0),
                       market_cap=coin_data.get('market_data', {}).get('market_cap', {}).get('usd', 0),
                       volume=coin_data.get('market_data', {}).get('total_volume', {}).get('usd', 0),
                       circulating_supply=coin_data.get('market_data', {}).get('circulating_supply', 0),
                       rank=coin_data.get('market_cap_rank', 0),
                       description=coin_data.get('description', {}).get('en', '')[:200] + '...')
        await message.answer(text, parse_mode=ParseMode.MARKDOWN)
    
    await state.clear()

@router.message(Command("heatmap"))
async def cmd_heatmap(message: Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    heatmap = await api_client.get_market_heatmap()
    if not heatmap:
        await message.answer(get_text("no_data", lang))
        return
    
    text = get_text("heatmap_title", lang)
    # Здесь можно добавить генерацию изображения тепловой карты
    # Пока просто текстовое описание
    await message.answer(text)

@router.message(Command("options"))
async def cmd_options(message: Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    options = await api_client.get_options_data()
    if not options:
        await message.answer(get_text("no_data", lang))
        return
    
    text = get_text("options_title", lang, data=str(options)[:500])
    await message.answer(text)

@router.message(Command("orderbook"))
async def cmd_orderbook(message: Message, command: CommandObject, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    if not command.args:
        await state.set_state(AIStates.waiting_for_orderbook_pair)
        await message.answer("Enter trading pair (e.g., BTC/USD):" if lang == 'en' 
                            else "Введите торговую пару (например: BTC/USD):")
        return
    
    pair = command.args.upper()
    orderbook = await api_client.get_orderbook(pair)
    
    if not orderbook:
        await message.answer(get_text("no_data", lang))
        return
    
    bids = "\n".join([f"{b[0]} @ {b[1]}" for b in orderbook.get('bids', [])[:5]])
    asks = "\n".join([f"{a[0]} @ {a[1]}" for a in orderbook.get('asks', [])[:5]])
    
    text = get_text("orderbook_title", lang,
                   pair=pair,
                   bids=bids or 'None',
                   asks=asks or 'None')
    
    await message.answer(text)

@router.message(AIStates.waiting_for_orderbook_pair)
async def process_orderbook(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    pair = message.text.upper()
    orderbook = await api_client.get_orderbook(pair)
    
    if not orderbook:
        await message.answer(get_text("no_data", lang))
    else:
        bids = "\n".join([f"{b[0]} @ {b[1]}" for b in orderbook.get('bids', [])[:5]])
        asks = "\n".join([f"{a[0]} @ {a[1]}" for a in orderbook.get('asks', [])[:5]])
        
        text = get_text("orderbook_title", lang,
                       pair=pair,
                       bids=bids or 'None',
                       asks=asks or 'None')
        await message.answer(text)
    
    await state.clear()

@router.message(Command("feargreed"))
async def cmd_feargreed(message: Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    cached = await get_cache("fear_greed")
    if cached:
        await message.answer(cached)
        return
    
    fg = await api_client._make_request("/api/fear-greed")
    if not fg:
        await message.answer(get_text("no_data", lang))
        return
    
    text = get_text("feargreed", lang, value=fg['value'], classification=fg['classification'])
    await set_cache("fear_greed", text, ttl=600)
    await message.answer(text)

@router.message(Command("dominance"))
async def cmd_dominance(message: Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    cached = await get_cache("dominance")
    if cached:
        await message.answer(cached)
        return
    
    dom = await api_client._make_request("/api/dominance")
    if not dom:
        await message.answer(get_text("no_data", lang))
        return
    
    text = get_text("dominance", lang, btc=dom['btc_dominance'], eth=dom['eth_dominance'])
    await set_cache("dominance", text, ttl=600)
    await message.answer(text)

@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        if not user:
            user = User(telegram_id=user_id, language=lang)
            session.add(user)
            await session.commit()
        
        text = get_text("subscribe_menu", lang)
        await message.answer(text, reply_markup=subscription_keyboard(user, lang))

@router.callback_query(F.data.startswith("sub_"))
async def process_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    sub_type = callback.data.split("_")[1]
    
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        if user:
            if sub_type == "whales":
                user.subscribed_whales = not user.subscribed_whales
            elif sub_type == "liquidations":
                user.subscribed_liquidations = not user.subscribed_liquidations
            elif sub_type == "triggered":
                user.subscribed_triggered = not user.subscribed_triggered
            elif sub_type == "historical":
                user.subscribed_historical = not user.subscribed_historical
            elif sub_type == "international":
                user.subscribed_international = not user.subscribed_international
            elif sub_type == "ai":
                user.subscribed_ai_alerts = not user.subscribed_ai_alerts
            
            await session.commit()
            await callback.message.edit_reply_markup(
                reply_markup=subscription_keyboard(user, lang)
            )
    
    await callback.answer("Settings saved" if lang == 'en' else "Настройки сохранены")

# Обработчики меню
@router.callback_query(F.data == "menu_main")
async def menu_main(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await callback.message.edit_text(
        get_text("start_message", lang),
        reply_markup=main_menu_keyboard(lang)
    )
    await callback.answer()

@router.callback_query(F.data == "menu_btc")
async def menu_btc(callback: CallbackQuery):
    await cmd_btc(callback.message)
    await callback.answer()

@router.callback_query(F.data == "menu_whales")
async def menu_whales(callback: CallbackQuery):
    await cmd_whales(callback.message)
    await callback.answer()

@router.callback_query(F.data == "menu_liquidations")
async def menu_liquidations(callback: CallbackQuery):
    await cmd_liquidations(callback.message)
    await callback.answer()

@router.callback_query(F.data == "menu_latest")
async def menu_latest(callback: CallbackQuery):
    await cmd_latest(callback.message)
    await callback.answer()

@router.callback_query(F.data == "menu_ai")
async def menu_ai(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await callback.message.edit_text(
        "🤖 **AI Tools**" if lang == 'en' else "🤖 **AI Инструменты**",
        reply_markup=ai_menu_keyboard(lang),
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

@router.callback_query(F.data == "menu_international")
async def menu_international(callback: CallbackQuery):
    await callback.message.edit_text(
        "Select language for international news:",
        reply_markup=international_languages_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "menu_market")
async def menu_market(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await callback.message.edit_text(
        "📊 **Market Data**" if lang == 'en' else "📊 **Рыночные данные**",
        reply_markup=market_menu_keyboard(lang),
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

@router.callback_query(F.data == "menu_research")
async def menu_research(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await callback.message.edit_text(
        "🔬 **Research Tools**" if lang == 'en' else "🔬 **Исследования**",
        reply_markup=research_menu_keyboard(lang),
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

@router.callback_query(F.data == "menu_settings")
async def menu_settings(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await cmd_subscribe(callback.message)
    await callback.answer()

# Обработчики AI меню
@router.callback_query(F.data == "ai_ask")
async def ai_ask(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await state.set_state(AIStates.waiting_for_question)
    await callback.message.edit_text(
        "What would you like to ask about crypto?" if lang == 'en' 
        else "Что вы хотите спросить о криптовалютах?"
    )
    await callback.answer()

@router.callback_query(F.data == "ai_summarize")
async def ai_summarize(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await state.set_state(AIStates.waiting_for_url)
    await callback.message.edit_text(
        "Send me a news URL to summarize:" if lang == 'en' 
        else "Отправьте URL новости для краткого содержания:"
    )
    await callback.answer()

@router.callback_query(F.data == "ai_factcheck")
async def ai_factcheck(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await state.set_state(AIStates.waiting_for_factcheck)
    await callback.message.edit_text(
        "Send me a claim to fact-check:" if lang == 'en' 
        else "Отправьте утверждение для проверки фактов:"
    )
    await callback.answer()

@router.callback_query(F.data == "ai_entities")
async def ai_entities(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await state.set_state(AIStates.waiting_for_entities)
    await callback.message.edit_text(
        "Send me text to extract entities from:" if lang == 'en' 
        else "Отправьте текст для извлечения сущностей:"
    )
    await callback.answer()

# Обработчики рыночного меню
@router.callback_query(F.data == "market_gainers")
async def market_gainers(callback: CallbackQuery):
    await cmd_gainers(callback.message)
    await callback.answer()

@router.callback_query(F.data == "market_losers")
async def market_losers(callback: CallbackQuery):
    await cmd_losers(callback.message)
    await callback.answer()

@router.callback_query(F.data == "market_heatmap")
async def market_heatmap(callback: CallbackQuery):
    await cmd_heatmap(callback.message)
    await callback.answer()

@router.callback_query(F.data == "market_options")
async def market_options(callback: CallbackQuery):
    await cmd_options(callback.message)
    await callback.answer()

@router.callback_query(F.data == "market_orderbook")
async def market_orderbook(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await state.set_state(AIStates.waiting_for_orderbook_pair)
    await callback.message.edit_text(
        "Enter trading pair (e.g., BTC/USD):" if lang == 'en' 
        else "Введите торговую пару (например: BTC/USD):"
    )
    await callback.answer()

@router.callback_query(F.data == "market_fear_greed")
async def market_fear_greed(callback: CallbackQuery):
    await cmd_feargreed(callback.message)
    await callback.answer()

# Обработчики исследовательского меню
@router.callback_query(F.data == "research_coin")
async def research_coin(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await state.set_state(AIStates.waiting_for_coin)
    await callback.message.edit_text(
        "Enter coin name (e.g., bitcoin, ethereum):" if lang == 'en' 
        else "Введите название монеты (например: bitcoin, ethereum):"
    )
    await callback.answer()

@router.callback_query(F.data == "research_historical")
async def research_historical(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    await state.set_state(AIStates.waiting_for_historical_ticker)
    await callback.message.edit_text(
        "Enter ticker (e.g., BTC, ETH):" if lang == 'en' 
        else "Введите тикер (например: BTC, ETH):"
    )
    await callback.answer()

@router.message(AIStates.waiting_for_historical_ticker)
async def process_historical_ticker(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    
    ticker = message.text.upper()
    news = await api_client.get_historical_archive(ticker=ticker, limit=10)
    
    if not news:
        await message.answer(get_text("no_data", lang))
    else:
        text = get_text("historical_news_title", lang, ticker=ticker)
        for item in news:
            text += f"• {item['published_at'][:10]}: [{item['title']}]({item['url']})\n"
        await message.answer(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    
    await state.clear()

@router.callback_query(F.data.startswith("intl_"))
async def process_intl_language(callback: CallbackQuery):
    lang_code = callback.data.split("_")[1]
    user_id = callback.from_user.id
    lang = await get_user_language(user_id)
    
    news = await api_client.get_international_news(language=lang_code, limit=5)
    
    if not news:
        await callback.message.edit_text(get_text("no_data", lang))
        await callback.answer()
        return
    
    lang_names = {'ko': 'Korean', 'zh': 'Chinese', 'ja': 'Japanese', 'es': 'Spanish'}
    lang_name = lang_names.get(lang_code, lang_code)
    
    text = get_text("international_news_title", lang, lang=lang_name)
    for item in news:
        text += f"• [{item['title']}]({item['url']}) — {item['source']}\n"
        if item.get('translated_title'):
            text += f"  🔄 {item['translated_title']}\n"
    
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    await callback.answer()


@router.message(Command("breaking"))
async def cmd_breaking(message: Message):
    news = await api_client.get_breaking_news(limit=8)
    news = top_btc_articles(news or [], limit=5)
    if not news:
        await message.answer("No BTC breaking news right now.")
        return

    text = "🚨 <b>BTC Breaking</b>\n\n"
    for item in news:
        text += f"• <a href='{item.get('url')}'>{item.get('title')}</a>\n"
    await message.answer(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


@router.message(Command("digest"))
async def cmd_digest(message: Message):
    digest = await api_client.summarize_daily_digest()
    if not digest:
        await message.answer("Digest is unavailable now.")
        return
    await message.answer(f"🧾 <b>BTC Daily Digest</b>\n\n{digest}", parse_mode=ParseMode.HTML)


@router.message(Command("sentiment"))
async def cmd_sentiment(message: Message):
    data = await api_client.get_ai_sentiment(asset="BTC")
    if not data:
        await message.answer("Sentiment endpoint unavailable.")
        return

    label = data.get("label", "unknown")
    score = data.get("score", 0)
    await message.answer(f"🧠 BTC sentiment: <b>{label}</b> ({score:.2f})", parse_mode=ParseMode.HTML)


@router.message(Command("narratives"))
async def cmd_narratives(message: Message):
    items = await api_client.get_narratives(limit=5)
    if not items:
        await message.answer("Narratives unavailable.")
        return

    lines = []
    for item in items[:5]:
        if isinstance(item, dict):
            lines.append(f"• {item.get('name') or item.get('title') or str(item)}")
        else:
            lines.append(f"• {item}")
    await message.answer("📚 <b>BTC Narratives</b>\n\n" + "\n".join(lines), parse_mode=ParseMode.HTML)


@router.message(Command("anomalies"))
async def cmd_anomalies(message: Message):
    anomalies = await api_client.get_anomalies()
    if not anomalies:
        await message.answer("No BTC anomalies now.")
        return

    lines = []
    for a in anomalies[:5]:
        if isinstance(a, dict):
            title = a.get("title") or a.get("type") or "Anomaly"
            sev = a.get("severity", "n/a")
            lines.append(f"• {title} (severity: {sev})")
        else:
            lines.append(f"• {a}")
    await message.answer("⚠️ <b>BTC anomalies</b>\n\n" + "\n".join(lines), parse_mode=ParseMode.HTML)


@router.message(Command("credibility"))
async def cmd_credibility(message: Message):
    data = await api_client.get_credibility()
    if not data:
        await message.answer("Credibility data unavailable.")
        return

    score = data.get("score") or data.get("credibility_score") or "n/a"
    top_sources = data.get("top_sources") or []
    src_text = ", ".join(top_sources[:5]) if isinstance(top_sources, list) else str(top_sources)
    await message.answer(
        f"🛡 <b>BTC source credibility</b>\nScore: <b>{score}</b>\nTop: {src_text or 'n/a'}",
        parse_mode=ParseMode.HTML
    )


@router.inline_query()
async def inline_btc_news(inline_query: InlineQuery):
    query = (inline_query.query or "").lower().strip()
    if query and "btc" not in query and "bitcoin" not in query:
        await inline_query.answer([], cache_time=5, is_personal=True)
        return

    articles = await api_client.get_bitcoin_news(limit=8)
    articles = top_btc_articles(articles or [], limit=5)
    results = []

    for idx, item in enumerate(articles):
        title = item.get("title", "BTC news")
        url = item.get("url", "https://cryptocurrency.cv")
        source = item.get("source", "source")
        content = InputTextMessageContent(
            message_text=f"📰 <b>{title}</b>\n\n{source}\n<a href='{url}'>Read full article</a>",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )
        results.append(
            InlineQueryResultArticle(
                id=f"btc_{idx}_{hash(url)}",
                title=title[:64],
                description=source,
                input_message_content=content,
            )
        )

    await inline_query.answer(results, cache_time=30, is_personal=True)
