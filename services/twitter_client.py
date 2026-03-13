import asyncio
import snscrape.modules.twitter as sntwitter
import tweepy
from typing import List, Dict, Optional
import logging
from datetime import datetime, timedelta
from config import TWITTER_BEARER_TOKEN
from redis_cache import get_cache, set_cache

logger = logging.getLogger(__name__)

class TwitterClient:
    def __init__(self):
        self.use_api = False
        if TWITTER_BEARER_TOKEN:
            try:
                self.client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)
                self.use_api = True
                logger.info("Twitter API client initialized")
            except Exception as e:
                logger.error(f"Failed to init Twitter API: {e}")

    async def search_tweets(self, query: str, limit: int = 10, hours_back: int = 6) -> List[Dict]:
        cache_key = f"twitter:{query}:{hours_back}"
        cached = await get_cache(cache_key)
        if cached:
            return cached

        tweets = []
        since = datetime.utcnow() - timedelta(hours=hours_back)

        if self.use_api:
            try:
                response = self.client.search_recent_tweets(
                    query=query,
                    max_results=min(limit, 100),
                    tweet_fields=['created_at', 'public_metrics']
                )
                if response.data:
                    for tweet in response.data:
                        tweets.append({
                            'id': tweet.id,
                            'text': tweet.text,
                            'created_at': tweet.created_at.isoformat(),
                            'likes': tweet.public_metrics['like_count'],
                            'retweets': tweet.public_metrics['retweet_count'],
                            'source': 'twitter'
                        })
            except Exception as e:
                logger.error(f"Tweepy error: {e}")
        else:
            try:
                scraper = sntwitter.TwitterSearchScraper(f"{query} since:{since.strftime('%Y-%m-%d')}")
                for i, tweet in enumerate(scraper.get_items()):
                    if i >= limit:
                        break
                    tweets.append({
                        'id': tweet.id,
                        'text': tweet.content,
                        'created_at': tweet.date.isoformat(),
                        'likes': tweet.likeCount,
                        'retweets': tweet.retweetCount,
                        'source': 'twitter'
                    })
            except Exception as e:
                logger.error(f"snscrape error: {e}")

        await set_cache(cache_key, tweets, ttl=600)
        return tweets

twitter_client = TwitterClient()
