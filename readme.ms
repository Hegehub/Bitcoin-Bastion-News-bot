# Bitcoin Bastion News Bot

Telegram-бот для отслеживания и публикации новостей о рынке криптовалют с упором на Bitcoin.

## Что умеет
- собирает новости и сигналы из подключённых источников;
- определяет потенциально важные триггеры;
- работает с локализацией (RU/EN);
- включает веб-страницы для интеграции (`templates/`, `web.py`, `api/`).

## Основные модули
- `bot.py`, `main.py` — запуск и оркестрация бота;
- `handlers/` — обработчики команд и сообщений;
- `services/` — работа с API, историей цены и детекцией триггеров;
- `scheduler.py` — планировщик периодических задач;
- `database.py`, `redis_cache.py` — хранение и кеш.

## Быстрый старт
1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
2. Создайте `.env` и заполните переменные (минимум `BOT_TOKEN`, `DATABASE_URL`).
3. Запустите проект:
   ```bash
   python main.py
   ```

## Подключение к Supabase (важно)
Используйте URL подключения к Postgres в `DATABASE_URL` (или `SUPABASE_DB_URL`).

Пример:
```env
DATABASE_URL=postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres?sslmode=require
```

Проект автоматически:
- преобразует `postgres://` в `postgresql+asyncpg://`;
- преобразует `sslmode=require` в формат, который понимает `asyncpg`.

Если видите ошибку при старте, проверьте:
- что пароль в URL не содержит неэкранированные спецсимволы;
- что в Supabase не ограничен доступ по IP;
- что URL взят из раздела **Project Settings → Database → Connection string**.
