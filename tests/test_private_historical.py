import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import importlib

private = importlib.import_module("handlers.private")


class _FakeState:
    def __init__(self):
        self.clear = AsyncMock()


class _FakeMessage:
    def __init__(self, text):
        self.text = text
        self.from_user = SimpleNamespace(id=123)
        self.answer = AsyncMock()


def test_process_historical_ticker_empty_input_clears_state(monkeypatch):
    message = _FakeMessage(text="   ")
    state = _FakeState()

    monkeypatch.setattr(private, "get_user_language", AsyncMock(return_value="en"))
    monkeypatch.setattr(private, "get_text", lambda *_args, **_kwargs: "NO_DATA")

    asyncio.run(private.process_historical_ticker(message, state))

    message.answer.assert_awaited_once_with("NO_DATA")
    state.clear.assert_awaited_once()


def test_process_historical_ticker_sends_formatted_news(monkeypatch):
    message = _FakeMessage(text="btc")
    state = _FakeState()

    monkeypatch.setattr(private, "get_user_language", AsyncMock(return_value="en"))
    monkeypatch.setattr(private, "get_text", lambda *_args, **kwargs: f"HEADER {kwargs.get('ticker', '')}" if kwargs.get("ticker") else "NO_DATA")

    sample_news = [{
        "published_at": "2025-01-02T11:00:00Z",
        "url": "https://example.com/a",
        "title": "Some title",
    }]
    monkeypatch.setattr(private.api_client, "get_historical_archive", AsyncMock(return_value=sample_news))

    asyncio.run(private.process_historical_ticker(message, state))

    assert message.answer.await_count == 1
    args, kwargs = message.answer.await_args
    assert "HEADER BTC" in args[0]
    assert "Some title" in args[0]
    assert kwargs.get("disable_web_page_preview") is True
    state.clear.assert_awaited_once()
