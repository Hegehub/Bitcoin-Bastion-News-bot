import pytest
from services.breaking_news import BreakingNewsDetector
from redis_cache import redis_client

@pytest.mark.asyncio
async def test_breaking_news_detection():
    detector = BreakingNewsDetector(redis_client, window_minutes=5, threshold=2)

    news1 = {'title': 'Bitcoin ETF approved by SEC'}
    news2 = {'title': 'Bitcoin ETF approved by SEC (update)'}
    news3 = {'title': 'Breaking: Bitcoin ETF gets green light'}

    # Первая новость
    result = await detector.add_news(news1)
    assert result is False

    # Вторая похожая новость
    result = await detector.add_news(news2)
    assert result is True  # порог достигнут

    # Третья, непохожая
    result = await detector.add_news(news3)
    assert result is False  # другой хеш