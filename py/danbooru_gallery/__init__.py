from .danbooru_gallery import NODE_CLASS_MAPPINGS as gallery_mappings, NODE_DISPLAY_NAME_MAPPINGS as gallery_display
from .tag_category_filter import TagCategoryFilter
from .tag_category_split import TagCategorySplit
from .metadata_formatter import MetadataFormatter
from .metadata_split import MetadataSplit
from .category_processor import CategoryProcessor

NODE_CLASS_MAPPINGS = {
    **gallery_mappings,
    "TagCategoryFilter": TagCategoryFilter,
    "TagCategorySplit": TagCategorySplit,
    "MetadataFormatter": MetadataFormatter,
    "MetadataSplit": MetadataSplit,
    "CategoryProcessor": CategoryProcessor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    **gallery_display,
    "TagCategoryFilter": "🏷️ Filter by Category",
    "TagCategorySplit": "📤 Split by Category",
    "MetadataFormatter": "📝 Format Metadata",
    "MetadataSplit": "📋 Split Metadata",
    "CategoryProcessor": "🔧 Process Categories",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
