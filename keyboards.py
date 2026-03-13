from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import User
from config import WEBAPP_URL

def reaction_keyboard(news_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👍", callback_data=f"react_like_{news_id}")
    builder.button(text="👎", callback_data=f"react_dislike_{news_id}")
    builder.button(text="🔥", callback_data=f"react_fire_{news_id}")
    builder.adjust(3)
    return builder.as_markup()

def main_menu_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if language == 'en':
        builder.row(
            InlineKeyboardButton(text="💰 BTC", callback_data="menu_btc"),
            InlineKeyboardButton(text="🐋 Whales", callback_data="menu_whales"),
            InlineKeyboardButton(text="💥 Liquids", callback_data="menu_liquidations")
        )
        builder.row(
            InlineKeyboardButton(text="📰 News", callback_data="menu_latest"),
            InlineKeyboardButton(text="🤖 AI", callback_data="menu_ai"),
            InlineKeyboardButton(text="🌍 Intl", callback_data="menu_international")
        )
        builder.row(
            InlineKeyboardButton(text="📊 Market", callback_data="menu_market"),
            InlineKeyboardButton(text="🔬 Research", callback_data="menu_research"),
            InlineKeyboardButton(text="⚙️ Settings", callback_data="menu_settings")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="💰 BTC", callback_data="menu_btc"),
            InlineKeyboardButton(text="🐋 Киты", callback_data="menu_whales"),
            InlineKeyboardButton(text="💥 Ликвидации", callback_data="menu_liquidations")
        )
        builder.row(
            InlineKeyboardButton(text="📰 Новости", callback_data="menu_latest"),
            InlineKeyboardButton(text="🤖 ИИ", callback_data="menu_ai"),
            InlineKeyboardButton(text="🌍 Мир", callback_data="menu_international")
        )
        builder.row(
            InlineKeyboardButton(text="📊 Рынок", callback_data="menu_market"),
            InlineKeyboardButton(text="🔬 Исслед", callback_data="menu_research"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings")
        )
    # Кнопка Web App
    builder.row(InlineKeyboardButton(
        text="📊 Dashboard" if language == 'en' else "📊 Дашборд",
        web_app=WebAppInfo(url=WEBAPP_URL)
    ))
    return builder.as_markup()

def subscription_keyboard(user: User, language: str = 'en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if language == 'en':
        builder.row(InlineKeyboardButton(
            text=f"{'✅' if user.subscribed_whales else '❌'} Whales",
            callback_data="sub_whales"
        ))
        builder.row(InlineKeyboardButton(
            text=f"{'✅' if user.subscribed_liquidations else '❌'} Liquidations",
            callback_data="sub_liquidations"
        ))
        builder.row(InlineKeyboardButton(
            text=f"{'✅' if user.subscribed_triggered else '❌'} Triggered News",
            callback_data="sub_triggered"
        ))
        builder.row(InlineKeyboardButton(
            text=f"{'✅' if user.subscribed_historical else '❌'} Historical",
            callback_data="sub_historical"
        ))
        builder.row(InlineKeyboardButton(
            text=f"{'✅' if user.subscribed_international else '❌'} International",
            callback_data="sub_international"
        ))
        builder.row(InlineKeyboardButton(
            text=f"{'✅' if user.subscribed_ai_alerts else '❌'} AI Alerts",
            callback_data="sub_ai"
        ))
    else:
        builder.row(InlineKeyboardButton(
            text=f"{'✅' if user.subscribed_whales else '❌'} Киты",
            callback_data="sub_whales"
        ))
        builder.row(InlineKeyboardButton(
            text=f"{'✅' if user.subscribed_liquidations else '❌'} Ликвидации",
            callback_data="sub_liquidations"
        ))
        builder.row(InlineKeyboardButton(
            text=f"{'✅' if user.subscribed_triggered else '❌'} Триггерные",
            callback_data="sub_triggered"
        ))
        builder.row(InlineKeyboardButton(
            text=f"{'✅' if user.subscribed_historical else '❌'} Архив",
            callback_data="sub_historical"
        ))
        builder.row(InlineKeyboardButton(
            text=f"{'✅' if user.subscribed_international else '❌'} Мировые",
            callback_data="sub_international"
        ))
        builder.row(InlineKeyboardButton(
            text=f"{'✅' if user.subscribed_ai_alerts else '❌'} AI оповещения",
            callback_data="sub_ai"
        ))
    return builder.as_markup()

def language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
    )
    return builder.as_markup()

def ai_menu_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if language == 'en':
        builder.row(
            InlineKeyboardButton(text="🤖 Ask", callback_data="ai_ask"),
            InlineKeyboardButton(text="📝 Summarize", callback_data="ai_summarize")
        )
        builder.row(
            InlineKeyboardButton(text="🔍 FactCheck", callback_data="ai_factcheck"),
            InlineKeyboardButton(text="🔬 Entities", callback_data="ai_entities")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="🤖 Спросить", callback_data="ai_ask"),
            InlineKeyboardButton(text="📝 Саммари", callback_data="ai_summarize")
        )
        builder.row(
            InlineKeyboardButton(text="🔍 Фактчек", callback_data="ai_factcheck"),
            InlineKeyboardButton(text="🔬 Сущности", callback_data="ai_entities")
        )
    builder.row(InlineKeyboardButton(
        text="🔙 Back" if language == 'en' else "🔙 Назад",
        callback_data="menu_main"
    ))
    return builder.as_markup()

