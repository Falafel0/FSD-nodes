"""
Shared modules for ComfyUI-Danbooru-Gallery (только БД для офлайн-автодополнения)
"""

from ..utils.logger import get_logger
logger = get_logger(__name__)

try:
    from .db.db_manager import TagDatabaseManager, get_db_manager
except ImportError as e:
    logger.warning(f"[DanbooruGallery.shared] db_manager import failed: {e}")
    TagDatabaseManager = None
    get_db_manager = None

__all__ = [
    'TagDatabaseManager',
    'get_db_manager',
]
