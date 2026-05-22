"""
Нода разделения тегов промптов по категориям Danbooru на отдельные выходы.

Принимает tags_by_category от D站画廊 и раскладывает теги
по пяти выходам — по одному на каждую категорию.
"""

import json
from ..utils.logger import get_logger
from .tag_category_filter import format_tags

logger = get_logger(__name__)


class TagCategorySplit:
    """
    Разделяет теги промптов по категориям Danbooru на отдельные выходы.

    Подключите выход "tags_by_category" от D站画廊 к входу
    "tags_by_category" этой ноды. На выходах получите пять списков
    промптов — по одному на каждую категорию.

    Форматирование (как в D站画廊):
      - Замена _ на пробел
      - Экранирование скобок ( ) → \\( \\)
      - Префикс @ к нику художника

    Выходы:
      - character  — теги персонажей (1girl, izayoi sakuya, ...)
      - copyright  — теги копирайта (touhou, ...)
      - artist     — теги художников (@jack (wkm74959), ...)
      - general    — общие теги (blonde hair, sitting, ...)
      - meta       — мета-теги (highres, ...)
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "tags_by_category": ("STRING", {"forceInput": True}),
                "replace_underscores": ("BOOLEAN", {"default": True}),
                "escape_brackets": ("BOOLEAN", {"default": False}),
                "artist_prefix": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("character", "copyright", "artist", "general", "meta")
    OUTPUT_IS_LIST = (True, True, True, True, True)
    FUNCTION = "split_categories"
    CATEGORY = "danbooru"

    @classmethod
    def IS_CHANGED(cls, tags_by_category, replace_underscores=True,
                   escape_brackets=False, artist_prefix=False):
        return (tags_by_category, replace_underscores, escape_brackets, artist_prefix)

    def split_categories(self, tags_by_category, replace_underscores=True,
                         escape_brackets=False, artist_prefix=False):
        if isinstance(tags_by_category, str):
            tbc_list = [tags_by_category]
        elif isinstance(tags_by_category, list):
            tbc_list = tags_by_category
        else:
            logger.warning("[TagCategorySplit] Неожиданный тип: %s", type(tags_by_category))
            return ([""], [""], [""], [""], [""])

        character_list = []
        copyright_list = []
        artist_list = []
        general_list = []
        meta_list = []

        for tbc_str in tbc_list:
            if not tbc_str or not isinstance(tbc_str, str) or not tbc_str.strip():
                for lst in (character_list, copyright_list, artist_list,
                            general_list, meta_list):
                    lst.append("")
                continue

            try:
                tbc = json.loads(tbc_str)
            except (json.JSONDecodeError, TypeError):
                logger.warning("[TagCategorySplit] Невалидный JSON: %s", tbc_str[:100])
                for lst in (character_list, copyright_list, artist_list,
                            general_list, meta_list):
                    lst.append("")
                continue

            character_list.append(
                format_tags(tbc.get("character", ""), "character",
                            replace_underscores, escape_brackets, artist_prefix))
            copyright_list.append(
                format_tags(tbc.get("copyright", ""), "copyright",
                            replace_underscores, escape_brackets, artist_prefix))
            artist_list.append(
                format_tags(tbc.get("artist", ""), "artist",
                            replace_underscores, escape_brackets, artist_prefix))
            general_list.append(
                format_tags(tbc.get("general", ""), "general",
                            replace_underscores, escape_brackets, artist_prefix))
            meta_list.append(
                format_tags(tbc.get("meta", ""), "meta",
                            replace_underscores, escape_brackets, artist_prefix))

        return (character_list, copyright_list, artist_list, general_list, meta_list)
