🚀 Использование

Вариант 1: Реальные данные (рекомендуется для продакшена)

```bash
# Убедитесь, что у вас настроен CRYPTORANK_API_KEY в .env
cd ваш_проект
python scripts/download_historical_btc.py
```

Вариант 2: Тестовые данные (для разработки и отладки)

```bash
cd ваш_проект
python scripts/generate_test_data.py
```

📋 Результат

После выполнения скрипта в папке data/ появится файл historical_btc.csv со следующей структурой:

```csv
timestamp,price,title,source,sentiment_score
2026-01-01 10:30:00,51234.56,"Bitcoin ETF approved by SEC, price surges",CoinDesk,0.85
2026-01-01 14:15:00,51890.23,"Major bank launches Bitcoin trading desk",CoinTelegraph,0.78
2026-01-02 09:45:00,50987.34,"SEC delays Bitcoin ETF decision",The Block,0.12
...
```
