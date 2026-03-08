# Bitcoin Bastion News Bot 🤖⛓️

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Aiogram Version](https://img.shields.io/badge/aiogram-3.x-blue)](https://docs.aiogram.dev/)

Telegram-бот для мониторинга и рассылки актуальных новостей, связанных с Bitcoin и экосистемой криптовалют. Проект использует асинхронную архитектуру, поддерживает многоязычность, кэширование через Redis и готов к развертыванию как serverless-приложение на Vercel.

## ✨ Ключевые возможности

*   **Автоматический сбор новостей:** Бот периодически опрашивает внешние API (сервис `services/api_client.py`) для получения свежих материалов.
*   **Мгновенные уведомления:** Подписчики получают новости в реальном времени через Telegram.
*   **Интерактивное меню:** Удобная навигация по разделам с помощью кастомных клавиатур (`keyboards.py`).
*   **Многоязычность:** Поддержка нескольких языков интерфейса (используется Fluent — `locales/messages.ftl`).
*   **Веб-интерфейс:** Встроенная простая веб-страница (`templates/webapp.html`) для отображения статистики или последних новостей (доступна через `web.py`).
*   **Производительность:** Кэширование данных в Redis (`redis_cache.py`) для снижения нагрузки на внешние источники и ускорения работы.
*   **Гибкое планирование задач:** Модуль `scheduler.py` управляет периодическими задачами, такими как проверка новостей.

## 🛠 Технологический стек

*   **Язык:** Python 3.9+
*   **Фреймворк для бота:** [Aiogram 3.x](https://docs.aiogram.dev/) (асинхронный)
*   **API и бэкенд:** [FastAPI](https://fastapi.tiangolo.com/) (для веб-части `web.py`)
*   **База данных:** (Предположительно SQLite/PostgreSQL, см. `database.py`)
*   **Кэширование:** Redis
*   **Локализация:** Fluent (`locales/`)
*   **Развертывание:** Готов к деплою на Vercel (`vercel.json`, `api/index.py`)

## 🚀 Быстрый старт

### Предварительные требования

*   Python 3.9 или выше
*   Установленный и запущенный Redis
*   Токен бота Telegram (получить у [@BotFather](https://t.me/BotFather))
*   API-ключ (или несколько) от сервиса новостей (нужно указать в настройках)

### Установка и запуск

1.  **Клонируйте репозиторий**
    ```bash
    git clone https://github.com/Hegehub/Bitcoin-Bastion-News-bot.git
    cd Bitcoin-Bastion-News-bot
    ```

2.  **Создайте и активируйте виртуальное окружение**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    # venv\Scripts\activate  # Windows
    ```

3.  **Установите зависимости**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Настройте переменные окружения**
    Скопируйте файл `.env.example` в `.env` (если его нет, создайте) и заполните необходимые данные:
    ```dotenv
    BOT_TOKEN=токен_вашего_бота_здесь
    REDIS_HOST=localhost
    REDIS_PORT=6379
    NEWS_API_KEY=ваш_ключ_для_новостного_api
    # Приоритет: DATABASE_URL -> SUPABASE_POOLER_URL -> SUPABASE_DB_URL -> отдельные DB_* переменные
    DATABASE_URL=
    SUPABASE_POOLER_URL=postgresql://postgres.<project-ref>:<password>@aws-1-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require
    SUPABASE_DB_URL=postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres?sslmode=require
    SUPABASE_POOL_MODE=session  # session | transaction

    # Альтернатива: можно передать подключение отдельными переменными
    DB_USER=postgres.<project-ref>
    DB_PASSWORD=<password>
    DB_HOST=aws-1-eu-central-1.pooler.supabase.com
    DB_PORT=5432
    DB_NAME=postgres

    DATABASE_CONNECT_RETRIES=3
    DATABASE_CONNECT_RETRY_DELAY=2
    # ... другие переменные из .env файла
    ```

5.  **Запустите бота**
    ```bash
    python main.py
    ```
    Бот начнет работу и будет проверять новости согласно расписанию.

## ☁️ Развертывание на Vercel

Проект содержит файлы `vercel.json` и директорию `api/` для бессерверного развертывания.

1.  Установите [Vercel CLI](https://vercel.com/cli) или подключите репозиторий к [Vercel Dashboard](https://vercel.com/).
2.  Настройте переменные окружения в проекте Vercel (аналогично пункту 4 выше).
3.  Выполните команду в корне проекта:
    ```bash
    vercel --prod
    ```
    Веб-часть бота (например, для вебхуков или веб-интерфейса) будет доступна по ссылке, предоставленной Vercel.

## 📁 Структура проекта

*   `main.py` — точка входа в приложение (запуск бота и веб-сервера).
*   `bot.py` — инициализация и настройка экземпляра бота Aiogram.
*   `handlers/` — директория с обработчиками команд и сообщений (разделение на `private.py`, `admin.py` и т.д.).
*   `services/` — логика взаимодействия с внешними API (`api_client.py`).
*   `database.py` — модели и настройки для работы с базой данных.
*   `redis_cache.py` — функции для работы с кэшем Redis.
*   `scheduler.py` — планировщик периодических задач (проверка новостей).
*   `keyboards.py` — генерация inline и reply клавиатур.
*   `middlewares.py` — middlewares для обработки входящих обновлений.
*   `locales/` — файлы локализации в формате Fluent.
*   `templates/` — HTML-шаблоны для веб-интерфейса.
*   `web.py` — FastAPI приложение для веб-части.
*   `api/` — serverless-функции для Vercel.
*   `config.py` — загрузка и валидация конфигурации из переменных окружения.
*   `utils.py` — вспомогательные функции.
*   `.env` — файл с локальными переменными окружения (не коммитится).

## 🤝 Как внести вклад

Будем рады вашей помощи! Если у вас есть идеи по улучшению бота или вы нашли ошибку:

1.  Создайте **Issue** в репозитории с описанием проблемы или предложения.
2.  Если хотите предложить изменения, создайте **Pull Request** с подробным описанием ваших правок.

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. Подробнее см. в файле `LICENSE` (если он добавлен в репозиторий).

---

**Связь и поддержка:** Если у вас возникли вопросы по работе с ботом, создайте Issue на GitHub.