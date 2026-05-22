"""LoRA Stack module — FSD_LoraStack node + gallery API + CivitAI sync."""

import os
import json
import urllib.parse
import folder_paths
from aiohttp import web

from .nodes import FSD_LoraStack
from .metadata import load_metadata, save_metadata, read_safetensors_meta
from .civitai import sync_lora_metadata

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".avi")

NODE_CLASS_MAPPINGS = {"FSD_LoraStack": FSD_LoraStack}
NODE_DISPLAY_NAME_MAPPINGS = {"FSD_LoraStack": "LoRA Stack (Advanced)"}


def _get_preview_info(lora_name):
    """Find preview image/video alongside a LoRA file. Returns (url, type)."""
    lora_path = folder_paths.get_full_path("loras", lora_name)
    if not lora_path:
        return None, "none"
    base, _ = os.path.splitext(lora_path)
    for ext in IMAGE_EXTENSIONS + VIDEO_EXTENSIONS:
        ppath = base + ext
        if os.path.exists(ppath):
            ptype = "video" if ext.lower() in VIDEO_EXTENSIONS else "image"
            enc_lora = urllib.parse.quote_plus(lora_name)
            enc_file = urllib.parse.quote_plus(os.path.basename(ppath))
            url = "/fsd_lora/preview?filename=" + enc_file + "&lora_name=" + enc_lora
            return url, ptype
    return None, "none"


