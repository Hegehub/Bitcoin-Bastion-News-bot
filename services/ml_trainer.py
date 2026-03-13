import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import lightgbm as lgb
import joblib
import os
from datetime import datetime, timedelta
from database import async_session, News
from sqlalchemy import select
import logging
from services.entity_service import entity_service
import asyncio

logger = logging.getLogger(__name__)

class MLTrainer:
    def __init__(self, model_path='models/price_movement_model.pkl'):
        self.model_path = model_path
        self.model = None
        self.feature_names = None

    async def load_data(self, days: int = 90) -> pd.DataFrame:
        """Загружает исторические данные из БД для обучения."""
        async with async_session() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            result = await session.execute(
                select(News).where(News.published_at >= cutoff)
            )
            news_list = result.scalars().all()

        data = []
        for news in news_list:
            # Извлекаем сущности
            entities = entity_service.get_important_entities(news.title)
            # Определяем целевой признак: 1 если цена выросла, 0 если упала
            target = 1 if news.price_change and news.price_change > 0 else 0 if news.price_change else -1
            if target == -1:
                continue
            row = {
                'sentiment_score': news.sentiment_score or 0.5,
                'source_weight': 1.0,  # можно заменить на вес из БД
                'hour': news.published_at.hour,
                'day_of_week': news.published_at.weekday(),
                'has_etf': int('etf' in news.title.lower()),
                'has_sec': int('sec' in news.title.lower()),
                'has_halving': int('halving' in news.title.lower()),
                'entity_count': len(entities),
                'target': target
            }
            data.append(row)

        df = pd.DataFrame(data)
        logger.info(f"Loaded {len(df)} samples for training")
        return df

    def train(self, df: pd.DataFrame):
        """Обучает модель LightGBM."""
        if len(df) < 100:
            logger.warning("Not enough data for training")
            return

        X = df.drop('target', axis=1)
        y = df['target']
        self.feature_names = X.columns.tolist()

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        train_data = lgb.Dataset(X_train, label=y_train)
        test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

        params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': 0
        }

        self.model = lgb.train(
            params,
            train_data,
            valid_sets=[test_data],
            num_boost_round=100,
            callbacks=[lgb.early_stopping(10)]
        )

        # Сохраняем модель
        os.makedirs('models', exist_ok=True)
        joblib.dump({'model': self.model, 'features': self.feature_names}, self.model_path)
        logger.info(f"Model saved to {self.model_path}")

        # Оценка на тестовой выборке
        y_pred = (self.model.predict(X_test) > 0.5).astype(int)
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        logger.info(f"Test metrics - Accuracy: {acc:.3f}, Precision: {prec:.3f}, Recall: {rec:.3f}, F1: {f1:.3f}")

    async def retrain_if_needed(self, force: bool = False):
        """Периодическое переобучение (вызывается из планировщика)."""
        df = await self.load_data()
        if len(df) > 200 or force:
            self.train(df)

    def load_model(self):
        """Загружает сохранённую модель."""
        if os.path.exists(self.model_path):
            data = joblib.load(self.model_path)
            self.model = data['model']
            self.feature_names = data['features']
            logger.info(f"Model loaded from {self.model_path}")
            return True
        return False

    def predict_proba(self, features: dict) -> float:
        """Предсказывает вероятность роста цены для одной новости."""
        if not self.model or not self.feature_names:
            return 0.5
        # Создаём DataFrame с правильным порядком признаков
        df = pd.DataFrame([features])[self.feature_names]
        return float(self.model.predict(df)[0])

# Глобальный экземпляр
ml_trainer = MLTrainer()