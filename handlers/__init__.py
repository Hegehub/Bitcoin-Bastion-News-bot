from .private import router as private
from .group import router as group
from .admin import router as admin

__all__ = ["private", "group", "admin"]
