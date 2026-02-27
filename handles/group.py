from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from metrics import MetricsCollector

router = Router()
metrics = MetricsCollector()

@router.message(Command("btc"))
async def btc_group(message: Message):
    price_data = await metrics.get_btc_price_coindesk()
    if price_data:
        await message.reply(f"💰 BTC Price: ${price_data['price']:,.2f}")
    else:
        await message.reply("Не удалось получить цену.")

@router.message(Command("feargreed"))
async def feargreed_group(message: Message):
    fg = await metrics.get_fear_greed()
    if fg:
        await message.reply(f"😨 Fear & Greed Index: {fg['value']} - {fg['value_classification']}")
    else:
        await message.reply("Не удалось получить индекс.")
