"""
Нода фильтрации тегов промптов по категориям Danbooru.

Использует данные о категориях тегов напрямую от D站画廊
(выход "tags_by_category" ноды DanbooruGalleryNode) —
без дополнительных запросов к API.
"""

import json
from ..utils.logger import get_logger

logger = get_logger(__name__)


def format_tags(tags_str: str, category: str, replace_underscores: bool,
                escape_brackets: bool, artist_prefix: bool) -> str:
    """Применить форматирование к строке тегов одной категории (как в D站画廊)."""
    if not tags_str:
        return tags_str
    tags = tags_str.split(" ")
    formatted = []
    for tag in tags:
        if not tag:
            continue
        if artist_prefix and category == "artist":
            tag = "@" + tag
        if replace_underscores:
            tag = tag.replace("_", " ")
        if escape_brackets:
            tag = tag.replace("(", "\\(").replace(")", "\\)")
        formatted.append(tag)
    return ", ".join(formatted)


class TagCategoryFilter:
    """
    Фильтрует теги в промптах по выбранным категориям Danbooru.

    Подключите выход "tags_by_category" от D站画廊 к входу
    "tags_by_category" этой ноды. Выберите нужные категории —
    на выходе получите промпты только с тегами этих категорий.

    Форматирование (как в D站画廊):
      - Замена _ на пробел
      - Экранирование скобок ( ) → \\( \\)
      - Префикс @ к нику художника
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "tags_by_category": ("STRING", {"forceInput": True}),
                "general": ("BOOLEAN", {"default": True}),
                "artist": ("BOOLEAN", {"default": True}),
                "copyright": ("BOOLEAN", {"default": True}),
                "character": ("BOOLEAN", {"default": True}),
                "meta": ("BOOLEAN", {"default": False}),
                "replace_underscores": ("BOOLEAN", {"default": True}),
                "escape_brackets": ("BOOLEAN", {"default": False}),
                "artist_prefix": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "prompts": ("STRING", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filtered_prompts",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "filter_by_category"
    CATEGORY = "danbooru"

    _CATEGORY_KEYS = ("character", "copyright", "artist", "general", "meta")

    def filter_by_category(self, tags_by_category, general=True, artist=True,
                           copyright=True, character=True, meta=False,
                           replace_underscores=True, escape_brackets=False,
                           artist_prefix=False, prompts=None):
        # Обратная совместимость
        if (not tags_by_category or tags_by_category == "") and prompts is not None:
            tags_by_category = prompts

        if isinstance(tags_by_category, str):
            tbc_list = [tags_by_category]
        elif isinstance(tags_by_category, list):
            tbc_list = tags_by_category
        else:
            logger.warning("[TagCategoryFilter] Неожиданный тип: %s", type(tags_by_category))
            return [[""]]

        keep: set[str] = set()
        if general:
            keep.add("general")
        if artist:
            keep.add("artist")
        if copyright:
            keep.add("copyright")
        if character:
            keep.add("character")
        if meta:
            keep.add("meta")

        if not keep:
            return [[""] * len(tbc_list)]

        filtered = []
        for tbc_str in tbc_list:
            if not tbc_str or not isinstance(tbc_str, str) or not tbc_str.strip():
                filtered.append("")
                continue

            try:
                tbc = json.loads(tbc_str)
            except (json.JSONDecodeError, TypeError):
                logger.warning("[TagCategoryFilter] Невалидный JSON: %s", tbc_str[:100])
                filtered.append("")
                continue

            parts = []
            for cat in self._CATEGORY_KEYS:
                if cat in keep:
                    tags_str = tbc.get(cat, "")
                    if tags_str:
                        formatted = format_tags(tags_str, cat, replace_underscores,
                                                escape_brackets, artist_prefix)
                        parts.append(formatted)

            filtered.append(", ".join(parts))

        return [filtered]

    @classmethod
    def IS_CHANGED(cls, tags_by_category, general=True, artist=True,
                   copyright=True, character=True, meta=False,
                   replace_underscores=True, escape_brackets=False,
                   artist_prefix=False, prompts=None):
        return (tags_by_category, general, artist, copyright, character, meta,
                replace_underscores, escape_brackets, artist_prefix)
