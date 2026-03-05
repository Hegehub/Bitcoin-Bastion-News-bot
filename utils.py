import html

def escape_html(text: str) -> str:
    """Экранирует спецсимволы для безопасного использования в HTML-разметке Telegram."""
    return html.escape(text, quote=False)