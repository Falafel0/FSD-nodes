"""
FSD Style Selector — вынесен из demonalone-styleselector-comfyui.
Предоставляет ноду DA_StyleSelector и API-роуты для выбора стилей.
"""

import os
import json
from aiohttp import web
import urllib.parse
from PIL import Image
import server

IMAGE_EXTENSIONS = frozenset(['.png', '.jpg', '.jpeg', '.webp'])

# === CONFIGURATION ===
# Корень проекта (на 2 уровня выше: py/style_selector/ → py/ → корень)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STYLE_DATABASES_DIR = os.path.join(_PROJECT_ROOT, "data", "style_databases")
UI_STATE_FILE = os.path.join(_PROJECT_ROOT, "data", "styleselector_ui_state.json")

# Cache for JSON styles per database
_styles_cache = {}
_styles_cache_time = {}


def get_available_databases():
    """Returns list of subfolder names within style_databases that contain styles.json and previews folder."""
    databases = []
    if not os.path.exists(STYLE_DATABASES_DIR):
        return databases
    for entry in os.scandir(STYLE_DATABASES_DIR):
        if entry.is_dir():
            db_path = entry.path
            json_path = os.path.join(db_path, "styles.json")
            previews_path = os.path.join(db_path, "previews")
            if os.path.isfile(json_path) and os.path.isdir(previews_path):
                databases.append(entry.name)
    return sorted(databases)


def get_database_paths(database_name):
    """
    Returns (previews_dir, json_path) for specified database.
    If database doesn't exist, returns paths for first available database (fallback).
    If no available databases, returns (None, None).
    """
    available = get_available_databases()
    if not available:
        return None, None
    if database_name not in available:
        database_name = available[0]  # fallback to first
    db_path = os.path.join(STYLE_DATABASES_DIR, database_name)
    previews_dir = os.path.join(db_path, "previews")
    json_path = os.path.join(db_path, "styles.json")
    return previews_dir, json_path


def load_styles_json(database_name, force=False):
    """Loads styles.json for specified database with caching."""
    _, json_path = get_database_paths(database_name)
    if not json_path or not os.path.exists(json_path):
        return {}
    try:
        mtime = os.path.getmtime(json_path)
        cache_key = database_name
        if not force and cache_key in _styles_cache and _styles_cache_time.get(cache_key) == mtime:
            return _styles_cache[cache_key]
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Normalize: single object → list
        if isinstance(data, dict):
            data = [data]
        styles = {}
        for item in data:
            name = item.get("name")
            if name:
                styles[name] = {
                    "positive": item.get("positive", ""),
                    "negative": item.get("negative_prompt", "")
                }
        _styles_cache[cache_key] = styles
        _styles_cache_time[cache_key] = mtime
        return styles
    except Exception as e:
        print(f"FSD_StyleSelector: Error loading styles.json for '{database_name}': {e}")
        return {}


def save_styles_json(database_name, styles_list):
    """Saves styles list to styles.json for specified database. Invalidates cache."""
    _, json_path = get_database_paths(database_name)
    if not json_path:
        return False
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(styles_list, f, indent=2, ensure_ascii=False)
        _styles_cache.pop(database_name, None)
        _styles_cache_time.pop(database_name, None)
        return True
    except Exception as e:
        print(f"FSD_StyleSelector: Error saving styles.json for '{database_name}': {e}")
        return False


def _scan_input_directory(input_dir):
    """Returns sorted list of image file names and dictionary of their mtimes."""
    if not input_dir or not os.path.exists(input_dir):
        return [], {}
    images = []
    mtimes = {}
    for entry in os.scandir(input_dir):
        if entry.is_file():
            ext = os.path.splitext(entry.name)[1].lower()
            if ext in IMAGE_EXTENSIONS:
                images.append(entry.name)
                try:
                    mtimes[entry.name] = entry.stat().st_mtime
                except OSError:
                    mtimes[entry.name] = 0
    return sorted(images, key=lambda x: x.lower()), mtimes


# === API Endpoints ===

