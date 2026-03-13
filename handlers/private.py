# ... (все импорты и предыдущий код) ...
from services.llm_service import llm
from services.price_categories import PriceCategorizer

# ... другие команды ...

@router.message(Command("ask"))
async def cmd_ask(message: Message, command: CommandObject, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    if not command.args:
        await state.set_state(AIStates.waiting_for_question)
        await message.answer(get_text("ask_prompt", lang))
        return
    # Сначала пробуем free-crypto-news API
    response = await api_client.ask_ai(command.args)
    if not response:
        response = await llm.ask(command.args)
    await message.answer(get_text("ask_response", lang, response=response), parse_mode=ParseMode.HTML)

@router.message(Command("backtest"))
async def cmd_backtest(message: Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    # Проверка прав администратора (пример)
    is_admin = user_id in ADMIN_IDS
    if not is_admin:
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.telegram_id == user_id))
            is_admin = user.is_admin if user else False
    if not is_admin:
        await message.answer("Access denied.")
        return

    await message.answer("Running backtest for last 30 days...")
    stats = await trigger_detector.analyze_historical_news(days=30)

    # Дополнительная статистика по категориям
    async with async_session() as session:
        cutoff = datetime.utcnow() - timedelta(days=30)
        result = await session.execute(
            select(News.price_change, News.sentiment_score).where(
                News.published_at >= cutoff,
                News.triggered == True
            )
        )
        rows = result.all()
    thresholds = await trigger_detector.get_thresholds()  # добавить метод в trigger_detector
    categories = {'extreme_bearish': 0, 'bearish': 0, 'bullish': 0, 'extreme_bullish': 0}
    for price_change, _ in rows:
        cat = PriceCategorizer.get_category(price_change, thresholds)
        categories[cat] += 1

    text = (
        f"📊 Backtest Results (30 days)\n\n"
        f"Total news analyzed: {stats['total_analyzed']}\n"
        f"Triggered events: {stats['triggered']}\n"
        f"Accuracy: {stats['accuracy']:.1f}%\n\n"
        f"Breakdown by coin:\n" +
        "\n".join([f"• {coin}: {count}" for coin, count in stats['by_coin'].items()]) +
        f"\n\nBreakdown by category:\n" +
        "\n".join([f"• {cat}: {count}" for cat, count in categories.items()])
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

@router.message(Command("backtest"))
async def cmd_backtest(message: Message):
    user_id = message.from_user.id
    lang = await get_user_language(user_id)

    # Проверка прав (только админы)
    is_admin = user_id in ADMIN_IDS
    if not is_admin:
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.telegram_id == user_id))
            is_admin = user.is_admin if user else False
    if not is_admin:
        await message.answer("Access denied.")
        return

    await message.answer("Running backtest for last 30 days... This may take a moment.")

    # Запускаем бэктестинг
    results = await backtest_engine.run_backtest(days=30, use_ml=True)

    text = (
        f"📊 Backtest Results (30 days)\n\n"
        f"Total news: {results['total']}\n"
        f"With price data: {results['with_price']}\n"
        f"Accuracy (sentiment): {results['accuracy']:.1f}%\n"
        f"ML Accuracy: {results.get('ml_accuracy', 0):.1f}%\n\n"
        f"Top categories:\n" +
        "\n".join([f"• {k}: {v}" for k, v in list(results['by_category'].items())[:5]]) +
        f"\n\nTop sources:\n" +
        "\n".join([f"• {k}: {v}" for k, v in list(results['by_source'].items())[:5]])
    )
    await message.answer(text, parse_mode=ParseMode.HTML)
