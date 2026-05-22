"""CivitAI integration — hash-based LoRA metadata sync + preview download."""

import os
import urllib.request
import urllib.parse
import json
from urllib.parse import urlparse

import folder_paths
from .metadata import calculate_sha256, load_metadata, save_metadata

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
API_BASE = "https://civitai.com/api/v1"
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".avi")
REQUEST_TIMEOUT = 20


def _api_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _download_file(url, save_path):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Referer": "https://civitai.com/"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(save_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
        return True
    except Exception:
        return False


def sync_lora_metadata(lora_name):
    """Sync a local LoRA with CivitAI by SHA256 hash.

    Returns dict: {status: "ok", metadata: {preview_url, preview_type, trigger_words, download_url, tags}}
    """
    lora_full_path = folder_paths.get_full_path("loras", lora_name)
    if not lora_full_path:
        return {"status": "error", "message": "LoRA file not found"}

    metadata = load_metadata()
    lora_meta = metadata.get(lora_name, {})

    # Calculate hash if missing
    model_hash = lora_meta.get("hash")
    if not model_hash:
        model_hash = calculate_sha256(lora_full_path)
        if not model_hash:
            return {"status": "error", "message": "Failed to calculate hash"}
        lora_meta["hash"] = model_hash
        metadata[lora_name] = lora_meta
        save_metadata(metadata)

    # Lookup by hash
    version_url = API_BASE + "/model-versions/by-hash/" + model_hash
    version_data = _api_get(version_url)
    if not version_data:
        return {"status": "error", "message": "Model not found on CivitAI"}

    # Download preview
    images = version_data.get("images", [])
    preview_url = None
    preview_type = "none"

    if images:
        preview = next((img for img in images if img.get("type") == "image"), images[0])
        raw_url = preview.get("url")
        is_video = preview.get("type") == "video"

        if raw_url:
            # Build download URL
            if is_video:
                dl_url = raw_url.replace("/original=true/", "/transcode=true,width=450/")
                dl_url = os.path.splitext(dl_url)[0] + ".webm"
                file_ext = ".webm"
            else:
                if "/original=true/" in raw_url:
                    dl_url = raw_url.replace("/original=true/", "/width=450/")
                else:
                    dl_url = raw_url + "/width=450"
                parsed = urlparse(dl_url)
                file_ext = os.path.splitext(parsed.path)[1]
                if not file_ext or file_ext.lower() not in IMAGE_EXTENSIONS:
                    file_ext = ".jpg"

            lora_dir = os.path.dirname(lora_full_path)
            lora_basename = os.path.splitext(os.path.basename(lora_full_path))[0]
            save_path = os.path.join(lora_dir, lora_basename + file_ext)

            if _download_file(dl_url, save_path):
                # Build preview URL for frontend
                encoded_lora = urllib.parse.quote_plus(lora_name)
                encoded_file = urllib.parse.quote_plus(os.path.basename(save_path))
                preview_url = "/fsd_lora/preview?filename=" + encoded_file + "&lora_name=" + encoded_lora
                preview_type = "video" if is_video else "image"

    # Extract trigger words
    trained_words = version_data.get("trainedWords", [])
    if trained_words:
        lora_meta["trigger_words"] = ", ".join(trained_words)

    # Extract base model from CivitAI (e.g. "SD 1.5", "SDXL 1.0", "Pony", "Flux.1 D")
    base_model = version_data.get("baseModel", "")
    if base_model:
        lora_meta["base_model"] = base_model

    # Save tags from CivitAI if available
    civitai_tags = version_data.get("tags", [])
    if civitai_tags:
        lora_meta["tags"] = civitai_tags

    # Download URL
    model_id = version_data.get("modelId")
    if model_id:
        lora_meta["download_url"] = "https://civitai.com/models/" + str(model_id)

    metadata[lora_name] = lora_meta
    save_metadata(metadata)

    return {
        "status": "ok",
        "metadata": {
            "preview_url": preview_url or "",
            "preview_type": preview_type,
            "trigger_words": lora_meta.get("trigger_words", ""),
            "download_url": lora_meta.get("download_url", ""),
            "tags": lora_meta.get("tags", []),
            "base_model": lora_meta.get("base_model", ""),
        },
    }