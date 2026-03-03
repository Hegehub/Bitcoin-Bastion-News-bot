from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def subscription_keyboard(user):
    """Клавиатура для управления подписками."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=f"{'✅' if user.subscribed_whales else '❌'} Киты",
        callback_data="sub_whales"
    ))
    builder.row(InlineKeyboardButton(
        text=f"{'✅' if user.subscribed_liquidations else '❌'} Ликвидации",
        callback_data="sub_liquidations"
    ))
    builder.row(InlineKeyboardButton(
        text=f"{'✅' if user.subscribed_triggered else '❌'} Триггерные новости",
        callback_data="sub_triggered"
    ))
    return builder.as_markup()

def admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="⚙️ Настройки триггера", callback_data="admin_settings")
    builder.button(text="📢 Отправить в канал", callback_data="admin_broadcast_channel")
    builder.button(text="📣 Отправить всем", callback_data="admin_broadcast_all")
    builder.adjust(2)
    return builder.as_markup()
