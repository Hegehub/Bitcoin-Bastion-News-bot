# План улучшений Bitcoin-Bastion-News-bot (BTC-only): 21 функция

## Контекст анализа

План собран после обзора:
- репозитория **OpenCryptoBot** (архитектура плагинов, Telegram UX-паттерны, rate-limit/repeat/inline подход);
- репозитория **free-crypto-news** (каталог API и AI/market/on-chain endpoint-ов);
- документации **Telegram Bot API** (методы для современного UX и realtime-взаимодействия).

Ниже перечислены только функции, релевантные **Bitcoin**.

---

## 21 полезная функция для внедрения

### A. BTC данные и аналитика (core продукта)

1. **BTC-only news feed c фильтрацией шума**  
   Источник: `/api/bitcoin`, `/api/news`, `/api/search` из free-crypto-news.  
   Польза: убрать альткоин-шум и оставить только новости, влияющие на BTC.

2. **Breaking BTC Alert Mode**  
   Источник: `/api/breaking` + текущий scheduler проекта.  
   Польза: мгновенно пушить только критически важные новости (ETF, регуляция, биржи, хак).

3. **AI sentiment именно по Bitcoin**  
   Источник: `/api/sentiment`, `/api/ai/sentiment?asset=BTC`.  
   Польза: оценка бычий/медвежий фон по BTC-новостям.

4. **Причинно-следственный триггер “news -> move”**  
   Источник: идеи текущего `trigger_detector` + `/api/analytics/causality`.  
   Польза: выделять новости, после которых действительно был импульс цены BTC.

5. **BTC fear & greed в каждом дайджесте**  
   Источник: `/api/fear-greed`.  
   Польза: единая “рыночная температура” в сообщениях канала и лички.

6. **Whale Alerts (BTC транзакции)**  
   Источник: `/api/whale-alerts`.  
   Польза: отслеживание крупных переводов и потенциального давления на цену.

7. **BTC Liquidations Monitor**  
   Источник: `/api/liquidations`.  
   Польза: видеть перегретость рынка и вероятность резких движений.

8. **Funding/Derivatives Pulse для BTC**  
   Источник: `/api/funding`, `/api/options`, `/api/market/derivatives`.  
   Польза: понимать позиционирование фьючерсного рынка.

9. **On-chain модуль по Bitcoin сети**  
   Источник: раздел Bitcoin On-Chain API в free-crypto-news (`/api/onchain/*`).  
   Польза: добавить метрики сети (нагрузка, активность, потоки) к новостям.

10. **BTC narrative clustering (темы недели)**  
    Источник: `/api/narratives`, `/api/ai/narratives`, `/api/entities`.  
    Польза: группировать шум в 3–5 ключевых сюжетов (ETF, майнинг, макро и т.д.).

11. **Умный BTC-дайджест (утро/вечер)**  
    Источник: `/api/digest`, `/api/summarize`, `/api/ai/brief`.  
    Польза: короткие сводки без перегруза.

12. **Q&A по BTC новостям внутри бота**  
    Источник: `/api/ask`, `/api/ai/explain`.  
    Польза: пользователь задает “что происходит с BTC?” и получает контекстный ответ.

13. **Исторический backfill для обучения триггеров**  
    Источник: `/api/archive`, `/api/archive/status` + архив free-crypto-news.  
    Польза: ретро-анализ, какие типы новостей сильнее двигают BTC.

14. **Credibility scoring источников**  
    Источник: `/api/analytics/credibility`, `/api/ai/source-quality`.  
    Польза: приоритизация надежных источников и понижение кликбейта.

15. **BTC anomaly detection**  
    Источник: `/api/analytics/anomalies`, `/api/analytics/headlines`.  
    Польза: автообнаружение нехарактерных всплесков новостной активности.

### B. Telegram “современный бот” (UX, delivery, engagement)

16. **Глубокое inline-меню c callback-переотрисовкой**  
    Telegram: `InlineKeyboardMarkup` + `answerCallbackQuery` + `editMessageText`.  
    Польза: быстрый UX без спама новыми сообщениями.

17. **Персональные команды и scope-команды**  
    Telegram: `setMyCommands` (разные наборы для private/group/admin).  
    Польза: чистый интерфейс и меньше ошибок пользователей.

18. **Медиа-дайджесты (текст + график/картинка)**  
    Telegram: `sendPhoto`, `sendMediaGroup`, `copyMessage`.  
    Польза: выше вовлечение, визуально понятные сводки BTC.

19. **Inline mode: “@bot btc” для шаринга в любых чатах**  
    Telegram: `answerInlineQuery`.  
    Польза: органический рост и удобное распространение аналитики.

20. **Тематические топики/форумы в группах**  
    Telegram: поддержка `message_thread_id` в `sendMessage` и related methods.  
    Польза: отделить “alerts”, “discussion”, “education” по BTC.

21. **Гибкая модель доставки: webhook + fallback polling**  
    Telegram: `setWebhook` + healthchecks.  
    Польза: надежность в проде и устойчивость к деградациям.

---

## Лучшее применение для Bitcoin-Bastion-News-bot

### 1) Что внедрять в первую очередь (максимум value)

- **P1:** 1, 2, 3, 4, 5, 16, 17  
  (чистый BTC-поток + качественная доставка + удобный Telegram UX)
- **P2:** 6, 7, 8, 11, 14, 18  
  (деривативы/киты + наглядные дайджесты + качество источников)
- **P3:** 9, 10, 12, 13, 15, 19, 20, 21  
  (интеллектуализация, историческое обучение, масштабирование и growth)

### 2) Как лучше использовать OpenCryptoBot идеи

- Взять **плагинный подход** для изоляции модулей (`btc_news`, `btc_derivatives`, `btc_onchain`, `btc_digest`).
- Внедрить **rate-limit per-user/per-command** и антиспам политику.
- Добавить **repeat/subscription** модель с тонкой частотой (например, каждые 15/30/60 минут).
- Использовать **inline-паттерн** и edit-механики вместо лишних новых сообщений.

### 3) Как лучше использовать free-crypto-news

- Сделать его **primary data layer** для новостей/AI/sentiment.
- Включить **SSE/realtime endpoint** для “breaking” и быстрых оповещений.
- На уровне ingestion оставить только **BTC релевантность** (тикер/семантика/контекст).
- Применить AI endpoint-ы к **ранжированию важности**, а не к публикации “всего подряд”.

### 4) Ожидаемый результат для проекта

После внедрения 21 функции бот становится:
- BTC-first (без шума по альтам),
- быстрым по доставке,
- объясняющим “почему движение произошло”,
- удобным в Telegram (inline/callback/scoped commands/topics),
- и масштабируемым для канала, группы и личных подписок.