def market_menu_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if language == 'en':
        builder.row(
            InlineKeyboardButton(text="📈 Gainers", callback_data="market_gainers"),
            InlineKeyboardButton(text="📉 Losers", callback_data="market_losers")
        )
        builder.row(
            InlineKeyboardButton(text="🔥 Heatmap", callback_data="market_heatmap"),
            InlineKeyboardButton(text="📊 Options", callback_data="market_options")
        )
        builder.row(
            InlineKeyboardButton(text="📚 OrderBook", callback_data="market_orderbook"),
            InlineKeyboardButton(text="😨 Fear&Greed", callback_data="market_fear_greed")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="📈 Рост", callback_data="market_gainers"),
            InlineKeyboardButton(text="📉 Падение", callback_data="market_losers")
        )
        builder.row(
            InlineKeyboardButton(text="🔥 Тепло", callback_data="market_heatmap"),
            InlineKeyboardButton(text="📊 Опционы", callback_data="market_options")
        )
        builder.row(
            InlineKeyboardButton(text="📚 Стакан", callback_data="market_orderbook"),
            InlineKeyboardButton(text="😨 Страх/Жадность", callback_data="market_fear_greed")
        )
    builder.row(InlineKeyboardButton(
        text="🔙 Back" if language == 'en' else "🔙 Назад",
        callback_data="menu_main"
    ))
    return builder.as_markup()

def research_menu_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if language == 'en':
        builder.row(
            InlineKeyboardButton(text="🪙 Coin Info", callback_data="research_coin"),
            InlineKeyboardButton(text="📚 Historical", callback_data="research_historical")
        )
        builder.row(
            InlineKeyboardButton(text="📊 Correlation", callback_data="research_correlation"),
            InlineKeyboardButton(text="⚙️ Backtest", callback_data="research_backtest")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="🪙 Инфо о монете", callback_data="research_coin"),
            InlineKeyboardButton(text="📚 Архив", callback_data="research_historical")
        )
        builder.row(
            InlineKeyboardButton(text="📊 Корреляция", callback_data="research_correlation"),
            InlineKeyboardButton(text="⚙️ Бэктест", callback_data="research_backtest")
        )
    builder.row(InlineKeyboardButton(
        text="🔙 Back" if language == 'en' else "🔙 Назад",
        callback_data="menu_main"
    ))
    return builder.as_markup()

def admin_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if language == 'en':
        builder.row(
            InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton(text="⚙️ Trigger", callback_data="admin_settings")
        )
        builder.row(
            InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="📊 Backtest", callback_data="admin_backtest")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="⚙️ Триггер", callback_data="admin_settings")
        )
        builder.row(
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="📊 Бэктест", callback_data="admin_backtest")
        )
    return builder.as_markup()

def international_languages_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    languages = [
        ("🇰🇷 Korean", "ko"), ("🇨🇳 Chinese", "zh"), ("🇯🇵 Japanese", "ja"),
        ("🇪🇸 Spanish", "es"), ("🇩🇪 German", "de"), ("🇫🇷 French", "fr"),
        ("🇮🇹 Italian", "it"), ("🇷🇺 Russian", "ru"), ("🇧🇷 Portuguese", "pt"),
        ("🇹🇷 Turkish", "tr"), ("🇮🇳 Hindi", "hi"), ("🇮🇩 Indonesian", "id")
    ]
    for name, code in languages:
        builder.button(text=name, callback_data=f"intl_{code}")
    builder.adjust(3)
    return builder.as_markup()
