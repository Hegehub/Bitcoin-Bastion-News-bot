import asyncio
from types import SimpleNamespace

import scheduler


class _FakeExistsResult:
    def scalar_one_or_none(self):
        return None


class _FakeSession:
    def __init__(self, *, db_obj=None):
        self.db_obj = db_obj
        self.committed = False

    async def execute(self, _query):
        return _FakeExistsResult()

    async def get(self, _model, _id):
        return self.db_obj

    async def commit(self):
        self.committed = True


class _SessionFactory:
    def __init__(self, sessions):
        self._sessions = list(sessions)

    def __call__(self):
        session = self._sessions.pop(0)

        class _Ctx:
            async def __aenter__(self_nonlocal):
                return session

            async def __aexit__(self_nonlocal, exc_type, exc, tb):
                return False

        return _Ctx()


def test_scheduled_news_check_updates_attached_db_object(monkeypatch):
    news = {
        "url": "https://example.com/news",
        "title": "BTC jumps",
        "published_at": "2025-01-01T00:00:00Z",
    }
    detached_db_news = SimpleNamespace(id=42)
    attached_db_news = SimpleNamespace(triggered=False, price_change=None, sentiment_score=None)

    first_session = _FakeSession()
    second_session = _FakeSession(db_obj=attached_db_news)
    monkeypatch.setattr(scheduler, "async_session", _SessionFactory([first_session, second_session]))

    async def _latest_news(limit=20):
        return [news]

    async def _add_news_to_db(_news):
        return detached_db_news

    async def _check_if_triggered(_news):
        return {"price_change": 3.5, "sentiment": {"score": 0.91}, "title": "BTC jumps", "url": "u"}

    published = []
    notified = []

    async def _publish(data):
        published.append(data)

    async def _notify(data):
        notified.append(data)

    monkeypatch.setattr(scheduler.api_client, "get_latest_news", _latest_news)
    monkeypatch.setattr(scheduler, "add_news_to_db", _add_news_to_db)
    monkeypatch.setattr(scheduler.trigger_detector, "check_if_triggered", _check_if_triggered)
    monkeypatch.setattr(scheduler, "publish_triggered_news_to_channel", _publish)
    monkeypatch.setattr(scheduler, "notify_subscribers", _notify)

    asyncio.run(scheduler.scheduled_news_check())

    assert attached_db_news.triggered is True
    assert attached_db_news.price_change == 3.5
    assert attached_db_news.sentiment_score == 0.91
    assert second_session.committed is True
    assert len(published) == 1
    assert len(notified) == 1
