import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from services.ml_trainer import ml_trainer
from services.entity_service import entity_service
from services.price_categories import PriceCategorizer

logger = logging.getLogger(__name__)

class BacktestEngine:
    def __init__(self):
        self.categorizer = PriceCategorizer()

    async def run_backtest(self, days: int = 30, use_ml: bool = False) -> Dict:
        """
        Запускает бэктестинг на исторических данных из БД.
        Если use_ml=True, использует ML-модель для предсказаний.
        """
        from database import async_session, News
        from sqlalchemy import select

        async with async_session() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            result = await session.execute(
                select(News).where(News.published_at >= cutoff)
            )
            news_list = result.scalars().all()

        results = {
            'total': len(news_list),
            'with_price': 0,
            'correct_predictions': 0,
            'accuracy': 0.0,
            'by_category': {},
            'by_source': {},
            'ml_accuracy': 0.0
        }

        ml_correct = 0
        ml_total = 0

        for news in news_list:
            if news.price_change is None:
                continue
            results['with_price'] += 1
            actual_up = news.price_change > 0

            # Определяем категорию
            category = self.categorizer.get_category(news.price_change, {})
            results['by_category'][category] = results['by_category'].get(category, 0) + 1

            # Источник
            source = news.source or 'unknown'
            results['by_source'][source] = results['by_source'].get(source, 0) + 1

            # Проверяем наше предсказание (на основе тональности)
            if news.sentiment_score is not None:
                predicted_up = news.sentiment_score > 0.6  # порог
                if predicted_up == actual_up:
                    results['correct_predictions'] += 1

            # ML предсказание
            if use_ml and news.sentiment_score is not None:
                # Собираем признаки
                entities = entity_service.get_important_entities(news.title)
                features = {
                    'sentiment_score': news.sentiment_score,
                    'source_weight': 1.0,
                    'hour': news.published_at.hour,
                    'day_of_week': news.published_at.weekday(),
                    'has_etf': int('etf' in news.title.lower()),
                    'has_sec': int('sec' in news.title.lower()),
                    'has_halving': int('halving' in news.title.lower()),
                    'entity_count': len(entities)
                }
                proba = ml_trainer.predict_proba(features)
                ml_pred_up = proba > 0.5
                ml_total += 1
                if ml_pred_up == actual_up:
                    ml_correct += 1

        if results['with_price'] > 0:
            results['accuracy'] = (results['correct_predictions'] / results['with_price']) * 100

        if ml_total > 0:
            results['ml_accuracy'] = (ml_correct / ml_total) * 100

        return results

    async def backtest_on_csv(self, csv_path: str) -> Dict:
        """
        Запускает бэктестинг на предоставленном CSV-файле с историческими данными.
        Ожидается формат: timestamp, price, title, source, sentiment_score (опционально)
        """
        df = pd.read_csv(csv_path)
        # Здесь реализуется логика симуляции
        # ...
        return {'status': 'not implemented yet'}

backtest_engine = BacktestEngine()