from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard(is_admin=False):
    keyboard = [
        [InlineKeyboardButton(text="📰 Latest News", callback_data="latest")],
        [InlineKeyboardButton(text="💰 BTC Price", callback_data="btc")],
        [InlineKeyboardButton(text="😨 Fear & Greed", callback_data="feargreed")],
        [InlineKeyboardButton(text="📊 Dominance", callback_data="dominance")],
        [InlineKeyboardButton(text="💧 Liquidations", callback_data="liquidations")],
        [InlineKeyboardButton(text="🐋 Whales", callback_data="whales")],
        [InlineKeyboardButton(text="🔍 Search", callback_data="search")],
        [InlineKeyboardButton(text="📝 Analyze URL", callback_data="analyze")],
        [InlineKeyboardButton(text="🔔 Subscriptions", callback_data="subscriptions")],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def subscription_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐋 Whales", callback_data="sub_whales")],
        [InlineKeyboardButton(text="💥 Liquidations", callback_data="sub_liquidations")],
        [InlineKeyboardButton(text="📰 High sentiment news", callback_data="sub_news")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="back_main")],
    ])

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Post to channel", callback_data="admin_post")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="back_main")],
    ])
