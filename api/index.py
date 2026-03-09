import sys
from pathlib import Path

# Добавляем путь к корневой папке проекта, чтобы импортировать web
sys.path.append(str(Path(__file__).parent.parent))

from web import app as app  # импортируем экземпляр FastAPI из web.py

__all__ = ["app"]

# Vercel ожидает переменную с именем 'app'
# Можно оставить как есть, или переименовать, но обычно оставляют app