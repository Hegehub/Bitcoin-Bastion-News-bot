import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from services.api_client import api_client
from services.twitter_client import twitter_client
from services.nlp_service import nlp

app = FastAPI(title="Crypto News MCP Server")

class NewsRequest(BaseModel):
    coin: Optional[str] = "BTC"
    limit: int = 10
    include_twitter: bool = True

class NewsItem(BaseModel):
    source: str
    title: str
    url: str
    published_at: str
    sentiment: dict
    summary: Optional[str] = None

@app.on_event("startup")
async def startup():
    await api_client._get_session()
    # twitter_client не требует сессии

@app.on_event("shutdown")
async def shutdown():
    await api_client.close()

@app.post("/api/news", response_model=List[NewsItem])
async def get_news(request: NewsRequest):
    news_list = []

    # free-crypto-news
    api_news = await api_client.get_news_by_ticker(request.coin, limit=request.limit)
    if api_news:
        for news in api_news:
            sentiment = nlp.analyze(news['title'])[0]
            news_list.append(NewsItem(
                source=news.get('source', 'free-crypto-news'),
                title=news['title'],
                url=news['url'],
                published_at=news['published_at'],
                sentiment=sentiment,
                summary=news.get('summary')
            ))

    # Twitter
    if request.include_twitter and os.getenv("TWITTER_BEARER_TOKEN"):
        tweets = await twitter_client.search_tweets(request.coin, limit=5)
        for tweet in tweets:
            sentiment = nlp.analyze(tweet['text'])[0]
            news_list.append(NewsItem(
                source='Twitter',
                title=tweet['text'][:200],
                url=f"https://twitter.com/i/web/status/{tweet['id']}",
                published_at=tweet['created_at'],
                sentiment=sentiment
            ))

    news_list.sort(key=lambda x: x.published_at, reverse=True)
    return news_list[:request.limit]

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
