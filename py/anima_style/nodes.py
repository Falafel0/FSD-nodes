import nodes
import re
from .artist_data import inject as anima_inject

# fsd_encode_prompts lives in top-level utils.py (available via sys.path in ComfyUI)
# Try multiple import paths for robustness
_fsd_encode_prompts = None
try:
    from utils import fsd_encode_prompts as _fsd_encode_prompts
except ImportError:
    try:
        from ...utils import fsd_encode_prompts as _fsd_encode_prompts
    except ImportError:
        pass


class AnimaStyleExplorer(nodes.CLIPTextEncode):
    """Original Anima Style Explorer — single artist browser with Fullet integration."""

    CATEGORY = "Anima"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                "text": ("STRING", {
                    "multiline": True,
                    "default": "1girl, masterpiece, best quality",
                }),
            },
        }


class FSD_AnimaMultiArtist:
    """Multi-artist injector — pipe-integrated. Artists are injected directly into the positive prompt by the JS browser."""

    CATEGORY = "Anima"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pipe": ("FSD_PIPE",),
                "positive": ("STRING", {
                    "multiline": True,
                    "default": "1girl, masterpiece, best quality",
                }),
                "negative": ("STRING", {
                    "multiline": True,
                    "default": "",
                }),
                "syntax_mode": (["ComfyUI", "A1111", "ComfyUI+"], {"default": "ComfyUI"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "add_at_prefix": ("BOOLEAN", {"default": True, "label_on": "@artist", "label_off": "artist"}),
            },
        }

    RETURN_TYPES = ("FSD_PIPE", "STRING")
    RETURN_NAMES = ("FSD_PIPE", "prompt")
    FUNCTION = "apply"
    DESCRIPTION = "Multi-artist browser — pick @artists via Browse Artists button, encoded into FSD pipe conditioning"

    def apply(self, pipe, positive, negative, syntax_mode, seed, add_at_prefix=True):
        p = pipe.copy()
        p["syntax_mode"] = syntax_mode
        p["seed"] = seed
        p["pos_text"] = positive
        p["neg_text"] = negative

        clip = p.get("clip")

        # ── ComfyUI mode: native CLIPTextEncode (1:1 match with FSD_Prompts behaviour) ──
        if syntax_mode == "ComfyUI" and clip is not None:
            if positive.strip():
                pos_cond = clip.encode_from_tokens_scheduled(clip.tokenize(positive))
            else:
                pos_cond = clip.encode_from_tokens_scheduled(clip.tokenize(""))
            if negative.strip():
                neg_cond = clip.encode_from_tokens_scheduled(clip.tokenize(negative))
            else:
                neg_cond = clip.encode_from_tokens_scheduled(clip.tokenize(""))
            p["positive"] = pos_cond
            p["negative"] = neg_cond
        elif _fsd_encode_prompts is not None:
            # ── A1111 / ComfyUI+ modes: full dynamic prompt parser ──
            pos_cond, neg_cond = _fsd_encode_prompts(
                p, clip, positive, negative, seed, syntax_mode
            )
            p["positive"] = pos_cond
            p["negative"] = neg_cond
        elif clip is not None:
            # ── Fallback: native encode if fsd_encode_prompts unavailable ──
            pos_cond = clip.encode_from_tokens_scheduled(clip.tokenize(positive or ""))
            neg_cond = clip.encode_from_tokens_scheduled(clip.tokenize(negative or ""))
            p["positive"] = pos_cond
            p["negative"] = neg_cond

        return (p, positive)


class FSD_AnimaMultiArtist_Simple:
    """Multi-artist injector — simple STRING version. Artists injected via Browse Artists button, pure passthrough."""

    CATEGORY = "Anima"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "positive": ("STRING", {
                    "multiline": True,
                    "default": "1girl, masterpiece, best quality",
                }),
                "negative": ("STRING", {
                    "multiline": True,
                    "default": "",
                }),
                "add_at_prefix": ("BOOLEAN", {"default": True, "label_on": "@artist", "label_off": "artist"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("positive", "negative")
    FUNCTION = "apply"
    DESCRIPTION = "Multi-artist browser — pick @artists via Browse Artists button, pure string I/O, no CLIP required"

    def apply(self, positive, negative, add_at_prefix=True):
        # Strip @ prefix from artist tags if add_at_prefix is False,
        # so downstream nodes that don't expect @-syntax get clean artist names
        if not add_at_prefix:
            positive = re.sub(r'@(\w[\w\s]*\w|\w)', r'\1', positive or "")
        return (positive, negative)


NODE_CLASS_MAPPINGS = {
    "AnimaStyleExplorer": AnimaStyleExplorer,
    "FSD_AnimaMultiArtist": FSD_AnimaMultiArtist,
    "FSD_AnimaMultiArtist_Simple": FSD_AnimaMultiArtist_Simple,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaStyleExplorer": "Anima Style Explorer",
    "FSD_AnimaMultiArtist": "Multi Artist (FSD Pipe)",
    "FSD_AnimaMultiArtist_Simple": "Multi Artist (Simple)",
}
