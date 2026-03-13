import pytest
from services.backtest_engine import backtest_engine
from database import async_session, News

@pytest.mark.asyncio
async def test_backtest():
    # Запускаем на маленьком интервале (1 день)
    results = await backtest_engine.run_backtest(days=1)
    assert 'total' in results
    assert 'accuracy' in results
    assert 'by_category' in results