from __future__ import annotations

from typing import Dict, List

BTC_KEYWORDS = {
    "btc", "bitcoin", "satoshi", "lightning", "segwit", "ordinals", "mempool", "hashrate"
}


def _norm(value: str) -> str:
    return (value or "").strip().lower()


def is_btc_related(article: Dict) -> bool:
    tickers = [str(t).upper() for t in (article.get("tickers") or [])]
    if "BTC" in tickers:
        return True

    text_blob = " ".join(
        [
            _norm(article.get("title", "")),
            _norm(article.get("summary", "")),
            _norm(article.get("content", "")),
        ]
    )
    return any(k in text_blob for k in BTC_KEYWORDS)


def btc_relevance_score(article: Dict) -> int:
    score = 0
    tickers = [str(t).upper() for t in (article.get("tickers") or [])]
    if "BTC" in tickers:
        score += 5

    title = _norm(article.get("title", ""))
    summary = _norm(article.get("summary", ""))

    for kw in BTC_KEYWORDS:
        if kw in title:
            score += 2
        if kw in summary:
            score += 1

    # меньше шума от alt-only новостей
    if any(x in title for x in ["solana", "xrp", "dogecoin", "shib", "cardano"]):
        score -= 2

    return score


def top_btc_articles(articles: List[Dict], limit: int = 5) -> List[Dict]:
    filtered = [a for a in (articles or []) if is_btc_related(a)]
    filtered.sort(key=btc_relevance_score, reverse=True)
    return filtered[:limit]
