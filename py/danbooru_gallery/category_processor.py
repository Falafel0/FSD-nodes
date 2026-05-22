"""
Нода обработки тегов по категориям с префиксами и суффиксами.

Принимает tags_by_category (JSON) от Danbooru Gallery и позволяет
для каждой категории задать свой префикс и суффикс.
"""

import json
from ..utils.logger import get_logger
from .tag_category_filter import format_tags

logger = get_logger(__name__)


class CategoryProcessor:
    """
    Добавляет префиксы и суффиксы к тегам отдельных категорий.

    Подключите выход "tags_by_category" от Danbooru Gallery к входу
    "tags_by_category" этой ноды. Для каждой из 5 категорий можно
    задать текст, который будет добавлен перед тегами (префикс)
    и после них (суффикс).

    Пример:
      - character: префикс "character:" → "character: 1girl, blue eyes"
      - artist: префикс "by " → "by jack (wkm74959)"
      - general: без префикса, суффикс " | "

    Если категория не включена (enabled=false), её теги пропускаются.
    Пустая категория (без тегов) тоже пропускается.
    """

    @classmethod
    def INPUT_TYPES(cls):
        cats = ["character", "copyright", "artist", "general", "meta"]
        inputs = {
            "required": {
                "tags_by_category": ("STRING", {"forceInput": True}),
                "separator": ("STRING", {"default": ", "}),
                "replace_underscores": ("BOOLEAN", {"default": True}),
                "escape_brackets": ("BOOLEAN", {"default": False}),
                "artist_prefix": ("BOOLEAN", {"default": False}),
            }
        }
        for cat in cats:
            inputs["required"][f"{cat}_enabled"] = ("BOOLEAN", {"default": True})
            inputs["required"][f"{cat}_prefix"] = ("STRING", {"default": ""})
            inputs["required"][f"{cat}_suffix"] = ("STRING", {"default": ""})
        return inputs

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "process_categories"
    CATEGORY = "danbooru"

    _CATEGORY_KEYS = ("character", "copyright", "artist", "general", "meta")

    def process_categories(self, tags_by_category, separator=", ",
                           replace_underscores=True, escape_brackets=False,
                           artist_prefix=False, **kwargs):
        if isinstance(tags_by_category, str):
            tbc_list = [tags_by_category]
        elif isinstance(tags_by_category, list):
            tbc_list = tags_by_category
        else:
            return [[""]]

        result = []
        for tbc_str in tbc_list:
            if not tbc_str or not isinstance(tbc_str, str) or not tbc_str.strip():
                result.append("")
                continue

            try:
                tbc = json.loads(tbc_str)
            except (json.JSONDecodeError, TypeError):
                result.append("")
                continue

            parts = []
            for cat in self._CATEGORY_KEYS:
                enabled = kwargs.get(f"{cat}_enabled", True)
                if not enabled:
                    continue

                tags_str = tbc.get(cat, "")
                if not tags_str:
                    continue

                formatted = format_tags(tags_str, cat, replace_underscores,
                                        escape_brackets, artist_prefix)

                prefix = kwargs.get(f"{cat}_prefix", "")
                suffix = kwargs.get(f"{cat}_suffix", "")

                if prefix or suffix:
                    parts.append(f"{prefix}{formatted}{suffix}")
                else:
                    parts.append(formatted)

            result.append(separator.join(parts))

        return [result]

    @classmethod
    def IS_CHANGED(cls, tags_by_category, **kwargs):
        return (tags_by_category, kwargs)
