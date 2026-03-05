from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import User

def main_menu_keyboard(language: str = 'en'):
    """Главное меню с кнопками"""
    builder = InlineKeyboardBuilder()
    
    # Рыночные данные
    builder.row(
        InlineKeyboardButton(text="💰 BTC" if language == 'en' else "💰 BTC", callback_data="menu_btc"),
        InlineKeyboardButton(text="🐋 Whales" if language == 'en' else "🐋 Киты", callback_data="menu_whales"),
        InlineKeyboardButton(text="💥 Liquids" if language == 'en' else "💥 Ликвидации", callback_data="menu_liquidations")
    )
    
    # Новости и AI
    builder.row(
        InlineKeyboardButton(text="📰 News" if language == 'en' else "📰 Новости", callback_data="menu_latest"),
        InlineKeyboardButton(text="🤖 AI" if language == 'en' else "🤖 ИИ", callback_data="menu_ai"),
        InlineKeyboardButton(text="🌍 Intl" if language == 'en' else "🌍 Мир", callback_data="menu_international")
    )
    
    # Расширенные функции
    builder.row(
        InlineKeyboardButton(text="📊 Market" if language == 'en' else "📊 Рынок", callback_data="menu_market"),
        InlineKeyboardButton(text="🔬 Research" if language == 'en' else "🔬 Исслед", callback_data="menu_research"),
        InlineKeyboardButton(text="⚙️ Settings" if language == 'en' else "⚙️ Настройки", callback_data="menu_settings")
    )
    
    return builder.as_markup()

def subscription_keyboard(user: User, language: str = 'en'):
    """Клавиатура для управления подписками"""
    builder = InlineKeyboardBuilder()
    
    texts = {
        'en': {
            'whales': '🐋 Whales',
            'liquidations': '💥 Liquidations',
            'triggered': '⚡ Triggered News',
            'historical': '📚 Historical',
            'international': '🌍 International',
            'ai_alerts': '🤖 AI Alerts'
        },
        'ru': {
            'whales': '🐋 Киты',
            'liquidations': '💥 Ликвидации',
            'triggered': '⚡ Триггерные',
            'historical': '📚 Архив',
            'international': '🌍 Мировые',
            'ai_alerts': '🤖 AI оповещения'
        }
    }
    
    t = texts.get(language, texts['en'])
    
    builder.row(InlineKeyboardButton(
        text=f"{'✅' if user.subscribed_whales else '❌'} {t['whales']}",
        callback_data="sub_whales"
    ))
    builder.row(InlineKeyboardButton(
        text=f"{'✅' if user.subscribed_liquidations else '❌'} {t['liquidations']}",
        callback_data="sub_liquidations"
    ))
    builder.row(InlineKeyboardButton(
        text=f"{'✅' if user.subscribed_triggered else '❌'} {t['triggered']}",
        callback_data="sub_triggered"
    ))
    builder.row(InlineKeyboardButton(
        text=f"{'✅' if user.subscribed_historical else '❌'} {t['historical']}",
        callback_data="sub_historical"
    ))
    builder.row(InlineKeyboardButton(
        text=f"{'✅' if user.subscribed_international else '❌'} {t['international']}",
        callback_data="sub_international"
    ))
    builder.row(InlineKeyboardButton(
        text=f"{'✅' if user.subscribed_ai_alerts else '❌'} {t['ai_alerts']}",
        callback_data="sub_ai"
    ))
    
    return builder.as_markup()

