"""
Нода разделения метаданных Danbooru на отдельные выходы.

Принимает JSON-метаданные от выхода "metadata" ноды Danbooru Gallery
и раскладывает по отдельным выходам — каждое поле отдельно.
"""

import json
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MetadataSplit:
    """
    Разделяет метаданные Danbooru на отдельные выходы.

    Подключите выход "metadata" от Danbooru Gallery к входу
    "metadata" этой ноды. На выходах получите отдельные поля.

    Выходы:
      - post_id     — ID поста
      - post_url    — ссылка на Danbooru
      - rating      — рейтинг (g, s, q, e)
      - score       — счёт (голоса)
      - fav_count   — добавлений в избранное
      - created_at  — дата загрузки
      - dimensions  — размеры "WxH"
      - source      — источник
      - image_url   — URL оригинального изображения
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "metadata": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT", "INT",
                    "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("post_id", "post_url", "rating", "score", "fav_count",
                    "created_at", "dimensions", "source", "image_url")
    OUTPUT_IS_LIST = (True, True, True, True, True,
                      True, True, True, True)
    FUNCTION = "split_metadata"
    CATEGORY = "danbooru"

    @classmethod
    def IS_CHANGED(cls, metadata):
        return metadata

    def split_metadata(self, metadata):
        if isinstance(metadata, str):
            meta_list = [metadata]
        elif isinstance(metadata, list):
            meta_list = metadata
        else:
            logger.warning("[MetadataSplit] Неожиданный тип: %s", type(metadata))
            empty = [""]
            return (empty, empty, empty, [0], [0], empty, empty, empty, empty)

        post_ids = []
        post_urls = []
        ratings = []
        scores = []
        fav_counts = []
        created_ats = []
        dimensions = []
        sources = []
        image_urls = []

        for meta_str in meta_list:
            if not meta_str or not isinstance(meta_str, str) or not meta_str.strip():
                post_ids.append("")
                post_urls.append("")
                ratings.append("")
                scores.append(0)
                fav_counts.append(0)
                created_ats.append("")
                dimensions.append("")
                sources.append("")
                image_urls.append("")
                continue

            try:
                meta = json.loads(meta_str)
            except (json.JSONDecodeError, TypeError):
                post_ids.append("")
                post_urls.append("")
                ratings.append("")
                scores.append(0)
                fav_counts.append(0)
                created_ats.append("")
                dimensions.append("")
                sources.append("")
                image_urls.append("")
                continue

            post_ids.append(str(meta.get("post_id", "")))
            post_urls.append(meta.get("post_url", ""))
            ratings.append(meta.get("rating", ""))

            score = meta.get("score", 0)
            scores.append(int(score) if score is not None else 0)

            fav = meta.get("fav_count", 0)
            fav_counts.append(int(fav) if fav is not None else 0)

            created_ats.append(meta.get("created_at", ""))

            w = meta.get("image_width", 0)
            h = meta.get("image_height", 0)
            if w and h:
                dimensions.append(f"{w}x{h}")
            else:
                dimensions.append("")

            sources.append(meta.get("source", ""))
            image_urls.append(meta.get("image_url", ""))

        return (post_ids, post_urls, ratings, scores, fav_counts,
                created_ats, dimensions, sources, image_urls)
