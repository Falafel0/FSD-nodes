"""Safetensors header reader + local JSON metadata store for LoRA Stack."""

import os
import json
import struct
import hashlib
import folder_paths

# ── Metadata file (same pattern as LocalLoraGallery) ─────────────────

METADATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lora_stack_metadata.json")


def load_metadata():
    if not os.path.exists(METADATA_FILE):
        return {}
    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            if not content:
                return {}
            return json.loads(content)
    except Exception:
        return {}


def save_metadata(data):
    try:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ── Safetensors header ───────────────────────────────────────────────

def _read_safetensors_header(filepath):
    with open(filepath, "rb") as f:
        length_bytes = f.read(8)
        if len(length_bytes) < 8:
            return {}
        header_len = struct.unpack("<Q", length_bytes)[0]
        header_str = f.read(header_len).decode("utf-8")
        return json.loads(header_str)


def extract_trigger_words(metadata):
    """Extract trigger words from safetensors __metadata__."""
    if not metadata:
        return []
    tag_freq = metadata.get("ss_tag_frequency_0") or metadata.get("ss_tag_frequency")
    if tag_freq and isinstance(tag_freq, str):
        try:
            tag_freq = json.loads(tag_freq)
        except json.JSONDecodeError:
            pass
    if isinstance(tag_freq, dict):
        return list(tag_freq.keys())
    trained = metadata.get("trainedWords") or metadata.get("trained_words")
    if trained and isinstance(trained, str):
        words = [w.strip() for w in trained.replace(",", " ").split() if w.strip()]
        if words:
            return words
    tags = metadata.get("tags")
    if tags and isinstance(tags, str):
        words = [w.strip() for w in tags.replace(",", " ").split() if w.strip()]
        if words:
            return words
    activation = metadata.get("activation_text")
    if activation and isinstance(activation, str):
        return [activation.strip()]
    return []


def read_safetensors_meta(lora_filename):
    """Read safetensors metadata and return {base_model, trigger_words, raw_meta}."""
    lora_path = folder_paths.get_full_path("loras", lora_filename)
    if not lora_path:
        return None
    try:
        header = _read_safetensors_header(lora_path)
    except Exception:
        return None
    raw = header.get("__metadata__", {})
    return {
        "base_model": raw.get("ss_base_model_version", raw.get("modelspec.architecture", "")),
        "trigger_words": extract_trigger_words(raw),
        "raw_meta": raw,
    }


# ── Hash ─────────────────────────────────────────────────────────────

def calculate_sha256(filepath):
    if not os.path.exists(filepath):
        return None
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()