def register_routes(server):
    """Register all API routes for LoRA Stack."""

    # ── List LoRAs with metadata ──────────────────────────────────────

    @server.instance.routes.get("/fsd_lora/list")
    async def lora_list(request):
        try:
            filter_tags_str = request.query.get("filter_tag", "").strip().lower()
            filter_tags = [t.strip() for t in filter_tags_str.split(",") if t.strip()]
            filter_mode = request.query.get("mode", "OR").upper()
            filter_folder = request.query.get("folder", "").strip()
            filter_base_model = request.query.get("base_model", "").strip()
            name_filter = request.query.get("name_filter", "").strip().lower()
            selected_loras = request.query.getall("selected_loras", [])
            page = int(request.query.get("page", 1))
            per_page = int(request.query.get("per_page", 50))

            lora_files = folder_paths.get_filename_list("loras")
            lora_roots = folder_paths.get_folder_paths("loras")
            metadata = load_metadata()
            all_folders = set()
            all_base_models = set()
            filtered = []
            meta_changed = False

            for lora in lora_files:
                full = folder_paths.get_full_path("loras", lora)
                if not full:
                    continue
                this_root = None
                for root in lora_roots:
                    if os.path.normpath(full).startswith(os.path.normpath(root)):
                        this_root = root
                        break
                if not this_root:
                    continue
                folder = os.path.relpath(os.path.dirname(full), this_root)
                if folder == ".":
                    folder = "."
                all_folders.add(folder)

                if name_filter and name_filter not in lora.lower():
                    continue
                if filter_folder and filter_folder != folder:
                    continue

                lora_meta = metadata.get(lora, {})
                # Lazily populate base_model from safetensors
                if "base_model" not in lora_meta:
                    safetensors_meta = read_safetensors_meta(lora)
                    if safetensors_meta:
                        lora_meta["base_model"] = safetensors_meta.get("base_model", "")
                    else:
                        lora_meta["base_model"] = ""
                    metadata[lora] = lora_meta
                    meta_changed = True

                base_model = lora_meta.get("base_model", "")
                if base_model:
                    all_base_models.add(base_model)

                if filter_base_model and base_model != filter_base_model:
                    continue

                tags = [t.lower() for t in lora_meta.get("tags", [])]
                if filter_tags:
                    if filter_mode == "AND":
                        if not all(ft in tags for ft in filter_tags):
                            continue
                    else:
                        if not any(ft in tags for ft in filter_tags):
                            continue
                filtered.append(lora)

            if meta_changed:
                save_metadata(metadata)

            # Pin selected items to top
            pinned = [l for l in selected_loras if l in filtered]
            remaining = [l for l in filtered if l not in set(selected_loras)]
            remaining.sort(key=lambda x: x.lower())
            final_list = pinned + remaining

            total = len(final_list)
            total_pages = (total + per_page - 1) // per_page
            start = (page - 1) * per_page
            end = start + per_page
            paginated = final_list[start:end]

            result = []
            for lora in paginated:
                lora_meta = metadata.get(lora, {})
                preview_url, preview_type = _get_preview_info(lora)
                result.append({
                    "name": lora,
                    "preview_url": preview_url or "",
                    "preview_type": preview_type,
                    "tags": lora_meta.get("tags", []),
                    "trigger_words": lora_meta.get("trigger_words", ""),
                    "download_url": lora_meta.get("download_url", ""),
                    "base_model": lora_meta.get("base_model", ""),
                })

            return web.json_response({
                "loras": result,
                "folders": sorted(all_folders, key=str.lower),
                "base_models": sorted(all_base_models, key=str.lower),
                "total_pages": total_pages,
                "current_page": page,
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # ── Preview asset ──────────────────────────────────────────────────

    @server.instance.routes.get("/fsd_lora/preview")
    async def lora_preview(request):
        filename = request.query.get("filename", "")
        lora_name = request.query.get("lora_name", "")
        if not filename or not lora_name or ".." in filename or "/" in filename or "\\" in filename:
            return web.Response(status=403)

        try:
            lora_name_dec = urllib.parse.unquote_plus(lora_name)
            filename_dec = urllib.parse.unquote_plus(filename)
            lora_path = folder_paths.get_full_path("loras", lora_name_dec)
            if not lora_path:
                return web.Response(status=404, text="LoRA not found")
            preview_path = os.path.join(os.path.dirname(lora_path), filename_dec)
            if os.path.exists(preview_path):
                return web.FileResponse(preview_path)
            return web.Response(status=404, text="Preview not found")
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # ── CivitAI sync ───────────────────────────────────────────────────

    @server.instance.routes.post("/fsd_lora/sync_civitai")
    async def civitai_sync(request):
        try:
            data = await request.json()
            lora_name = data.get("lora_name", "")
            if not lora_name:
                return web.json_response({"status": "error", "message": "Missing lora_name"}, status=400)

            result = sync_lora_metadata(lora_name)
            if result["status"] == "ok":
                return web.json_response(result)
            return web.json_response(result, status=500)
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    # ── Update metadata (tags, trigger words, URL) ─────────────────────

    @server.instance.routes.post("/fsd_lora/update_metadata")
    async def update_metadata(request):
        try:
            data = await request.json()
            lora_name = data.get("lora_name", "")
            if not lora_name:
                return web.json_response({"status": "error", "message": "Missing lora_name"}, status=400)

            meta = load_metadata()
            if lora_name not in meta:
                meta[lora_name] = {}

            if data.get("tags") is not None:
                meta[lora_name]["tags"] = [str(t).strip() for t in data["tags"] if str(t).strip()]
            if data.get("trigger_words") is not None:
                meta[lora_name]["trigger_words"] = str(data["trigger_words"])
            if data.get("download_url") is not None:
                meta[lora_name]["download_url"] = str(data["download_url"])
            if data.get("base_model") is not None:
                meta[lora_name]["base_model"] = str(data["base_model"])

            save_metadata(meta)
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    # ── All tags ───────────────────────────────────────────────────────

    @server.instance.routes.get("/fsd_lora/tags")
    async def all_tags(request):
        try:
            meta = load_metadata()
            all_t = set()
            for item_meta in meta.values():
                if isinstance(item_meta.get("tags"), list):
                    for t in item_meta["tags"]:
                        all_t.add(t)
            return web.json_response({"tags": sorted(all_t, key=str.lower)})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    # ── Presets ────────────────────────────────────────────────────────

    PRESETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lora_stack_presets.json")

    def _load_presets():
        if not os.path.exists(PRESETS_FILE):
            return {}
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            return json.loads(f.read() or "{}")

    def _save_presets(data):
        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @server.instance.routes.get("/fsd_lora/presets")
    async def get_presets(request):
        return web.json_response(_load_presets())

    @server.instance.routes.post("/fsd_lora/save_preset")
    async def save_preset(request):
        try:
            data = await request.json()
            name = data.get("name", "")
            preset_data = data.get("data")
            if not name or not preset_data:
                return web.json_response({"status": "error", "message": "Missing name or data"}, status=400)
            presets = _load_presets()
            presets[name] = preset_data
            _save_presets(presets)
            return web.json_response({"status": "ok", "presets": presets})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    @server.instance.routes.post("/fsd_lora/delete_preset")
    async def delete_preset(request):
        try:
            data = await request.json()
            name = data.get("name", "")
            if not name:
                return web.json_response({"status": "error", "message": "Missing name"}, status=400)
            presets = _load_presets()
            if name in presets:
                del presets[name]
                _save_presets(presets)
            return web.json_response({"status": "ok", "presets": presets})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    # ── UI State ───────────────────────────────────────────────────────

    UI_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lora_stack_ui_state.json")

    def _load_ui_state():
        if not os.path.exists(UI_STATE_FILE):
            return {}
        with open(UI_STATE_FILE, "r", encoding="utf-8") as f:
            return json.loads(f.read() or "{}")

    def _save_ui_state(data):
        with open(UI_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @server.instance.routes.post("/fsd_lora/set_ui_state")
    async def set_ui_state(request):
        try:
            data = await request.json()
            node_id = str(data.get("node_id", ""))
            gallery_id = data.get("gallery_id", "")
            state = data.get("state", {})
            if not gallery_id:
                return web.Response(status=400)
            key = gallery_id + "_" + node_id
            ui_states = _load_ui_state()
            if key not in ui_states:
                ui_states[key] = {}
            ui_states[key].update(state)
            _save_ui_state(ui_states)
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    @server.instance.routes.get("/fsd_lora/get_ui_state")
    async def get_ui_state(request):
        try:
            node_id = request.query.get("node_id", "")
            gallery_id = request.query.get("gallery_id", "")
            if not node_id or not gallery_id:
                return web.json_response({"error": "node_id or gallery_id required"}, status=400)
            key = gallery_id + "_" + node_id
            ui_states = _load_ui_state()
            return web.json_response(ui_states.get(key, {"is_collapsed": False}))
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)


__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "register_routes"]