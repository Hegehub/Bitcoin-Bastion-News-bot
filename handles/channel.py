# В scheduler.py добавим:
async def publish_matched_news():
    # Выбираем последние 5 совпавших новостей, которые еще не опубликованы
    async for session in get_db():
        news_items = await session.execute(
            select(News).where(News.matched == True, News.published_in_channel == False).order_by(News.published_at.desc()).limit(5)
        )
        for news in news_items.scalars():
            # Формируем сообщение
            text = f"<b>{news.title}</b>\nИсточник: {news.source}\nТональность: {news.sentiment_label} ({news.sentiment_score:.2f})\nИзменение цены через 1ч: {((news.btc_price_1h_later - news.btc_price_at_publish)/news.btc_price_at_publish*100):.2f}%"
            await bot.send_message(chat_id=CHANNEL_ID, text=text)
            news.published_in_channel = True
            await session.commit()