def language_keyboard():
    """Клавиатура выбора языка"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
    )
    return builder.as_markup()

def ai_menu_keyboard(language: str = 'en'):
    """Меню AI функций"""
    builder = InlineKeyboardBuilder()
    
    texts = {
        'en': ['Ask Question', 'Summarize', 'Fact Check', 'Extract Entities'],
        'ru': ['Задать вопрос', 'Саммари', 'Проверка фактов', 'Извлечь сущности']
    }
    
    t = texts.get(language, texts['en'])
    
    builder.row(
        InlineKeyboardButton(text=f"🤖 {t[0]}", callback_data="ai_ask"),
        InlineKeyboardButton(text=f"📝 {t[1]}", callback_data="ai_summarize")
    )
    builder.row(
        InlineKeyboardButton(text=f"🔍 {t[2]}", callback_data="ai_factcheck"),
        InlineKeyboardButton(text=f"🔬 {t[3]}", callback_data="ai_entities")
    )
    builder.row(InlineKeyboardButton(
        text="🔙 Back" if language == 'en' else "🔙 Назад", 
        callback_data="menu_main"
    ))
    
    return builder.as_markup()

def market_menu_keyboard(language: str = 'en'):
    """Меню рыночных данных"""
    builder = InlineKeyboardBuilder()
    
    texts = {
        'en': ['Gainers', 'Losers', 'Heatmap', 'Options', 'Order Book', 'Fear & Greed'],
        'ru': ['Рост', 'Падение', 'Тепловая карта', 'Опционы', 'Стакан', 'Страх/Жадность']
    }
    
    t = texts.get(language, texts['en'])
    
    builder.row(
        InlineKeyboardButton(text=f"📈 {t[0]}", callback_data="market_gainers"),
        InlineKeyboardButton(text=f"📉 {t[1]}", callback_data="market_losers")
    )
    builder.row(
        InlineKeyboardButton(text=f"🔥 {t[2]}", callback_data="market_heatmap"),
        InlineKeyboardButton(text=f"📊 {t[3]}", callback_data="market_options")
    )
    builder.row(
        InlineKeyboardButton(text=f"📚 {t[4]}", callback_data="market_orderbook"),
        InlineKeyboardButton(text=f"😨 {t[5]}", callback_data="market_fear_greed")
    )
    builder.row(InlineKeyboardButton(
        text="🔙 Back" if language == 'en' else "🔙 Назад", 
        callback_data="menu_main"
    ))
    
    return builder.as_markup()

def research_menu_keyboard(language: str = 'en'):
    """Меню исследовательских инструментов"""
    builder = InlineKeyboardBuilder()
    
    texts = {
        'en': ['Coin Info', 'Historical News', 'Correlation', 'Backtest'],
        'ru': ['Инфо о монете', 'Архив новостей', 'Корреляция', 'Бэктест']
    }
    
    t = texts.get(language, texts['en'])
    
    builder.row(
        InlineKeyboardButton(text=f"🪙 {t[0]}", callback_data="research_coin"),
        InlineKeyboardButton(text=f"📚 {t[1]}", callback_data="research_historical")
    )
    builder.row(
        InlineKeyboardButton(text=f"📊 {t[2]}", callback_data="research_correlation"),
        InlineKeyboardButton(text=f"⚙️ {t[3]}", callback_data="research_backtest")
    )
    builder.row(InlineKeyboardButton(
        text="🔙 Back" if language == 'en' else "🔙 Назад", 
        callback_data="menu_main"
    ))
    
    return builder.as_markup()

def admin_keyboard(language: str = 'en'):
    """Админская панель"""
    builder = InlineKeyboardBuilder()
    
    texts = {
        'en': ['📊 Stats', '⚙️ Trigger Settings', '📢 Broadcast', '📊 Backtest Results'],
        'ru': ['📊 Статистика', '⚙️ Настройки триггера', '📢 Рассылка', '📊 Результаты бэктеста']
    }
    
    t = texts.get(language, texts['en'])
    
    builder.row(
        InlineKeyboardButton(text=t[0], callback_data="admin_stats"),
        InlineKeyboardButton(text=t[1], callback_data="admin_settings")
    )
    builder.row(
        InlineKeyboardButton(text=t[2], callback_data="admin_broadcast"),
        InlineKeyboardButton(text=t[3], callback_data="admin_backtest")
    )
    
    return builder.as_markup()

def international_languages_keyboard():
    """Клавиатура выбора языка для международных новостей"""
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