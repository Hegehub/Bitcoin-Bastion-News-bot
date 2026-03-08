import sys
from pathlib import Path

# Добавляем путь к корневой папке проекта, чтобы импортировать web
sys.path.append(str(Path(__file__).parent.parent))

from web import app  # импортируем экземпляр FastAPI из web.py

# Vercel ожидает переменную с именем 'app'
# Можно оставить как есть, или переименовать, но обычно оставляют app