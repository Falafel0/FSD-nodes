"""
ComfyUI-FSD-nodes — единое расширение, объединяющее:
  - FSD_PIPE: пайплайн-ориентированные ноды (60+ узлов)
  - FSD Switches/Bypasser: динамические Switch, Diverter, Gate, Bypasser
  - Danbooru Gallery: поиск и импорт изображений с Danbooru (28 узлов)
  - Style Selector: визуальный выбор стилей с превью и локальной базой
  - KikoTools: коллекция инструментов (30 узлов) — ComfyAssets
  - Anima Style Explorer: браузер стилей художников с Fullet-интеграцией
"""

import sys
import time

_init_start_time = time.time()

# =============================================================================
# 1. FSD_PIPE nodes (ядро)
# =============================================================================
from .pipe_nodes import (
    NODE_CLASS_MAPPINGS as PIPE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS as PIPE_DISPLAY_NAME_MAPPINGS,
)

# =============================================================================
# 2. FSD standalone nodes (Switches, Bypasser, Toggle)
# =============================================================================
from .standalone_nodes import (
    NODE_CLASS_MAPPINGS as STANDALONE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS as STANDALONE_DISPLAY_NAME_MAPPINGS,
)

# =============================================================================
# 3. Danbooru Gallery nodes
# =============================================================================
try:
    from .py.danbooru_gallery import (
        NODE_CLASS_MAPPINGS as DANBOORU_CLASS_MAPPINGS,
        NODE_DISPLAY_NAME_MAPPINGS as DANBOORU_DISPLAY_NAME_MAPPINGS,
    )
    _has_danbooru = True