@server.PromptServer.instance.routes.get("/styleselector/get_databases")
async def get_databases_endpoint(request):
    """Returns list of available style databases."""
    databases = get_available_databases()
    return web.json_response({"databases": databases})


@server.PromptServer.instance.routes.get("/styleselector/get_images")
async def get_images_endpoint(request):
    try:
        page = int(request.query.get('page', 1))
        per_page = int(request.query.get('per_page', 100))
        search = request.query.get('search', '').lower()
        database = request.query.get('database', '')
        force_reload = request.query.get('force', 'false').lower() == 'true'

        previews_dir, json_path = get_database_paths(database)
        if not previews_dir:
            return web.json_response({"images": [], "total_pages": 0, "current_page": 1, "source_folder": ""})

        all_images, mtimes = _scan_input_directory(previews_dir)
        all_images = sorted(all_images, key=lambda x: x.lower())

        styles_data = load_styles_json(database, force=force_reload)

        styled_with_previews = set()
        for img in all_images:
            styled_with_previews.add(os.path.splitext(img)[0].lower())

        all_images_set = set(all_images)
        combined_entries = list(all_images)
        for style_name in styles_data:
            if style_name.lower() not in styled_with_previews:
                combined_entries.append(style_name)

        combined_entries = sorted(combined_entries, key=lambda x: x.lower())

        if search:
            combined_entries = [e for e in combined_entries if search in e.lower()]

        total_images = len(combined_entries)
        total_pages = max(1, (total_images + per_page - 1) // per_page)
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        paginated_entries = combined_entries[start_index:end_index]

        image_info_list = []
        for entry in paginated_entries:
            if entry in all_images_set:
                img = entry
                encoded_name = urllib.parse.quote(img, safe='')
                width, height = 0, 0
                try:
                    full_path = os.path.join(previews_dir, img)
                    with Image.open(full_path) as img_opened:
                        width, height = img_opened.size
                except Exception:
                    pass

                mtime = mtimes.get(img, 0)
                style_name = os.path.splitext(img)[0]
                style_info = styles_data.get(style_name, {})
                style_positive = style_info.get("positive", "")
                style_negative = style_info.get("negative", "")

                image_info_list.append({
                    "name": img,
                    "original_name": img,
                    "preview_url": f"/styleselector/preview?filename={encoded_name}&database={database}&t={int(mtime)}",
                    "source": previews_dir,
                    "width": width,
                    "height": height,
                    "style_positive": style_positive,
                    "style_negative": style_negative,
                    "has_preview": True
                })
            else:
                style_name = entry
                style_info = styles_data.get(style_name, {})
                style_positive = style_info.get("positive", "")
                style_negative = style_info.get("negative", "")

                image_info_list.append({
                    "name": style_name,
                    "original_name": style_name,
                    "preview_url": "",
                    "source": previews_dir,
                    "width": 0,
                    "height": 0,
                    "style_positive": style_positive,
                    "style_negative": style_negative,
                    "has_preview": False
                })

        return web.json_response({
            "images": image_info_list,
            "folders": [],
            "total_pages": total_pages,
            "current_page": page,
            "source_folder": previews_dir
        })
    except Exception as e:
        import traceback
        print(f"Error in get_images_endpoint: {traceback.format_exc()}")
        return web.json_response({"error": str(e)}, status=500)


@server.PromptServer.instance.routes.get("/styleselector/preview")
async def get_preview_image(request):
    filename = request.query.get('filename')
    database = request.query.get('database', '')
    if not filename:
        return web.Response(status=400, text="Missing filename parameter")

    try:
        filename_decoded = urllib.parse.unquote(filename)
        if ".." in filename_decoded:
            return web.Response(status=403, text="Invalid filename")

        previews_dir, _ = get_database_paths(database)
        if not previews_dir:
            return web.Response(status=404, text="Database not found")

        image_path = os.path.normpath(os.path.join(previews_dir, filename_decoded))
        if not image_path.startswith(os.path.normpath(previews_dir)):
            return web.Response(status=403, text="Access denied")

        if os.path.exists(image_path) and os.path.isfile(image_path):
            return web.FileResponse(image_path, headers={
                'Cache-Control': 'public, max-age=3600'
            })
        else:
            return web.Response(status=404, text=f"Image '{filename_decoded}' not found.")
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@server.PromptServer.instance.routes.post("/styleselector/set_ui_state")
async def set_ui_state(request):
    try:
        data = await request.json()
        node_id = str(data.get("node_id"))
        gallery_id = data.get("gallery_id")
        state = data.get("state", {})

        if not gallery_id:
            return web.Response(status=400)

        node_key = f"{gallery_id}_{node_id}"

        ui_states = {}
        if os.path.exists(UI_STATE_FILE):
            try:
                with open(UI_STATE_FILE, 'r', encoding='utf-8') as f:
                    ui_states = json.load(f)
            except Exception as e:
                print(f"FSD_StyleSelector: Error reading UI state file: {e}")

        if not isinstance(state.get('selected_image'), list):
            state['selected_image'] = [state['selected_image']] if state.get('selected_image') else []

        if node_key not in ui_states:
            ui_states[node_key] = {}
        ui_states[node_key].update({k: v for k, v in state.items() if k != "selected_image"})
        selected_images = state.get('selected_image', [])
        if isinstance(selected_images, str):
            selected_images = [selected_images]
        ui_states[node_key]['selected_image'] = selected_images

        if 'selected_database' in state:
            ui_states[node_key]['selected_database'] = state['selected_database']

        try:
            with open(UI_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(ui_states, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"FSD_StyleSelector: Error writing UI state file: {e}")
            return web.json_response({"status": "error", "message": "Failed to save state"}, status=500)

        return web.json_response({"status": "ok"})
    except Exception as e:
        print(f"FSD_StyleSelector: Exception in set_ui_state: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)


@server.PromptServer.instance.routes.post("/styleselector/save_style")
async def save_style_endpoint(request):
    try:
        data = await request.json()
        database = data.get("database", "")
        name = data.get("name", "").strip()
        positive = data.get("positive", "")
        negative = data.get("negative", "")

        if not database:
            return web.json_response({"status": "error", "message": "No database specified"}, status=400)
        if not name:
            return web.json_response({"status": "error", "message": "Style name cannot be empty"}, status=400)

        _, json_path = get_database_paths(database)
        if not json_path:
            return web.json_response({"status": "error", "message": f"Database '{database}' not found"}, status=404)

        existing = []
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                if isinstance(existing, dict):
                    existing = [existing]
            except Exception:
                existing = []

        updated = False
        for item in existing:
            if item.get("name") == name:
                item["positive"] = positive
                item["negative_prompt"] = negative
                updated = True
                break

        if not updated:
            existing.append({
                "name": name,
                "positive": positive,
                "negative_prompt": negative
            })

        if save_styles_json(database, existing):
            return web.json_response({"status": "ok", "updated": updated})
        else:
            return web.json_response({"status": "error", "message": "Failed to save file"}, status=500)
    except Exception as e:
        print(f"FSD_StyleSelector: Exception in save_style_endpoint: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)


@server.PromptServer.instance.routes.post("/styleselector/create_database")
async def create_database_endpoint(request):
    try:
        data = await request.json()
        name = data.get("name", "").strip()
        if not name:
            return web.json_response({"status": "error", "message": "Database name cannot be empty"}, status=400)
        safe_name = "".join(c for c in name if c.isalnum() or c in "_-")
        if not safe_name:
            return web.json_response({"status": "error", "message": "Invalid database name"}, status=400)
        db_path = os.path.join(STYLE_DATABASES_DIR, safe_name)
        if os.path.exists(db_path):
            return web.json_response({"status": "error", "message": "Database already exists"}, status=409)
        os.makedirs(os.path.join(db_path, "previews"))
        with open(os.path.join(db_path, "styles.json"), 'w', encoding='utf-8') as f:
            json.dump([], f)
        return web.json_response({"status": "ok", "name": safe_name})
    except Exception as e:
        print(f"FSD_StyleSelector: Exception in create_database_endpoint: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)


@server.PromptServer.instance.routes.post("/styleselector/upload_preview")
async def upload_preview_endpoint(request):
    try:
        reader = await request.multipart()
        field = await reader.next()
        if not field:
            return web.json_response({"status": "error", "message": "No file uploaded"}, status=400)

        database = ""
        style_name = ""
        file_data = None
        filename = ""

        while field is not None:
            if field.name == "database":
                database = (await field.read()).decode().strip()
            elif field.name == "style_name":
                style_name = (await field.read()).decode().strip()
            elif field.name == "file":
                file_data = await field.read()
                filename = field.filename or ""
            field = await reader.next()

        if not database or not style_name or file_data is None:
            return web.json_response({"status": "error", "message": "Missing database, style_name or file"}, status=400)
        if not style_name:
            return web.json_response({"status": "error", "message": "Style name cannot be empty"}, status=400)

        _, json_path = get_database_paths(database)
        if not json_path:
            return web.json_response({"status": "error", "message": "Database not found"}, status=404)

        ext = os.path.splitext(filename)[1].lower()
        if ext not in IMAGE_EXTENSIONS:
            return web.json_response({"status": "error", "message": f"Unsupported format: {ext}"}, status=400)

        previews_dir = os.path.join(os.path.dirname(json_path), "previews")
        save_path = os.path.join(previews_dir, style_name + ext)

        for old_ext in IMAGE_EXTENSIONS:
            old_path = os.path.join(previews_dir, style_name + old_ext)
            if old_path != save_path and os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass

        with open(save_path, 'wb') as f:
            f.write(file_data)

        return web.json_response({"status": "ok", "filename": style_name + ext})
    except Exception as e:
        print(f"FSD_StyleSelector: Exception in upload_preview_endpoint: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)


@server.PromptServer.instance.routes.post("/styleselector/delete_style")
async def delete_style_endpoint(request):
    try:
        data = await request.json()
        database = data.get("database", "")
        name = data.get("name", "").strip()
        if not database or not name:
            return web.json_response({"status": "error", "message": "Missing database or name"}, status=400)

        _, json_path = get_database_paths(database)
        if not json_path or not os.path.exists(json_path):
            return web.json_response({"status": "error", "message": "Database not found"}, status=404)

        existing = []
        with open(json_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        if isinstance(existing, dict):
            existing = [existing]

        new_list = [item for item in existing if item.get("name") != name]
        if len(new_list) == len(existing):
            return web.json_response({"status": "error", "message": "Style not found"}, status=404)

        save_styles_json(database, new_list)

        previews_dir = os.path.join(os.path.dirname(json_path), "previews")
        for ext in IMAGE_EXTENSIONS:
            img_path = os.path.join(previews_dir, name + ext)
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except OSError:
                    pass

        return web.json_response({"status": "ok"})
    except Exception as e:
        print(f"FSD_StyleSelector: Exception in delete_style_endpoint: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)


@server.PromptServer.instance.routes.post("/styleselector/delete_database")
async def delete_database_endpoint(request):
    try:
        data = await request.json()
        database = data.get("database", "").strip()
        if not database:
            return web.json_response({"status": "error", "message": "Missing database"}, status=400)

        db_path = os.path.join(STYLE_DATABASES_DIR, database)
        if not os.path.exists(db_path):
            return web.json_response({"status": "error", "message": "Database not found"}, status=404)

        norm_db = os.path.normpath(db_path)
        norm_parent = os.path.normpath(STYLE_DATABASES_DIR)
        if not norm_db.startswith(norm_parent + os.sep) or norm_db == norm_parent:
            return web.json_response({"status": "error", "message": "Invalid database path"}, status=403)

        import shutil
        shutil.rmtree(norm_db)

        _styles_cache.pop(database, None)
        _styles_cache_time.pop(database, None)

        return web.json_response({"status": "ok"})
    except Exception as e:
        print(f"FSD_StyleSelector: Exception in delete_database_endpoint: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)


@server.PromptServer.instance.routes.get("/styleselector/get_ui_state")
async def get_ui_state(request):
    try:
        node_id = request.query.get('node_id')
        gallery_id = request.query.get('gallery_id')

        if not node_id or not gallery_id:
            return web.json_response({"error": "node_id or gallery_id is required"}, status=400)

        node_key = f"{gallery_id}_{node_id}"

        if os.path.exists(UI_STATE_FILE):
            with open(UI_STATE_FILE, 'r', encoding='utf-8') as f:
                ui_states = json.load(f)
        else:
            return web.json_response({"selected_image": [], "sort_order": "name", "preview_size": 110, "selected_database": ""})

        node_state = ui_states.get(node_key, {})
        raw_selected = node_state.get("selected_image", "")
        if not isinstance(raw_selected, list):
            if raw_selected and isinstance(raw_selected, str) and raw_selected.strip():
                selected_list = [raw_selected]
            else:
                selected_list = []
        else:
            selected_list = raw_selected

        state_obj = {
            "selected_image": selected_list,
            "sort_order": node_state.get("sort_order", "name"),
            "preview_size": node_state.get("preview_size", 110),
            "selected_database": node_state.get("selected_database", ""),
            "apply_mode": node_state.get("apply_mode", "append")
        }

        return web.json_response(state_obj)
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)


class DA_StyleSelector:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "positive": ("STRING", {"forceInput": True, "default": ""}),
                "negative": ("STRING", {"forceInput": True, "default": ""}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "selected_image": ("STRING", {"default": ""}),
                "database": ("STRING", {"default": ""}),
                "apply_mode": (["append", "prepend", "replace"],),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("positive", "negative")
    FUNCTION = "load_style"
    CATEGORY = "Style selector"

    @classmethod
    def IS_CHANGED(cls, selected_image="", database="", apply_mode="append", **kwargs):
        base = f"{database}_{selected_image}_{apply_mode}"
        # Check mtime of all referenced databases
        mtimestamps = []
        available = get_available_databases()
        raw = str(selected_image) if selected_image else ""

        if ':' in raw:
            for chunk in raw.split(';'):
                if ':' in chunk:
                    db_part = chunk.split(':', 1)[0].strip()
                    if db_part in available:
                        _, json_path = get_database_paths(db_part)
                        if json_path and os.path.exists(json_path):
                            try:
                                mtimestamps.append(str(os.path.getmtime(json_path)))
                            except OSError:
                                pass
        elif database and database in available:
            _, json_path = get_database_paths(database)
            if json_path and os.path.exists(json_path):
                try:
                    mtimestamps.append(str(os.path.getmtime(json_path)))
                except OSError:
                    pass

        return f"{base}_{'_'.join(mtimestamps)}"

    @classmethod
    def VALIDATE_INPUTS(cls, selected_image="", database="", **kwargs):
        if not selected_image:
            return True
        available = get_available_databases()
        raw = str(selected_image) if selected_image else ""

        # Multi-db or single-db format?
        if ':' in raw:
            for chunk in raw.split(';'):
                if ':' not in chunk:
                    continue
                db_part, styles_part = chunk.split(':', 1)
                db_part = db_part.strip()
                if db_part not in available:
                    return f"Database '{db_part}' not available"
                previews_dir, _ = get_database_paths(db_part)
                if not previews_dir:
                    return f"Database '{db_part}' previews folder missing"
                styles_list = load_styles_json(db_part)
                for img in styles_part.split(','):
                    img = img.strip()
                    if not img:
                        continue
                    image_path = os.path.normpath(os.path.join(previews_dir, img))
                    if not image_path.startswith(os.path.normpath(previews_dir)):
                        return f"Invalid image path: {img}"
                    if not os.path.exists(image_path):
                        style_name = os.path.splitext(img)[0] if '.' in img else img
                        if style_name not in styles_list:
                            return f"Style not found: {img}"
            return True

        # Old single-db format
        if database not in available:
            return f"Database '{database}' not available"
        previews_dir, _ = get_database_paths(database)
        if not previews_dir:
            return "Database previews folder missing"

        images_list = [i.strip() for i in raw.split(',') if i.strip()]
        for img in images_list:
            image_path = os.path.normpath(os.path.join(previews_dir, img))
            if not image_path.startswith(os.path.normpath(previews_dir)):
                return f"Invalid image path: {img}"
            if not os.path.exists(image_path):
                style_name = os.path.splitext(img)[0] if '.' in img else img
                styles = load_styles_json(database)
                if style_name not in styles:
                    return f"Style not found: {img}"
        return True

    def load_style(self, unique_id, positive="", negative="", selected_image="", database="", apply_mode="append", **kwargs):
        positive = positive or ""
        negative = negative or ""

        available = get_available_databases()

        # Parse selected_image — supports two formats:
        #   NEW: "db1:style1,style2;db2:style3,style4"
        #   OLD: "style1,style2" (uses single `database` param)
        db_selections = {}  # {db_name: [style_names]}
        if isinstance(selected_image, str) and selected_image.strip():
            raw = selected_image.strip()
            if ':' in raw:
                # New multi-db format
                for chunk in raw.split(';'):
                    chunk = chunk.strip()
                    if ':' in chunk:
                        db_part, styles_part = chunk.split(':', 1)
                        db_part = db_part.strip()
                        styles_part = styles_part.strip()
                        if db_part and styles_part:
                            db_selections[db_part] = [s.strip() for s in styles_part.split(',') if s.strip()]
            else:
                # Old format: single db
                if database and database in available:
                    db_selections[database] = [s.strip() for s in raw.split(',') if s.strip()]
                elif available:
                    db_selections[available[0]] = [s.strip() for s in raw.split(',') if s.strip()]
        elif isinstance(selected_image, dict):
            # JS may send as JSON object
            for db_name, style_list in selected_image.items():
                if db_name in available and isinstance(style_list, list):
                    db_selections[db_name] = style_list

        if not db_selections:
            return (positive, negative)

        positive_additions = []
        negative_additions = []

        for db_name, style_names in db_selections.items():
            styles = load_styles_json(db_name)
            previews_dir, _ = get_database_paths(db_name)
            if not previews_dir:
                continue

            for img_name in style_names:
                full_path = os.path.normpath(os.path.join(previews_dir, img_name))
                if not full_path.startswith(os.path.normpath(previews_dir)):
                    continue

                if os.path.exists(full_path):
                    style_name, _ = os.path.splitext(img_name)
                else:
                    style_name = os.path.splitext(img_name)[0] if '.' in img_name else img_name

                style = styles.get(style_name)
                if style:
                    if style.get("positive"):
                        positive_additions.append(style["positive"])
                    if style.get("negative"):
                        negative_additions.append(style["negative"])
                else:
                    print(f"DA_StyleSelector: Style '{style_name}' not found in styles.json of database '{db_name}'")

        style_positive = ", ".join(positive_additions) if positive_additions else ""
        style_negative = ", ".join(negative_additions) if negative_additions else ""

        if apply_mode == "replace":
            result_positive = style_positive
            result_negative = style_negative
        elif apply_mode == "prepend":
            result_positive = style_positive
            if positive:
                result_positive = (result_positive + ", " + positive) if result_positive else positive
            result_negative = style_negative
            if negative:
                result_negative = (result_negative + ", " + negative) if result_negative else negative
        else:  # append (default)
            result_positive = positive
            if style_positive:
                result_positive = (result_positive + ", " + style_positive) if result_positive else style_positive
            result_negative = negative
            if style_negative:
                result_negative = (result_negative + ", " + style_negative) if result_negative else style_negative

        return (result_positive, result_negative)


NODE_CLASS_MAPPINGS = {
    "DA_StyleSelector": DA_StyleSelector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DA_StyleSelector": "Style Selector",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
