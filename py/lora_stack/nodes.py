"""FSD_LoraStack — pipe-integrated advanced LoRA stack with gallery UI."""

import json
import nodes
from .metadata import load_metadata


class FSD_LoraStack:
    """Stack multiple LoRAs onto a pipe with individual strengths and trigger words."""

    CATEGORY = "FSD Pipe/Conditioning"
    DESCRIPTION = "Advanced LoRA stack — browse/select local LoRAs with gallery, sync CivitAI metadata, preview images, trigger words"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"pipe": ("FSD_PIPE",)},
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "selection_data": ("STRING", {"default": "[]", "multiline": True, "forceInput": True}),
            },
        }

    RETURN_TYPES = ("FSD_PIPE", "STRING")
    RETURN_NAMES = ("FSD_PIPE", "trigger_words")
    FUNCTION = "apply_loras"

    def _get_triggers_for_lora(self, lora_meta, config):
        """Return selected trigger words for a LoRA based on config.

        If 'selected_triggers' is present and non-empty, use only those words.
        Otherwise, return all trigger_words (backward compatibility).
        """
        all_triggers_raw = lora_meta.get("trigger_words", "").strip()
        if not all_triggers_raw:
            return []

        # Parse all trigger words: split by comma, strip each
        all_triggers = [t.strip() for t in all_triggers_raw.split(",") if t.strip()]

        selected = config.get("selected_triggers", None)
        if selected and isinstance(selected, list) and len(selected) > 0:
            # Filter to only selected triggers that exist in all_triggers
            selected_set = set(s.strip() for s in selected if s.strip())
            return [t for t in all_triggers if t in selected_set]

        return all_triggers

    def apply_loras(self, pipe, unique_id, selection_data="[]", **kwargs):
        p = pipe.copy()
        model = p.get("model")
        clip = p.get("clip")

        try:
            lora_configs = json.loads(selection_data)
        except (json.JSONDecodeError, TypeError):
            lora_configs = []

        if not isinstance(lora_configs, list):
            lora_configs = []

        all_metadata = load_metadata()
        trigger_words_list = []
        inject_phrases = []
        applied = 0

        for config in lora_configs:
            if not isinstance(config, dict):
                continue
            if not config.get("on", True):
                continue

            lora_name = config.get("lora", "")
            if not lora_name:
                continue

            # Collect trigger words if enabled
            if config.get("use_trigger", True):
                lora_meta = all_metadata.get(lora_name, {})
                selected_triggers = self._get_triggers_for_lora(lora_meta, config)
                if selected_triggers:
                    triggers_str = ", ".join(selected_triggers)
                    trigger_words_list.append(triggers_str)
                    inject_phrases.append(triggers_str)

            strength_model = float(config.get("strength", 1.0))
            strength_clip = float(config.get("strength_clip", strength_model))

            if strength_model == 0 and strength_clip == 0:
                continue

            try:
                lora_loader = nodes.NODE_CLASS_MAPPINGS["LoraLoader"]()
                model, clip = lora_loader.load_lora(
                    model, clip, lora_name, strength_model, strength_clip
                )
                applied += 1
            except Exception:
                continue

        p["model"] = model
        p["clip"] = clip

        # Inject trigger words into positive prompt and re-encode conditioning
        if inject_phrases:
            current_pos = (p.get("pos_text") or "").strip()
            trigger_text = ", ".join(inject_phrases)
            if current_pos:
                p["pos_text"] = current_pos + ", " + trigger_text
            else:
                p["pos_text"] = trigger_text

            # Re-encode positive conditioning with the updated pos_text
            if clip is not None and p.get("pos_text"):
                syntax_mode = p.get("syntax_mode", "ComfyUI")
                if syntax_mode == "ComfyUI":
                    p["positive"] = clip.encode_from_tokens_scheduled(
                        clip.tokenize(p["pos_text"] or "")
                    )
                else:
                    # For A1111/ComfyUI+ modes, use dynamic prompt parser
                    try:
                        from ...utils import fsd_encode_prompts
                        pos_cond, _ = fsd_encode_prompts(
                            p, clip, p["pos_text"], p.get("neg_text", "") or "",
                            p.get("seed", 0), syntax_mode
                        )
                        p["positive"] = pos_cond
                    except ImportError:
                        # Fallback: encode without scheduling
                        p["positive"] = clip.encode_from_tokens_scheduled(
                            clip.tokenize(p["pos_text"] or "")
                        )

        return (p, ", ".join(trigger_words_list))