except Exception as e:
    import traceback
    print(f"[FSD] Danbooru Gallery import failed: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    DANBOORU_CLASS_MAPPINGS = {}
    DANBOORU_DISPLAY_NAME_MAPPINGS = {}
    _has_danbooru = False

# =============================================================================
# 4. Style Selector node
# =============================================================================
try:
    from .py.style_selector import (
        NODE_CLASS_MAPPINGS as STYLESELECTOR_CLASS_MAPPINGS,
        NODE_DISPLAY_NAME_MAPPINGS as STYLESELECTOR_DISPLAY_NAME_MAPPINGS,
    )
    _has_styleselector = True
except Exception as e:
    print(f"[FSD] Style Selector import failed: {e}", file=sys.stderr)
    STYLESELECTOR_CLASS_MAPPINGS = {}
    STYLESELECTOR_DISPLAY_NAME_MAPPINGS = {}
    _has_styleselector = False

# =============================================================================
# 5. KikoTools nodes (30 узлов)
# =============================================================================
try:
    from .py.kikotools import (
        NODE_CLASS_MAPPINGS as KIKOTOOLS_CLASS_MAPPINGS,
        NODE_DISPLAY_NAME_MAPPINGS as KIKOTOOLS_DISPLAY_NAME_MAPPINGS,
    )
    _has_kikotools = True
except Exception as e:
    import traceback
    print(f"[FSD] KikoTools import failed: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    KIKOTOOLS_CLASS_MAPPINGS = {}
    KIKOTOOLS_DISPLAY_NAME_MAPPINGS = {}
    _has_kikotools = False

# =============================================================================
# 6. Anima Style Explorer node
# =============================================================================
try:
    from .py.anima_style import (
        NODE_CLASS_MAPPINGS as ANIMA_CLASS_MAPPINGS,
        NODE_DISPLAY_NAME_MAPPINGS as ANIMA_DISPLAY_NAME_MAPPINGS,
    )
    _has_anima = True
except Exception as e:
    import traceback
    print(f"[FSD] Anima Style Explorer import failed: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    ANIMA_CLASS_MAPPINGS = {}
    ANIMA_DISPLAY_NAME_MAPPINGS = {}
    _has_anima = False

# =============================================================================
# 7. LoRA Stack module
# =============================================================================
try:
    from .py.lora_stack import (
        NODE_CLASS_MAPPINGS as LORASTACK_CLASS_MAPPINGS,
        NODE_DISPLAY_NAME_MAPPINGS as LORASTACK_DISPLAY_NAME_MAPPINGS,
        register_routes as lorastack_register_routes,
    )
    _has_lorastack = True
except Exception as e:
    import traceback
    print(f"[FSD] LoRA Stack import failed: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    LORASTACK_CLASS_MAPPINGS = {}
    LORASTACK_DISPLAY_NAME_MAPPINGS = {}
    _has_lorastack = False

# =============================================================================
# Merge all NODE_CLASS_MAPPINGS
# Порядок приоритета (последний перезаписывает при конфликте):
#   1. pipe_nodes (FSD_PIPE)
#   2. standalone_nodes (Switches/Bypasser)
#   3. danbooru_gallery
#   4. style_selector
#   5. kikotools
#   6. anima_style
#   7. lora_stack
# =============================================================================
NODE_CLASS_MAPPINGS = {}
NODE_CLASS_MAPPINGS.update(PIPE_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(STANDALONE_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(DANBOORU_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(STYLESELECTOR_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(KIKOTOOLS_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(ANIMA_CLASS_MAPPINGS)
NODE_CLASS_MAPPINGS.update(LORASTACK_CLASS_MAPPINGS)

NODE_DISPLAY_NAME_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS.update(PIPE_DISPLAY_NAME_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS.update(STANDALONE_DISPLAY_NAME_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS.update(DANBOORU_DISPLAY_NAME_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS.update(STYLESELECTOR_DISPLAY_NAME_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS.update(KIKOTOOLS_DISPLAY_NAME_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS.update(ANIMA_DISPLAY_NAME_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS.update(LORASTACK_DISPLAY_NAME_MAPPINGS)

# =============================================================================
# JavaScript frontend directory
# =============================================================================
WEB_DIRECTORY = "./js"

# =============================================================================
# API routes registration
# =============================================================================

# --- KikoTools API routes ---
if _has_kikotools:
    try:
        from server import PromptServer
        from aiohttp import web
        import folder_paths
        import os as _os

        @PromptServer.instance.routes.get("/kikotools/autocomplete/embeddings")
        async def get_kikotools_embeddings(request):
            """API endpoint for getting list of embeddings with full paths."""
            try:
                embedding_files = folder_paths.get_filename_list("embeddings")
                embeddings = []
                for f in embedding_files:
                    clean_path = _os.path.splitext(f)[0]
                    embeddings.append({
                        "file_name": clean_path,
                        "model_name": clean_path,
                        "name": _os.path.basename(clean_path),
                        "path": clean_path,
                    })
                return web.json_response(embeddings)
            except Exception as e:
                print(f"[FSD] Error getting embeddings: {e}", file=sys.stderr)
                return web.json_response([])

        @PromptServer.instance.routes.get("/kikotools/autocomplete/loras")
        async def get_kikotools_loras(request):
            """API endpoint for getting list of LoRAs."""
            try:
                lora_files = folder_paths.get_filename_list("loras")
                loras = []
                for f in lora_files:
                    clean_path = _os.path.splitext(f)[0]
                    loras.append({
                        "name": _os.path.basename(clean_path),
                        "path": clean_path,
                        "file": f,
                    })
                return web.json_response(loras)
            except Exception as e:
                print(f"[FSD] Error getting LoRAs: {e}", file=sys.stderr)
                return web.json_response([])

        print("[FSD] KikoTools autocomplete API routes registered", file=sys.stderr)
    except ImportError as e:
        print(f"[FSD] KikoTools API init skipped (ComfyUI env not available): {e}", file=sys.stderr)
    except Exception as e:
        print(f"[FSD] KikoTools API init failed: {e}", file=sys.stderr)

# --- Danbooru Gallery API + Logger ---
if _has_danbooru:
    try:
        from server import PromptServer
        from aiohttp import web
        from .py.utils import config

        # Logger init
        from .py.utils.logger import get_logger
        logger = get_logger(__name__)

        @PromptServer.instance.routes.post("/danbooru/logs/batch")
        async def receive_js_logs(request):
            """Приём логов с фронтенда JS"""
            try:
                data = await request.json()
                logs = data.get("logs", [])

                for log_entry in logs:
                    level_str = log_entry.get("level", "INFO").upper()
                    component = log_entry.get("component", "JS")
                    message = log_entry.get("message", "")
                    browser = log_entry.get("browser", "Unknown")

                    js_logger = get_logger(f"JS/{browser}")

                    if message:
                        full_message = f"[{component}] {message}"
                    else:
                        full_message = f"[{component}]"

                    if level_str == "DEBUG":
                        js_logger.debug(full_message)
                    elif level_str == "INFO":
                        js_logger.info(full_message)
                    elif level_str == "WARNING":
                        js_logger.warning(full_message)
                    elif level_str == "ERROR":
                        js_logger.error(full_message)
                    elif level_str == "CRITICAL":
                        js_logger.critical(full_message)
                    else:
                        js_logger.info(full_message)

                return web.json_response({
                    "success": True,
                    "received": len(logs)
                })
            except Exception as e:
                logger.error(f"Ошибка приёма JS логов: {e}")
                return web.json_response({
                    "success": False,
                    "error": str(e)
                }, status=500)

        @PromptServer.instance.routes.get("/danbooru_gallery/get_sampler_node_types")
        async def get_sampler_node_types(request):
            """Получение списка типов KSampler-узлов"""
            try:
                sampler_types = config.get_sampler_node_types()
                return web.json_response({"status": "success", "sampler_node_types": sampler_types})
            except Exception as e:
                return web.json_response({"status": "error", "error": str(e)}, status=500)

        print("[FSD] Danbooru Gallery API routes registered", file=sys.stderr)
        logger.info("Danbooru Gallery API routes registered")

    except ImportError as e:
        print(f"[FSD] Danbooru API init skipped (ComfyUI env not available): {e}", file=sys.stderr)
    except Exception as e:
        print(f"[FSD] Danbooru API init failed: {e}", file=sys.stderr)

# --- Anima Style API routes ---
if _has_anima:
    try:
        from .py.anima_style.routes import register as anima_register_routes
        anima_register_routes(PromptServer)
        print("[FSD] Anima Style API routes registered", file=sys.stderr)
    except ImportError as e:
        print(f"[FSD] Anima API init skipped (ComfyUI env not available): {e}", file=sys.stderr)
    except Exception as e:
        import traceback
        print(f"[FSD] Anima API init failed: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

# --- LoRA Stack API routes ---
if _has_lorastack:
    try:
        lorastack_register_routes(PromptServer)
        print("[FSD] LoRA Stack API routes registered", file=sys.stderr)
    except Exception as e:
        import traceback
        print(f"[FSD] LoRA Stack API init failed: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

# =============================================================================
# Initialization report
# =============================================================================
_init_duration = time.time() - _init_start_time

print("=" * 70, file=sys.stderr)
print("  FSD Nodes — Unified ComfyUI Extension", file=sys.stderr)
print(f"  Nodes: {len(NODE_CLASS_MAPPINGS)}  |  Init: {_init_duration:.2f}s", file=sys.stderr)
print(f"  FSD_PIPE: {len(PIPE_CLASS_MAPPINGS)}  |  Standalone: {len(STANDALONE_CLASS_MAPPINGS)}", file=sys.stderr)
print(f"  Danbooru: {len(DANBOORU_CLASS_MAPPINGS)}  |  StyleSelector: {len(STYLESELECTOR_CLASS_MAPPINGS)}", file=sys.stderr)
print(f"  KikoTools: {len(KIKOTOOLS_CLASS_MAPPINGS)}  |  AnimaStyle: {len(ANIMA_CLASS_MAPPINGS)}", file=sys.stderr)
print(f"  LoRA Stack: {len(LORASTACK_CLASS_MAPPINGS)}", file=sys.stderr)
print("=" * 70, file=sys.stderr)

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']
