"""
Нода форматирования метаданных из Danbooru Gallery для сохранения.

Принимает JSON-метаданные от выхода "metadata" ноды Danbooru Gallery
и форматирует их в удобный текст (например, для SaveImage с метаданными).
"""

import json
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MetadataFormatter:
    """
    Форматирует метаданные Danbooru в текст для сохранения.

    Подключите выход "metadata" от Danbooru Gallery к входу
    "metadata" этой ноды. Выберите формат вывода.

    Режимы:
      - key_value — "Score: 10, Rating: s, Source: pixiv/123"
      - caption   — "Score: 10\nRating: s\nSource: pixiv/123\n..."
      - json      — как есть (JSON строка)
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "metadata": ("STRING", {"forceInput": True}),
                "format_mode": (["key_value", "caption", "json"], {"default": "key_value"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("formatted_text",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "format_metadata"
    CATEGORY = "danbooru"

    _FIELD_LABELS = {
        "post_id": "Post ID",
        "post_url": "Post URL",
        "rating": "Rating",
        "score": "Score",
        "fav_count": "Favorites",
        "created_at": "Date",
        "image_width": "Width",
        "image_height": "Height",
        "source": "Source",
        "image_url": "URL",
    }

    @classmethod
    def IS_CHANGED(cls, metadata, format_mode="key_value"):
        return (metadata, format_mode)

    def format_metadata(self, metadata, format_mode="key_value"):
        if isinstance(metadata, str):
            meta_list = [metadata]
        elif isinstance(metadata, list):
            meta_list = metadata
        else:
            return [[""]]

        result = []
        for meta_str in meta_list:
            if not meta_str or not isinstance(meta_str, str) or not meta_str.strip():
                result.append("")
                continue

            try:
                meta = json.loads(meta_str)
            except (json.JSONDecodeError, TypeError):
                result.append("")
                continue

            if format_mode == "json":
                result.append(meta_str)
                continue

            lines = []
            for key, label in self._FIELD_LABELS.items():
                value = meta.get(key, "")
                if value == "" or value is None:
                    continue
                if key == "image_width" and meta.get("image_height"):
                    lines.append(f"Size: {value}x{meta['image_height']}")
                    continue
                if key == "image_height":
                    continue  # уже в Size
                lines.append(f"{label}: {value}")

            if format_mode == "caption":
                result.append("\n".join(lines))
            else:  # key_value
                result.append(", ".join(lines))

        return [result]
