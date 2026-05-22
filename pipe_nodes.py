from .utils import *
from contextlib import nullcontext

#[FSD/0. Native Bridges — wraps ComfyUI built-in loaders/generators]
# ==========================================
class FSD_NativeCheckpointLoader:
    """Wraps native CheckpointLoaderSimple — pipe output for full compatibility."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"ckpt_name": (folder_paths.get_filename_list("checkpoints"),)}}
    RETURN_TYPES = ("FSD_PIPE", "MODEL", "CLIP", "VAE")
    RETURN_NAMES = ("FSD_PIPE", "MODEL", "CLIP", "VAE")
    FUNCTION = "load"; CATEGORY = "FSD Pipe/Setup"
    DESCRIPTION = "Load a checkpoint model directly (bypasses pipe)"

    def load(self, ckpt_name):
        ckpt_path = folder_paths.get_full_path("checkpoints", ckpt_name)
        model, clip, vae = comfy.sd.load_checkpoint_guess_config(
            ckpt_path, output_vae=True, output_clip=True,
            embedding_directory=folder_paths.get_folder_paths("embeddings")
        )[:3]
        pipe = {
            "model": model, "clip": clip, "vae": vae,
            "target_width": 512, "target_height": 512,
            "steps": 20, "cfg": 7.0, "sampler_name": "euler", "scheduler": "normal",
            "denoise": 1.0,
            "positive": [], "negative": [],
            "syntax_mode": "ComfyUI", "seed": 0
        }
        return (pipe, model, clip, vae)

class FSD_NativeVAELoader:
    """Wraps native VAELoader — outputs VAE + pipable."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"vae_name": (folder_paths.get_filename_list("vae"),)}}
    RETURN_TYPES = ("VAE",); FUNCTION = "load"; CATEGORY = "FSD Pipe/Setup"
    DESCRIPTION = "Load a VAE model directly (bypasses pipe)"
    def load(self, vae_name):
        vae_path = folder_paths.get_full_path("vae", vae_name)
        vae = comfy.sd.VAE(sd=comfy.utils.load_torch_file(vae_path))
        return (vae,)

class FSD_NativeEmptyLatent:
    """Wraps native EmptyLatentImage — creates empty latent tensor."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"width": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 8}), "height": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 8}), "batch_size": ("INT", {"default": 1, "min": 1, "max": 64})}}
    RETURN_TYPES = ("LATENT", "FSD_PIPE")
    RETURN_NAMES = ("LATENT", "FSD_PIPE")
    FUNCTION = "generate"; CATEGORY = "FSD Pipe/Setup"
    DESCRIPTION = "Create an empty latent tensor with given dimensions and batch size"
    def generate(self, width, height, batch_size):
        latent = torch.zeros([batch_size, 4, height // 8, width // 8])
        pipe = {"target_width": width, "target_height": height, "batch_size": batch_size, "latent": latent}
        return ({"samples": latent}, pipe)

class FSD_TopPanel:
    @classmethod
    def INPUT_TYPES(s): 
        return {
            "required": {
                "ckpt_name": (folder_paths.get_filename_list("checkpoints"), ), 
                "vae_name": (["Automatic"] + folder_paths.get_filename_list("vae"),), 
                "clip_skip": ("INT", {"default": 1, "min": 1, "max": 12, "step": 1})
            },
            "optional": {
                "model_override": ("MODEL",),
                "clip_override": ("CLIP",),
                "vae_override": ("VAE",)
            }
        }
    RETURN_TYPES = ("FSD_PIPE",)
    FUNCTION = "load"
    CATEGORY = "FSD Pipe/Core"
    DESCRIPTION = "Load checkpoint + VAE into a pipe (model, clip, vae)"

    def load(self, ckpt_name, vae_name, clip_skip, model_override=None, clip_override=None, vae_override=None):
        if model_override is not None and clip_override is not None and vae_override is not None:
            model, clip, vae = model_override, clip_override, vae_override
        else:
            ckpt_path = folder_paths.get_full_path("checkpoints", ckpt_name)
            model_c, clip_c, vae_c = comfy.sd.load_checkpoint_guess_config(
                ckpt_path, output_vae=True, output_clip=True, 
                embedding_directory=folder_paths.get_folder_paths("embeddings")
            )[:3]
            model = model_override if model_override is not None else model_c
            clip = clip_override if clip_override is not None else clip_c
            vae = vae_override if vae_override is not None else vae_c

        if clip_skip > 1: 
            clip = clip.clone()
            clip.clip_layer(-(clip_skip))
            
        if vae_override is None and vae_name != "Automatic": 
            vae = comfy.sd.VAE(sd=comfy.utils.load_torch_file(folder_paths.get_full_path("vae", vae_name)))
            
        pipe = {
            "model": model, "clip": clip, "vae": vae,
            "target_width": 512, "target_height": 512,
            "steps": 20, "cfg": 7.0, "sampler_name": "euler", "scheduler": "normal",
            "denoise": 1.0,
            "positive":[], "negative":[],
            "syntax_mode": "ComfyUI", "seed": 0
        }
        return (pipe, )

class FSD_SamplerSettings:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "sampler_name": (comfy.samplers.KSampler.SAMPLERS, {"default": "dpmpp_2m"}), "scheduler": (comfy.samplers.KSampler.SCHEDULERS, {"default": "karras"}), "steps": ("INT", {"default": 20, "min": 1, "max": 150}), "cfg_scale": ("FLOAT", {"default": 7.0, "min": 1.0, "max": 30.0, "step": 0.5})}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "set"; CATEGORY = "FSD Pipe/Core"
    DESCRIPTION = "Configure sampler: steps, cfg, scheduler, sampler name"
    def set(self, pipe, sampler_name, scheduler, steps, cfg_scale):
        p = pipe.copy(); p["sampler_name"] = sampler_name; p["scheduler"] = scheduler; p["steps"] = steps; p["cfg"] = cfg_scale
        return (p, )

class FSD_DiffusionLoader:
    """SDXL-only: load diffusion model + CLIP from separate folders.
       Does NOT touch standard SD1.5 checkpoints."""
    @classmethod
    def INPUT_TYPES(s):
        diff_models = folder_paths.get_filename_list("diffusion_models")
        clips = folder_paths.get_filename_list("clip")
        return {
            "required": {
                "diffusion_model": (diff_models or ["(none)"],),
                "clip_model": (clips or ["(none)"],),
                "clip_skip": ("INT", {"default": 1, "min": 1, "max": 12, "step": 1}),
            },
            "optional": {
                "model_override": ("MODEL",),
                "clip_override": ("CLIP",),
            }
        }
    RETURN_TYPES = ("MODEL", "CLIP")
    RETURN_NAMES = ("MODEL", "CLIP")
    FUNCTION = "load_sdxl"
    CATEGORY = "FSD Pipe/Core"
    DESCRIPTION = "Load SDXL checkpoint with dual CLIP into a pipe"

    def load_sdxl(self, diffusion_model, clip_model, clip_skip,
                  model_override=None, clip_override=None):
        model = model_override
        clip = clip_override
        if model is None and diffusion_model not in ("", "(none)"):
            if "UNETLoader" in nodes.NODE_CLASS_MAPPINGS:
                model = nodes.NODE_CLASS_MAPPINGS["UNETLoader"]().load_unet(diffusion_model, "default")[0]
        if clip is None and clip_model not in ("", "(none)"):
            if "CLIPLoader" in nodes.NODE_CLASS_MAPPINGS:
                clip = nodes.NODE_CLASS_MAPPINGS["CLIPLoader"]().load_clip(clip_model)[0]
        if clip_skip > 1 and clip is not None:
            clip = clip.clone()
            clip.clip_layer(-(clip_skip))
        return (model, clip)

class FSD_AnimaLoader:
    """Autonomous loader for Anima/Cosmos models — diffusion model + CLIP + VAE into a fresh pipe."""
    @classmethod
    def INPUT_TYPES(s):
        diff_models = folder_paths.get_filename_list("diffusion_models")
        clips = folder_paths.get_filename_list("text_encoders")
        vaes = folder_paths.get_filename_list("vae")
        return {
            "required": {
                "diffusion_model": (diff_models or ["(none)"],),
                "clip_model": (clips or ["(none)"],),
                "clip_type": (["qwen_image", "cosmos", "stable_diffusion", "sd3", "flux2", "wan", "hidream", "lumina2", "pixart", "stable_cascade", "mochi", "ltxv", "stable_audio", "chroma", "ace", "omnigen2", "hunyuan_image", "ovis", "longcat_image", "cogvideox"],),
                "vae_name": (vaes or ["(none)"],),
                "weight_dtype": (["default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2"],),
                "clip_skip": ("INT", {"default": 1, "min": 1, "max": 12, "step": 1}),
            },
        }
    RETURN_TYPES = ("FSD_PIPE", "MODEL", "CLIP", "VAE")
    RETURN_NAMES = ("FSD_PIPE", "MODEL", "CLIP", "VAE")
    FUNCTION = "load_anima"
    CATEGORY = "FSD Pipe/Setup"
    DESCRIPTION = "Load Anima/Cosmos model: diffusion model + CLIP (with type) + VAE → fresh pipe"

    def load_anima(self, diffusion_model, clip_model, clip_type, vae_name, weight_dtype, clip_skip):
        model = None
        clip = None
        vae = None

        if diffusion_model not in ("", "(none)", None):
            if "UNETLoader" in nodes.NODE_CLASS_MAPPINGS:
                model = nodes.NODE_CLASS_MAPPINGS["UNETLoader"]().load_unet(diffusion_model, weight_dtype)[0]

        if clip_model not in ("", "(none)", None):
            if "CLIPLoader" in nodes.NODE_CLASS_MAPPINGS:
                clip = nodes.NODE_CLASS_MAPPINGS["CLIPLoader"]().load_clip(clip_model, type=clip_type)[0]

        if vae_name not in ("", "(none)", None):
            if "VAELoader" in nodes.NODE_CLASS_MAPPINGS:
                vae = nodes.NODE_CLASS_MAPPINGS["VAELoader"]().load_vae(vae_name)[0]

        if clip_skip > 1 and clip is not None:
            clip = clip.clone()
            clip.clip_layer(-(clip_skip))

        pipe = {
            "model": model, "clip": clip, "vae": vae,
            "positive": None, "negative": None,
            "latent": None, "image": None, "mask": None, "segs": None,
            "seed": 0,
            "cfg": 1.0,
            "guidance": 3.5,
        }

        return (pipe, model, clip, vae)

def _format_danbooru_tags(tags_str, replace_underscores=True, artist_prefix=True):
    """Format space-separated Danbooru tags into comma-separated prompt text.
    - replace_underscores: turn '_' into ' '
    - artist_prefix: add '@' before each tag (if artist_prefix is True, all tags get @)"""
    if not tags_str:
        return ""
    tags = tags_str.split(" ")
    formatted = []
    for tag in tags:
        tag = tag.strip()
        if not tag:
            continue
        if replace_underscores:
            tag = tag.replace("_", " ")
        if artist_prefix:
            tag = "@" + tag
        formatted.append(tag)
    return ", ".join(formatted)

class FSD_DanbooruGalleryPipe:
    """Danbooru Gallery — pipe-integrated. Browse & select images in the frontend gallery,
    inject selected tags into FSD pipe positive prompt (append or replace),
    download the selected image, return modified pipe."""

    CATEGORY = "FSD Pipe/Setup"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pipe": ("FSD_PIPE",),
                "prompt_mode": (["Append", "Replace"], {"default": "Append"}),
                "include_general": ("BOOLEAN", {"default": True}),
                "include_artist": ("BOOLEAN", {"default": True}),
                "include_character": ("BOOLEAN", {"default": True}),
                "include_copyright": ("BOOLEAN", {"default": False}),
                "include_meta": ("BOOLEAN", {"default": False}),
                "artist_prefix": ("BOOLEAN", {"default": True, "label_on": "@artist", "label_off": "artist"}),
                "replace_underscores": ("BOOLEAN", {"default": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
            "hidden": {
                "selection_data": ("STRING", {"default": "{}", "multiline": True, "forceInput": True}),
            },
        }

    RETURN_TYPES = ("FSD_PIPE", "IMAGE", "STRING")
    RETURN_NAMES = ("FSD_PIPE", "image", "prompt")
    FUNCTION = "apply"
    DESCRIPTION = "Danbooru Gallery — browse & select images, inject tags into FSD pipe positive prompt (append or replace)"

    def apply(self, pipe, prompt_mode, include_general, include_artist,
              include_character, include_copyright, include_meta,
              artist_prefix, replace_underscores, seed, selection_data="{}"):
        import json as _json
        import io as _io
        import urllib.request as _urllib_request
        import numpy as np
        from PIL import Image as PILImage

        p = pipe.copy()
        p["seed"] = seed

        # ── Parse selection data ──
        sel = _json.loads(selection_data or "{}")
        selections = sel.get("selections", [sel] if sel and "selections" not in sel else [])
        if not selections:
            # Nothing selected — pass pipe through, return empty image
            empty_img = torch.zeros(1, 1, 1, 3)
            return (p, empty_img, "")

        # ── Build tag string from selected posts ──
        all_tags = []
        images = []
        prompts_out = []

        for item in selections:
            tbc = item.get("tags_by_category", {})
            tags_parts = []
            if include_general:
                tags_parts.append(tbc.get("general", ""))
            if include_artist:
                tags_parts.append(tbc.get("artist", ""))
            if include_character:
                tags_parts.append(tbc.get("character", ""))
            if include_copyright:
                tags_parts.append(tbc.get("copyright", ""))
            if include_meta:
                tags_parts.append(tbc.get("meta", ""))

            combined = " ".join(p for p in tags_parts if p).strip()
            if not combined:
                combined = item.get("prompt", "")

            # Format tags
            formatted = _format_danbooru_tags(combined, replace_underscores, artist_prefix)
            all_tags.append(formatted)
            prompts_out.append(formatted)

            # ── Download image ──
            image_url = item.get("image_url")
            if image_url:
                try:
                    with _urllib_request.urlopen(image_url) as response:
                        img_data = response.read()
                    img = PILImage.open(_io.BytesIO(img_data)).convert("RGB")
                    img_array = np.array(img).astype(np.float32) / 255.0
                    tensor = torch.from_numpy(img_array)[None,]
                    images.append(tensor)
                except Exception:
                    images.append(torch.zeros(1, 1, 1, 3))
            else:
                images.append(torch.zeros(1, 1, 1, 3))

        # Combine all selected tags
        danbooru_tags = ", ".join(all_tags)
        prompt_out = ", ".join(prompts_out)

        # ── Modify pipe positive ──
        pipe_pos = p.get("pos_text", "") or ""
        if prompt_mode == "Replace":
            new_pos = danbooru_tags
        else:  # Append
            new_pos = (pipe_pos + ", " + danbooru_tags).strip(", ")

        p["pos_text"] = new_pos

        # ── Re-encode conditioning ──
        # Use same logic as FSD_Prompts: ComfyUI → native, A1111/ComfyUI+ → fsd_encode_prompts
        clip = p.get("clip")
        neg_text = p.get("neg_text", "") or ""
        syntax_mode = p.get("syntax_mode", "ComfyUI")

        if syntax_mode == "ComfyUI" and clip is not None:
            pos_cond = clip.encode_from_tokens_scheduled(clip.tokenize(new_pos or ""))
            neg_cond = clip.encode_from_tokens_scheduled(clip.tokenize(neg_text))
        else:
            try:
                pos_cond, neg_cond = fsd_encode_prompts(
                    p, clip, new_pos, neg_text, seed, syntax_mode
                )
            except NameError:
                # fsd_encode_prompts not available — fallback to native
                if clip is not None:
                    pos_cond = clip.encode_from_tokens_scheduled(clip.tokenize(new_pos or ""))
                    neg_cond = clip.encode_from_tokens_scheduled(clip.tokenize(neg_text))
                else:
                    pos_cond, neg_cond = [], []

        p["positive"] = pos_cond
        p["negative"] = neg_cond

        # ── Combine images (stack batch) or return first ──
        if images:
            out_image = torch.cat(images, dim=0) if len(images) > 1 else images[0]
        else:
            out_image = torch.zeros(1, 1, 1, 3)

        return (p, out_image, prompt_out)


class FSD_Dimensions:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "width": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 8}), "height": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 8}), "batch_size": ("INT", {"default": 1, "min": 1, "max": 64})}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "set"; CATEGORY = "FSD Pipe/Core"
    DESCRIPTION = "Set width, height and batch size in the pipe"
    def set(self, pipe, width, height, batch_size):
        p = pipe.copy()
        p["latent"] = {"samples": torch.zeros([batch_size, 4, height // 8, width // 8]), "downscale_ratio_spacial": 8}
        p["target_width"] = width; p["target_height"] = height; p["denoise"] = 1.0
        return (p, )

class FSD_Generate:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "pipe": ("FSD_PIPE",),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff})
            },
            "optional": {
                "latent_override": ("LATENT", ),
                "positive_prompt": ("STRING", {"multiline": True, "default": ""}),
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
                "prompt_mode": (["Replace", "Append", "If not empty"],),
            }
        }
    RETURN_TYPES = ("FSD_PIPE", "IMAGE", "LATENT")
    RETURN_NAMES = ("FSD_PIPE", "IMAGE", "LATENT")
    FUNCTION = "generate"
    CATEGORY = "FSD Pipe/Core"
    DESCRIPTION = "Run the KSampler using pipe settings. Optional prompt override re-encodes from text."

    def generate(self, pipe, seed, latent_override=None, positive_prompt="", negative_prompt="", prompt_mode="Replace"):
        p = pipe.copy()
        model, vae = p.get("model"), p.get("vae")
        latent = latent_override if latent_override is not None else p.get("latent")
        if latent is None:
            latent = {"samples": torch.zeros([1, 4, p.get("target_height", 512) // 8, p.get("target_width", 512) // 8]),
                       "downscale_ratio_spacial": 8}

        actual_seed = p.get("seed") if p.get("seed") is not None else seed

        # Resolve prompts — override from widgets if provided, else use pipe conditioning
        pos_str = (positive_prompt or "").strip()
        neg_str = (negative_prompt or "").strip()
        if pos_str or neg_str:
            pos, neg = fsd_resolve_prompts(p, positive_prompt, negative_prompt, prompt_mode)
        else:
            pos, neg = p.get("positive", []), p.get("negative", [])

        sample_res = nodes.common_ksampler(
            model=model, seed=actual_seed, steps=p.get("steps", 20), cfg=p.get("cfg", 7.0),
            sampler_name=p.get("sampler_name", "euler"), scheduler=p.get("scheduler", "normal"),
            positive=pos, negative=neg, latent=latent, denoise=p.get("denoise", 1.0)
        )
        p["latent"] = sample_res[0]; p["seed"] = actual_seed
        if vae is not None:
            p["image"] = nodes.NODE_CLASS_MAPPINGS["VAEDecode"]().decode(vae, sample_res[0])[0]
            return (p, p["image"], sample_res[0])
        return (p, torch.zeros((1, 64, 64, 3)), sample_res[0])

class FSD_SaveImage:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"image": ("IMAGE",), "filename_prefix": ("STRING", {"default": "FSD_output"})}, "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}}
    RETURN_TYPES = ()
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "FSD Pipe/Core"
    DESCRIPTION = "Decode latent and save as image via VAE"
    def save(self, image, filename_prefix, prompt=None, extra_pnginfo=None): 
        return nodes.NODE_CLASS_MAPPINGS["SaveImage"]().save_images(images=image, filename_prefix=filename_prefix, prompt=prompt, extra_pnginfo=extra_pnginfo)

# ==========================================
# [FSD/2. Conditioning] НОДА ПРОМПТА
# ==========================================
class FSD_Prompts:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "pipe": ("FSD_PIPE",),
                "positive": ("STRING", {"multiline": True, "default": ""}),
                "negative": ("STRING", {"multiline": True, "default": ""}),
                "syntax_mode": (["ComfyUI", "A1111", "ComfyUI+"], {"default": "ComfyUI"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff})
            },
            "optional": {
                "guidance": ("FLOAT", {"default": 3.5, "min": 0.0, "max": 100.0, "step": 0.1})
            }
        }
    RETURN_TYPES = ("FSD_PIPE",)
    FUNCTION = "encode"
    CATEGORY = "FSD Pipe/Conditioning"
    DESCRIPTION = "Encode positive and negative text prompts into conditioning"

    def encode(self, pipe, positive, negative, syntax_mode, seed, guidance=None):
        p = pipe.copy()
        p["syntax_mode"] = syntax_mode
        p["seed"] = seed
        p["pos_text"] = positive
        p["neg_text"] = negative
        if guidance is not None:
            p["guidance"] = guidance

        clip = p.get("clip")
        # ComfyUI mode uses native CLIPTextEncode (1:1 match), other modes use scheduling parser
        if syntax_mode == "ComfyUI" and clip is not None:
            if positive.strip():
                pos_cond = clip.encode_from_tokens_scheduled(clip.tokenize(positive))
            else:
                pos_cond = clip.encode_from_tokens_scheduled(clip.tokenize(""))
            if negative.strip():
                neg_cond = clip.encode_from_tokens_scheduled(clip.tokenize(negative))
            else:
                neg_cond = clip.encode_from_tokens_scheduled(clip.tokenize(""))
        else:
            pos_cond, neg_cond = fsd_encode_prompts(p, clip, positive, negative, seed, syntax_mode)
        p["positive"] = pos_cond
        p["negative"] = neg_cond
        return (p, )

class FSD_ControlNet:
    """Autonomous ControlNet: loads image, preprocesses, applies conditioning.
       Bypass toggle disables the node — pipe passes through unchanged."""
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        files = folder_paths.filter_files_content_types(files, ["image"])

        preprocessor_list = ["none"]
        _has_aux = False
        try:
            from comfyui_controlnet_aux import PREPROCESSOR_OPTIONS
            preprocessor_list = PREPROCESSOR_OPTIONS
            _has_aux = True
        except ImportError:
            pass

        return {
            "required": {
                "control_net_name": (folder_paths.get_filename_list("controlnet"),),
                "image": (sorted(files), {"image_upload": True}),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01}),
                "start_percent": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.001}),
                "end_percent": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.001}),
                "preprocessor": (preprocessor_list,),
                "resolution": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 8}),
                "bypass": ("BOOLEAN", {"default": False}),
                "bypass_hires": ("BOOLEAN", {"default": False, "tooltip": "Auto-bypass when pipe comes from HiresFix (second pass)"}),
                "bypass_sam3": ("BOOLEAN", {"default": False, "tooltip": "Auto-bypass when pipe comes from SAM3 Detailer"}),
            },
            "optional": {
                "pipe": ("FSD_PIPE",),
                "positive_override": ("CONDITIONING",),
                "negative_override": ("CONDITIONING",),
                "vae": ("VAE",),
                "control_net_override": ("CONTROL_NET",),
            }
        }
    RETURN_TYPES = ("FSD_PIPE", "CONDITIONING", "CONDITIONING", "IMAGE")
    RETURN_NAMES = ("FSD_PIPE", "POSITIVE", "NEGATIVE", "CONTROL_IMAGE")
    FUNCTION = "apply"; CATEGORY = "FSD Pipe/Conditioning"
    DESCRIPTION = "Autonomous ControlNet: load image, preprocess, apply conditioning. Toggle bypass to disable."

    def apply(self, control_net_name, image, strength, start_percent, end_percent, preprocessor, resolution, bypass, bypass_hires, bypass_sam3, pipe=None, positive_override=None, negative_override=None, vae=None, control_net_override=None):
        import numpy as np
        from PIL import Image, ImageOps

        # --- load image from disk ---
        image_path = folder_paths.get_annotated_filepath(image)
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        img_np = np.array(img).astype(np.float32) / 255.0
        img_tensor = torch.from_numpy(img_np)[None,]

        # --- preprocess ---
        if preprocessor != "none":
            try:
                from comfyui_controlnet_aux import AUX_NODE_MAPPINGS
                aux_class = AUX_NODE_MAPPINGS[preprocessor]
                aux_inputs = aux_class.INPUT_TYPES()
                aux_inputs = {**aux_inputs["required"], **(aux_inputs.get("optional") or {})}
                params = {}
                for name, input_type in aux_inputs.items():
                    if name == "image":
                        params[name] = img_tensor
                        continue
                    if name == "resolution":
                        params[name] = resolution
                        continue
                    if len(input_type) == 2 and "default" in input_type[1]:
                        params[name] = input_type[1]["default"]
                        continue
                    default_values = {"INT": 0, "FLOAT": 0.0}
                    if type(input_type[0]) is list:
                        for input_type_value in input_type[0]:
                            if input_type_value in default_values:
                                params[name] = default_values[input_type_value]
                    else:
                        if input_type[0] in default_values:
                            params[name] = default_values[input_type[0]]
                result = getattr(aux_class(), aux_class.FUNCTION)(**params)
                img_tensor = result[0] if isinstance(result, tuple) else result
            except ImportError:
                pass  # aux nodes not available — use raw image

        # --- pipe handling ---
        p = pipe.copy() if pipe else {}
        positive = positive_override if positive_override is not None else p.get("positive", [])
        negative = negative_override if negative_override is not None else p.get("negative", [])

        if bypass or (bypass_hires and p.get("_fsd_hires_active")) or (bypass_sam3 and p.get("_fsd_sam3_active")):
            p["positive"] = positive
            p["negative"] = negative
            return (p, positive, negative, img_tensor)

        # --- load controlnet & apply ---
        if control_net_override is not None:
            cnet = control_net_override
        else:
            cnet = nodes.ControlNetLoader().load_controlnet(control_net_name)[0]

        cnet_node = nodes.NODE_CLASS_MAPPINGS["ControlNetApplyAdvanced"]()
        new_pos, new_neg = cnet_node.apply_controlnet(positive, negative, cnet, img_tensor, strength, start_percent, end_percent, vae=vae)
        p["positive"], p["negative"] = new_pos, new_neg

        # Accumulate ControlNet data in pipe so downstream re-encodes can re-apply all
        cn_entry = {
            "control_net_name": control_net_name if control_net_override is None else None,
            "control_net_override": control_net_override,
            "image": img_tensor,
            "strength": strength,
            "start_percent": start_percent,
            "end_percent": end_percent,
            "vae": vae,
        }
        p.setdefault("_fsd_controlnet", []).append(cn_entry)
        return (p, new_pos, new_neg, img_tensor)


_IPADAPTER_CACHE = {}

class FSD_IPAdapter:
    """Autonomous IPAdapter: loads image, IPAdapter+CLIPVision models, applies to pipe.
       Two modes: Preset (auto-downloads known models) or Manual (custom files — NoobAI, etc.).
       Requires ComfyUI_IPAdapter_plus extension. Bypass toggle disables the node."""
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        files = folder_paths.filter_files_content_types(files, ["image"])

        has_ipadapter_plus = "IPAdapterUnifiedLoader" in nodes.NODE_CLASS_MAPPINGS
        presets = [
            'LIGHT - SD1.5 only (low strength)',
            'STANDARD (medium strength)',
            'VIT-G (medium strength)',
            'PLUS (high strength)',
            'PLUS FACE (portraits)',
            'FULL FACE - SD1.5 only (portraits stronger)',
        ]

        ipadapter_files = folder_paths.get_filename_list("ipadapter")
        clipvision_files = folder_paths.get_filename_list("clip_vision")

        result: dict = {
            "required": {
                "image": (sorted(files), {"image_upload": True}),
                "mode": (["Preset (auto)", "Manual (custom files)"],),
                "weight": ("FLOAT", {"default": 1.0, "min": -1.0, "max": 5.0, "step": 0.05}),
                "weight_type": (['linear', 'ease in', 'ease out', 'ease in-out', 'reverse in-out', 'weak input', 'weak output', 'weak middle', 'strong middle', 'style transfer', 'composition', 'strong style', 'style and composition', 'style and composition reverse'],),
                "start_at": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.001}),
                "end_at": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.001}),
                "combine_embeds": (["concat", "add", "subtract", "average", "norm average"],),
                "embeds_scaling": (['V only', 'K+V', 'K+V w/ C penalty', 'K+mean(V) w/ C penalty'],),
                "bypass": ("BOOLEAN", {"default": False}),
                "bypass_hires": ("BOOLEAN", {"default": False, "tooltip": "Auto-bypass when pipe comes from HiresFix (second pass)"}),
                "bypass_sam3": ("BOOLEAN", {"default": False, "tooltip": "Auto-bypass when pipe comes from SAM3 Detailer"}),
            },
            "optional": {
                "pipe": ("FSD_PIPE",),
                "attn_mask": ("MASK",),
                "image_negative": ("IMAGE",),
                "ipadapter_override": ("IPADAPTER",),
            }
        }

        if has_ipadapter_plus:
            result["required"]["preset"] = (presets,)
            result["required"]["ipadapter_file"] = (ipadapter_files or ["(none)"],)
            result["required"]["clip_vision_file"] = (clipvision_files or ["(none)"],)
            result["optional"]["clip_vision_override"] = ("CLIP_VISION",)

        return result

    RETURN_TYPES = ("FSD_PIPE", "MODEL")
    RETURN_NAMES = ("FSD_PIPE", "MODEL")
    FUNCTION = "apply"
    CATEGORY = "FSD Pipe/Conditioning"
    DESCRIPTION = "Autonomous IPAdapter: load image, choose Preset or Manual (custom models), apply to pipe. Toggle bypass to disable."

    def apply(self, image, mode, weight, weight_type, start_at, end_at, combine_embeds, embeds_scaling, bypass, bypass_hires, bypass_sam3, pipe=None, attn_mask=None, image_negative=None, preset=None, ipadapter_file=None, clip_vision_file=None, ipadapter_override=None, clip_vision_override=None, **kwargs):
        import numpy as np
        from PIL import Image, ImageOps

        # --- load image from disk ---
        image_path = folder_paths.get_annotated_filepath(image)
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        img_np = np.array(img).astype(np.float32) / 255.0
        img_tensor = torch.from_numpy(img_np)[None,]

        p = pipe.copy() if pipe else {}
        model = p.get("model")

        if model is None:
            raise RuntimeError("FSD_IPAdapter: model not found in pipe. Connect a pipe with a loaded model.")

        if bypass or (bypass_hires and p.get("_fsd_hires_active")) or (bypass_sam3 and p.get("_fsd_sam3_active")):
            return (p, model)

        # Store original model before patching — allows HiresFix/SAM3Detailer
        # to use the clean model (bypassing IPAdapter on second pass).
        if bypass_hires or bypass_sam3:
            p["_fsd_model_pre_ipadapter"] = model

        has_ipadapter_plus = "IPAdapterUnifiedLoader" in nodes.NODE_CLASS_MAPPINGS
        if not has_ipadapter_plus:
            raise RuntimeError(
                "FSD_IPAdapter: 'ComfyUI_IPAdapter_plus' extension is required.\n"
                "Install it via ComfyUI-Manager or from:\n"
                "https://github.com/cubiq/ComfyUI_IPAdapter_plus"
            )

        # --- determine IPAdapter pipeline ---
        if ipadapter_override is not None:
            # Pre-loaded full pipeline (from IPAdapterUnifiedLoader or similar)
            ipadapter_pipe = ipadapter_override
        elif mode == "Preset (auto)":
            # Auto-load via preset
            global _IPADAPTER_CACHE
            cache_key = f"preset:{preset}"
            if cache_key in _IPADAPTER_CACHE:
                loader = _IPADAPTER_CACHE[cache_key]
            else:
                loader = nodes.NODE_CLASS_MAPPINGS["IPAdapterUnifiedLoader"]()
                _IPADAPTER_CACHE[cache_key] = loader

            model, ipadapter_pipe = loader.load_models(model.clone(), preset)
        else:
            # Manual mode: load specific files
            if ipadapter_file is None or ipadapter_file in ("(none)", "", None):
                raise RuntimeError("FSD_IPAdapter (Manual): select an ipadapter_file or use Preset mode.")
            if clip_vision_override is not None:
                clip_vision = clip_vision_override
            elif clip_vision_file is None or clip_vision_file in ("(none)", "", None):
                raise RuntimeError("FSD_IPAdapter (Manual): select a clip_vision_file or connect clip_vision_override.")
            else:
                clip_path = folder_paths.get_full_path_or_raise("clip_vision", clip_vision_file)
                clip_vision = comfy.clip_vision.load(clip_path)
                if clip_vision is None:
                    raise RuntimeError(f"FSD_IPAdapter: invalid CLIP Vision file: {clip_vision_file}")

            ipa_path = folder_paths.get_full_path_or_raise("ipadapter", ipadapter_file)
            ipadapter_model = comfy.utils.load_torch_file(ipa_path, safe_load=True)
            # Unpack safetensors structure: image_proj + ip_adapter keys
            if ipa_path.lower().endswith(".safetensors"):
                st_model = {"image_proj": {}, "ip_adapter": {}}
                for key in ipadapter_model.keys():
                    if key.startswith("image_proj."):
                        st_model["image_proj"][key.replace("image_proj.", "")] = ipadapter_model[key]
                    elif key.startswith("ip_adapter."):
                        st_model["ip_adapter"][key.replace("ip_adapter.", "")] = ipadapter_model[key]
                ipadapter_model = st_model
            if "ip_adapter" not in ipadapter_model or not ipadapter_model["ip_adapter"]:
                raise RuntimeError(f"FSD_IPAdapter: invalid IPAdapter model file: {ipadapter_file}")

            ipadapter_pipe = {
                "clipvision": {"file": clip_vision_file, "model": clip_vision},
                "ipadapter": {"file": ipadapter_file, "model": ipadapter_model},
                "insightface": {"provider": None, "model": None},
            }

        # --- apply IPAdapter to model ---
        # IPAdapterAdvanced returns (model, face_image) — 2 values despite RETURN_TYPES=("MODEL",)
        advanced = nodes.NODE_CLASS_MAPPINGS["IPAdapterAdvanced"]()
        result = advanced.apply_ipadapter(
            model=model, ipadapter=ipadapter_pipe,
            image=img_tensor, weight=weight, weight_type=weight_type,
            start_at=start_at, end_at=end_at,
            combine_embeds=combine_embeds, embeds_scaling=embeds_scaling,
            attn_mask=attn_mask, image_negative=image_negative,
        )
        model = result[0]

        p["model"] = model
        return (p, model)


class FSD_ConditioningCombine:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe_dst": ("FSD_PIPE",), "pipe_src": ("FSD_PIPE",)}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "combine"; CATEGORY = "FSD Pipe/Conditioning"
    DESCRIPTION = "Merge two conditionings into one"
    def combine(self, pipe_dst, pipe_src):
        p = pipe_dst.copy()
        p["positive"] = p.get("positive",[]) + pipe_src.get("positive",[])
        p["negative"] = p.get("negative",[]) + pipe_src.get("negative",[])
        return (p, )

# ==========================================
#[FSD/3. Modifiers]
# ==========================================
class FSD_Img2Img:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "image": ("IMAGE",), "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}), "size_mode": (["Original Size", "Custom", "From Pipe (Dimensions)"],), "width": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 8}), "height": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 8}), "resize_mode": (["Just resize", "Crop and resize", "Resize and fill"],), "denoise": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "apply"; CATEGORY = "FSD Pipe/Image"
    DESCRIPTION = "Encode an input image into latent space for img2img"
    def apply(self, pipe, image, seed, size_mode, width, height, resize_mode, denoise):
        p = pipe.copy(); B, H, W, C = image.shape
        if size_mode == "Original Size": tw, th = int(W), int(H)
        elif size_mode == "Custom": tw, th = width, height
        else: tw, th = p.get("target_width", 512), p.get("target_height", 512)
        p["target_width"] = tw; p["target_height"] = th
        resized_image = fsd_resize(image, tw, th, resize_mode)
        p["latent"] = {"samples": nodes.NODE_CLASS_MAPPINGS["VAEEncode"]().encode(p["vae"], resized_image[:,:,:,:3])[0]["samples"]}
        p["denoise"] = denoise; p["seed"] = seed
        return (p, )

class FSD_Inpaint:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "pipe": ("FSD_PIPE",), 
            "image": ("IMAGE",), 
            "mask": ("MASK",),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            "size_mode": (["Original Size", "Custom", "From Pipe (Dimensions)"],),
            "width": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 8}),
            "height": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 8}),
            "resize_scale": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.05}),
            "inpaint_area": (["Whole picture", "Only masked"],),
            "resize_mode": (["Just resize", "Crop and resize", "Resize and fill"],),
            "mask_mode": (["Inpaint masked", "Inpaint not masked"],),
            "mask_blur": ("INT", {"default": 4, "min": 0, "max": 64, "step": 1}),
            "masked_content": (["original", "fill", "latent noise", "latent nothing"],),
            "context_padding": ("INT", {"default": 32, "min": 0, "max": 256, "step": 4}),
            "context_expand": ("FLOAT", {"default": 1.0, "min": 1.0, "max": 10.0, "step": 0.05}),
            "context_preserve_aspect": ("BOOLEAN", {"default": True}),
            "denoise": ("FLOAT", {"default": 0.75, "min": 0.0, "max": 1.0, "step": 0.01}),
            "steps": ("INT", {"default": 20, "min": 1, "max": 150, "tooltip": "Overrides pipe — sampler steps for inpainting"}),
            "cfg": ("FLOAT", {"default": 7.0, "min": 1.0, "max": 30.0, "step": 0.5, "tooltip": "Overrides pipe — CFG scale"}),
            "sampler_name": (comfy.samplers.KSampler.SAMPLERS, {"default": "euler", "tooltip": "Overrides pipe — sampler for inpainting pass"}),
            "scheduler": (comfy.samplers.KSampler.SCHEDULERS, {"default": "normal", "tooltip": "Overrides pipe — scheduler for inpainting pass"}),
            "use_inpaint_model": ("BOOLEAN", {"default": False, "tooltip": "Use InpaintModelConditioning — allows denoise=1.0 by encoding unmasked context into the model"}),
            "color_fix": ("BOOLEAN", {"default": False, "tooltip": "Match color of inpainted region to original via mean correction"}),
            "color_fix_strength": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05, "tooltip": "Blend strength for color correction (0=off, 1=full)"}),
            "positive_prompt": ("STRING", {"multiline": True, "default": ""}),
            "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
            "prompt_mode": (["Replace", "Append", "If not empty"],),
        }}

    RETURN_TYPES = ("FSD_PIPE", "IMAGE")
    RETURN_NAMES = ("FSD_PIPE", "IMAGE")
    FUNCTION = "apply"
    CATEGORY = "FSD Pipe/Image"
    DESCRIPTION = "Standalone Inpaint: pipe + image + mask → inpainted image. All settings in one node."

    def apply(self, pipe, image, mask, seed, size_mode, width, height, resize_scale, inpaint_area, resize_mode, mask_mode, mask_blur, masked_content, context_padding, context_expand, context_preserve_aspect, denoise, steps, cfg, sampler_name, scheduler, use_inpaint_model, color_fix, color_fix_strength, positive_prompt, negative_prompt, prompt_mode):
        p = pipe.copy()
        current_image = image[0:1].clone()
        p["seed"] = seed
        # Overwrite pipe sampler settings
        p["steps"] = steps
        p["cfg"] = cfg
        p["sampler_name"] = sampler_name
        p["scheduler"] = scheduler

        # --- resolve prompts ---
        resolved_pos, resolved_neg = fsd_resolve_prompts(p, positive_prompt, negative_prompt, prompt_mode)

        for i in range(mask.shape[0]):
            B, H, W, C = current_image.shape
            
            if size_mode == "Original Size": tw, th = int(W), int(H)
            elif size_mode == "Custom": tw, th = width, height
            else: tw, th = p.get("target_width", int(W)), p.get("target_height", int(H))
            
            tw = max(64, int(tw * resize_scale) // 8 * 8)
            th = max(64, int(th * resize_scale) // 8 * 8)
            p["target_width"], p["target_height"] = tw, th
            
            curr_mask = mask[i:i+1].clone()
            if mask_blur > 0:
                k = mask_blur * 2 + 1
                curr_mask = TF.gaussian_blur(curr_mask.unsqueeze(1), kernel_size=[k, k]).squeeze(1)
            if mask_mode == "Inpaint not masked":
                curr_mask = 1.0 - curr_mask

            if curr_mask.shape[-2] != H or curr_mask.shape[-1] != W:
                curr_mask = F.interpolate(curr_mask.unsqueeze(1), size=(H, W), mode="bilinear").squeeze(1)

            m_exp = curr_mask.unsqueeze(-1).expand_as(current_image)
            img_cont = current_image.clone()
            if masked_content == "fill":
                blurred = TF.gaussian_blur(img_cont.movedim(-1,1), kernel_size=[51,51]).movedim(1,-1)
                img_cont = img_cont * (1 - m_exp) + blurred * m_exp
            elif masked_content == "latent noise":
                img_cont = img_cont * (1 - m_exp) + torch.rand_like(img_cont) * m_exp
            elif masked_content == "latent nothing":
                img_cont = img_cont * (1 - m_exp)
    
            crop_data = None
            if inpaint_area == "Only masked":
                non_zero = torch.nonzero(curr_mask[0])
                if len(non_zero) > 0:
                    y1_r, x1_r = non_zero.min(dim=0).values
                    y2_r, x2_r = non_zero.max(dim=0).values
                    
                    cx, cy = (x1_r + x2_r) / 2.0, (y1_r + y2_r) / 2.0
                    cw, ch = (x2_r - x1_r) + context_padding * 2, (y2_r - y1_r) + context_padding * 2
                    cw, ch = cw * context_expand, ch * context_expand
                    
                    if context_preserve_aspect:
                        target_ar = tw / th
                        if (cw / max(1.0, ch)) > target_ar: ch = cw / target_ar
                        else: cw = ch * target_ar
                            
                    scale = min(W / cw, H / ch, 1.0)
                    cw, ch = int(cw * scale), int(ch * scale)
                    
                    x1 = max(0, min(int(cx - cw // 2), W - cw))
                    y1 = max(0, min(int(cy - ch // 2), H - ch))
                    x2, y2 = x1 + cw, y1 + ch
                    
                    crop_data = (y1, y2, x1, x2)
                    final_img = fsd_resize(img_cont[:, y1:y2, x1:x2, :], tw, th, "Just resize")
                    final_mask = F.interpolate(curr_mask[:, y1:y2, x1:x2].unsqueeze(1), size=(th, tw), mode="bilinear").squeeze(1)
                else:
                    final_img, final_mask = fsd_resize(img_cont, tw, th, resize_mode), F.interpolate(curr_mask.unsqueeze(1), size=(th, tw), mode="bilinear").squeeze(1)
            else:
                final_img, final_mask = fsd_resize(img_cont, tw, th, resize_mode), F.interpolate(curr_mask.unsqueeze(1), size=(th, tw), mode="bilinear").squeeze(1)

            if use_inpaint_model:
                pos_cond, neg_cond, latent = nodes.InpaintModelConditioning().encode(
                    positive=resolved_pos,
                    negative=resolved_neg,
                    pixels=final_img[:,:,:,:3],
                    vae=p["vae"],
                    mask=final_mask,
                    noise_mask=True
                )
            else:
                pos_cond = resolved_pos
                neg_cond = resolved_neg
                latent = nodes.SetLatentNoiseMask().set_mask({"samples": nodes.NODE_CLASS_MAPPINGS["VAEEncode"]().encode(p["vae"], final_img[:,:,:,:3])[0]["samples"]}, final_mask)[0]
            res = nodes.common_ksampler(p["model"], seed + i, p["steps"], p["cfg"], p["sampler_name"], p["scheduler"], pos_cond, neg_cond, latent, denoise)
            gen_img = nodes.NODE_CLASS_MAPPINGS["VAEDecode"]().decode(p["vae"], res[0])[0]

            # --- color fix: mean matching ---
            if color_fix and color_fix_strength > 0:
                m_3ch = final_mask.unsqueeze(-1).expand_as(gen_img)
                orig_mean = (final_img * m_3ch).sum(dim=(1,2), keepdim=True) / (m_3ch.sum(dim=(1,2), keepdim=True) + 1e-8)
                gen_mean = (gen_img * m_3ch).sum(dim=(1,2), keepdim=True) / (m_3ch.sum(dim=(1,2), keepdim=True) + 1e-8)
                scale = orig_mean / (gen_mean + 1e-8)
                gen_img = gen_img * (scale * color_fix_strength + (1 - color_fix_strength))
                gen_img = gen_img.clamp(0, 1)

            if crop_data:
                y1, y2, x1, x2 = crop_data
                gen_resized = F.interpolate(gen_img.movedim(-1,1), size=(y2-y1, x2-x1), mode='bicubic').movedim(1,-1)
                m_crop = curr_mask[:, y1:y2, x1:x2].unsqueeze(-1)
                current_image[:, y1:y2, x1:x2, :] = current_image[:, y1:y2, x1:x2, :] * (1 - m_crop) + gen_resized * m_crop
            else:
                current_image = gen_img
        
        p["latent"] = {"samples": nodes.NODE_CLASS_MAPPINGS["VAEEncode"]().encode(p["vae"], current_image[:,:,:,:3])[0]["samples"]}
        return (p, current_image)

class FSD_SAM3Detailer:
    """Autonomous SAM3 Detailer: detects objects via SAM3 (text prompt), inpaints each detected region.
       Bypass toggle disables the node — pipe+image pass through unchanged."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "pipe": ("FSD_PIPE",),
            "image": ("IMAGE",),
            "sam3_model": ("EASY_SAM3_MODEL",),
            "prompt": ("STRING", {"multiline": True, "default": "face"}),
            "threshold": ("FLOAT", {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.05}),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            "denoise": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            "guide_size": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 8}),
            "mask_blur": ("INT", {"default": 4, "min": 0, "max": 64, "step": 1}),
            "context_padding": ("INT", {"default": 32, "min": 0, "max": 256, "step": 4}),
            "context_expand": ("FLOAT", {"default": 1.0, "min": 1.0, "max": 10.0, "step": 0.05}),
            "detection_limit": ("INT", {"default": 5, "min": 1, "max": 100}),
            "masked_content": (["original", "fill", "latent noise", "latent nothing"],),
            "sampler_name": (comfy.samplers.KSampler.SAMPLERS, {"default": "euler"}),
            "scheduler": (comfy.samplers.KSampler.SCHEDULERS, {"default": "normal"}),
            "bypass": ("BOOLEAN", {"default": False}),
            "use_inpaint_model": ("BOOLEAN", {"default": False, "tooltip": "Use InpaintModelConditioning — allows denoise=1.0 by encoding unmasked context into the model"}),
            "color_fix": ("BOOLEAN", {"default": False, "tooltip": "Match color of inpainted region to original via mean correction"}),
            "color_fix_strength": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05, "tooltip": "Blend strength for color correction (0=off, 1=full)"}),
            "positive_prompt": ("STRING", {"multiline": True, "default": ""}),
            "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
            "prompt_mode": (["Replace", "Append", "If not empty"],),
        }}

    RETURN_TYPES = ("FSD_PIPE", "IMAGE", "MASK")
    RETURN_NAMES = ("FSD_PIPE", "IMAGE", "MASK")
    FUNCTION = "apply"
    CATEGORY = "FSD Pipe/Image"
    DESCRIPTION = "Autonomous SAM3 Detailer: detect objects via text prompt (e.g. 'face', 'person'), inpaint each detected region. Toggle bypass to disable."

    def apply(self, pipe, image, sam3_model, prompt, threshold, seed, denoise,
              guide_size, mask_blur, context_padding, context_expand, detection_limit,
              masked_content, sampler_name, scheduler, bypass, use_inpaint_model,
              color_fix, color_fix_strength,
              positive_prompt, negative_prompt, prompt_mode):
        import numpy as np
        from PIL import Image
        import comfy.model_management as mm

        p = pipe.copy()
        current_image = image[0:1].clone()
        B, H, W, C = current_image.shape

        # --- combined mask (output) ---
        combined_mask = torch.zeros((H, W), dtype=torch.float32, device=current_image.device)

        if bypass:
            return (p, current_image, combined_mask)

        if not prompt.strip():
            return (p, current_image, combined_mask)

        # --- resolve prompts — force re-encode to avoid ControlNet/IPAdapter conditioning leak
        resolved_pos, resolved_neg = fsd_resolve_prompts(p, positive_prompt, negative_prompt, prompt_mode, force_reencode=True)
        # Mark pipe as SAM3/second-pass active
        p["_fsd_sam3_active"] = True

        # --- run SAM3 segmentation ---
        processor = sam3_model.get("processor", None)
        model_sam = sam3_model.get("model", None)
        device_sam = sam3_model.get("device", torch.device("cpu"))
        dtype_sam = sam3_model.get("dtype", torch.float32)

        if model_sam is None or processor is None:
            raise ValueError("FSD_SAM3Detailer: Invalid SAM3 model. Load a SAM3 model in 'image' mode.")

        processor.set_confidence_threshold(threshold)

        # Convert tensor to PIL
        img_np = (current_image[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
        pil_img = Image.fromarray(img_np)

        # Run SAM3
        model_sam.to(device_sam)
        autocast_condition = not mm.is_device_mps(device_sam)
        with torch.autocast(mm.get_autocast_device(device_sam), dtype=dtype_sam) if autocast_condition else nullcontext():
            state = processor.set_image(pil_img)
            state = processor.set_text_prompt(prompt.strip(), state)
            obj_masks = state.get('masks', None)

        if obj_masks is None or len(obj_masks) == 0:
            return (p, current_image, combined_mask)

        # Offload SAM3 model to free GPU memory for diffusion
        offload_device = mm.unet_offload_device()
        model_sam.to(offload_device)
        mm.soft_empty_cache()

        # Sort by score (area proxy — larger masks first)
        mask_areas = obj_masks.sum(dim=(1, 2, 3))
        top_indices = torch.argsort(mask_areas, descending=True)
        obj_masks = obj_masks[top_indices]

        if detection_limit > 0:
            obj_masks = obj_masks[:detection_limit]

        num_objects = len(obj_masks)

        # --- inpaint each detected region ---
        pbar = comfy.utils.ProgressBar(num_objects)
        for obj_idx in range(num_objects):
            obj_mask = obj_masks[obj_idx]  # (1, H, W) or (H, W)
            if obj_mask.dim() == 3:
                obj_mask = obj_mask[0]  # (H, W)
            obj_mask = obj_mask.float().to(current_image.device)  # SAM3 returns bool masks — convert & move

            # Resize mask to match image if needed
            if obj_mask.shape[-2] != H or obj_mask.shape[-1] != W:
                obj_mask = F.interpolate(obj_mask.unsqueeze(0).unsqueeze(0), size=(H, W), mode="bilinear").squeeze(0).squeeze(0)

            # Skip empty masks
            if obj_mask.sum() < 10:
                continue

            # Add to combined mask
            combined_mask = torch.clamp(combined_mask + obj_mask.to(combined_mask.device), 0, 1)

            # --- find crop region ---
            non_zero = torch.nonzero(obj_mask)
            if len(non_zero) == 0:
                continue

            y1_r, x1_r = non_zero.min(dim=0).values
            y2_r, x2_r = non_zero.max(dim=0).values

            cx, cy = (x1_r + x2_r) / 2.0, (y1_r + y2_r) / 2.0
            cw = (x2_r - x1_r).float() + context_padding * 2
            ch = (y2_r - y1_r).float() + context_padding * 2
            cw, ch = cw * context_expand, ch * context_expand

            # Preserve aspect ratio of guide_size
            target_ar = guide_size / max(1, guide_size)
            if (cw / max(1.0, ch)) > target_ar:
                ch = cw / target_ar
            else:
                cw = ch * target_ar

            scale = min(W / cw, H / ch, 1.0)
            cw, ch = int(cw * scale), int(ch * scale)

            x1 = max(0, min(int(cx - cw // 2), W - cw))
            y1 = max(0, min(int(cy - ch // 2), H - ch))
            x2, y2 = x1 + cw, y1 + ch

            # --- crop & resize ---
            crop_img = current_image[:, y1:y2, x1:x2, :]
            crop_mask = obj_mask[y1:y2, x1:x2].unsqueeze(0).unsqueeze(0)  # (1, 1, cropH, cropW)

            crop_img_rs = fsd_resize(crop_img, guide_size, guide_size, "Just resize")
            crop_mask_rs = F.interpolate(crop_mask, size=(guide_size, guide_size), mode="bilinear")

            # Apply mask blur
            curr_m = crop_mask_rs.squeeze(0)
            if mask_blur > 0:
                k = mask_blur * 2 + 1
                curr_m = TF.gaussian_blur(curr_m, kernel_size=[k, k])
            curr_m = curr_m.squeeze(0).clamp(0, 1)  # (H, W)

            # --- masked content handling ---
            m_exp = curr_m.unsqueeze(-1).expand_as(crop_img_rs)
            img_inpaint = crop_img_rs.clone()
            if masked_content == "fill":
                blurred = TF.gaussian_blur(img_inpaint.movedim(-1, 1), kernel_size=[51, 51]).movedim(1, -1)
                img_inpaint = img_inpaint * (1 - m_exp) + blurred * m_exp
            elif masked_content == "latent noise":
                img_inpaint = img_inpaint * (1 - m_exp) + torch.rand_like(img_inpaint) * m_exp
            elif masked_content == "latent nothing":
                img_inpaint = img_inpaint * (1 - m_exp)

            # --- encode + apply mask + sample ---
            if use_inpaint_model:
                pos_cond, neg_cond, latent = nodes.InpaintModelConditioning().encode(
                    positive=resolved_pos,
                    negative=resolved_neg,
                    pixels=img_inpaint[:, :, :, :3],
                    vae=p["vae"],
                    mask=curr_m.unsqueeze(0),
                    noise_mask=True
                )
            else:
                pos_cond = resolved_pos
                neg_cond = resolved_neg
                latent = nodes.SetLatentNoiseMask().set_mask(
                    {"samples": nodes.NODE_CLASS_MAPPINGS["VAEEncode"]().encode(p["vae"], img_inpaint[:, :, :, :3])[0]["samples"]},
                    curr_m.unsqueeze(0)
                )[0]

            # Use unpatched model if IPAdapter stored one (bypass_hires/bypass_sam3)
            detail_model = p.get("_fsd_model_pre_ipadapter", p["model"])
            res = nodes.common_ksampler(
                detail_model, seed + obj_idx, p["steps"], p["cfg"],
                sampler_name, scheduler,
                pos_cond, neg_cond,
                latent, denoise
            )

            gen_img = nodes.NODE_CLASS_MAPPINGS["VAEDecode"]().decode(p["vae"], res[0])[0]

            # --- color fix: mean matching ---
            if color_fix and color_fix_strength > 0:
                m_3ch = curr_m.unsqueeze(-1).expand_as(gen_img)
                orig_mean = (crop_img_rs * m_3ch).sum(dim=(1,2), keepdim=True) / (m_3ch.sum(dim=(1,2), keepdim=True) + 1e-8)
                gen_mean = (gen_img * m_3ch).sum(dim=(1,2), keepdim=True) / (m_3ch.sum(dim=(1,2), keepdim=True) + 1e-8)
                scale = orig_mean / (gen_mean + 1e-8)
                gen_img = gen_img * (scale * color_fix_strength + (1 - color_fix_strength))
                gen_img = gen_img.clamp(0, 1)

            # --- composite back ---
            gen_resized = F.interpolate(gen_img.movedim(-1, 1), size=(y2 - y1, x2 - x1), mode='bicubic').movedim(1, -1)
            m_orig = obj_mask[y1:y2, x1:x2].unsqueeze(-1).to(gen_resized.device)
            current_image[:, y1:y2, x1:x2, :] = (
                current_image[:, y1:y2, x1:x2, :] * (1 - m_orig) + gen_resized * m_orig
            )

            pbar.update_absolute(obj_idx + 1, num_objects)

        p["latent"] = {"samples": nodes.NODE_CLASS_MAPPINGS["VAEEncode"]().encode(p["vae"], current_image[:, :, :, :3])[0]["samples"]}
        p["seed"] = seed
        return (p, current_image, combined_mask)

class FSD_HiresFix_Latent:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "pipe": ("FSD_PIPE",),
            "upscale_method": (["bilinear", "nearest-exact", "bicubic", "area", "bislerp"],),
            "scale_by": ("FLOAT", {"default": 2.0, "min": 1.1, "max": 4.0, "step": 0.05}),
            "hires_steps": ("INT", {"default": 0, "min": 0, "max": 150}),
            "sampler_name": (["Use Base"] + comfy.samplers.KSampler.SAMPLERS,),
            "scheduler": (["Use Base"] + comfy.samplers.KSampler.SCHEDULERS,),
            "denoise": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            "bypass": ("BOOLEAN", {"default": False}),
            "positive_prompt": ("STRING", {"multiline": True, "default": ""}),
            "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
            "prompt_mode": (["Replace", "Append", "If not empty"],),
        }}
    RETURN_TYPES = ("FSD_PIPE", "IMAGE"); FUNCTION = "apply"; CATEGORY = "FSD Pipe/Image"
    DESCRIPTION = "Upscale latent directly via latent-space upscale method"
    def apply(self, pipe, upscale_method, scale_by, hires_steps, sampler_name, scheduler, denoise, seed, bypass, positive_prompt, negative_prompt, prompt_mode):
        p = pipe.copy(); p["seed"] = seed
        if not p.get("latent") or "samples" not in p["latent"]:
            return (p, torch.zeros((1, 64, 64, 3)))
        if bypass:
            return (p, nodes.NODE_CLASS_MAPPINGS["VAEDecode"]().decode(p["vae"], p["latent"])[0])
        # Resolve prompts — force re-encode to avoid ControlNet/IPAdapter conditioning leak
        resolved_pos, resolved_neg = fsd_resolve_prompts(p, positive_prompt, negative_prompt, prompt_mode, force_reencode=True)
        # Mark pipe as hires/second-pass active
        p["_fsd_hires_active"] = True
        latent = p["latent"]["samples"]
        B, C, H, W = latent.shape
        upscaled = comfy.utils.common_upscale(latent, int(W * scale_by), int(H * scale_by), upscale_method, "disabled")
        steps = hires_steps if hires_steps > 0 else p["steps"]
        s_name = p["sampler_name"] if sampler_name == "Use Base" else sampler_name
        sched = p["scheduler"] if scheduler == "Use Base" else scheduler
        # Use unpatched model if IPAdapter stored one (bypass_hires/bypass_sam3)
        hires_model = p.get("_fsd_model_pre_ipadapter", p["model"])
        sample_res = nodes.common_ksampler(model=hires_model, seed=seed, steps=steps, cfg=p["cfg"], sampler_name=s_name, scheduler=sched, positive=resolved_pos, negative=resolved_neg, latent={"samples": upscaled}, denoise=denoise)
        p["latent"] = sample_res[0]
        return (p, nodes.NODE_CLASS_MAPPINGS["VAEDecode"]().decode(p["vae"], sample_res[0])[0])

class FSD_HiresFix_Pixel:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "pipe": ("FSD_PIPE",),
            "upscale_model": (folder_paths.get_filename_list("upscale_models"),),
            "scale_by": ("FLOAT", {"default": 2.0, "min": 1.1, "max": 4.0, "step": 0.05}),
            "hires_steps": ("INT", {"default": 0, "min": 0, "max": 150}),
            "sampler_name": (["Use Base"] + comfy.samplers.KSampler.SAMPLERS,),
            "scheduler": (["Use Base"] + comfy.samplers.KSampler.SCHEDULERS,),
            "denoise": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            "bypass": ("BOOLEAN", {"default": False}),
            "positive_prompt": ("STRING", {"multiline": True, "default": ""}),
            "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
            "prompt_mode": (["Replace", "Append", "If not empty"],),
        }}
    RETURN_TYPES = ("FSD_PIPE", "IMAGE"); FUNCTION = "apply"; CATEGORY = "FSD Pipe/Image"
    DESCRIPTION = "Upscale via pixel-space model (e.g. Ultimate SD Upscale)"
    def apply(self, pipe, upscale_model, scale_by, hires_steps, sampler_name, scheduler, denoise, seed, bypass, positive_prompt, negative_prompt, prompt_mode):
        p = pipe.copy(); p["seed"] = seed
        if not p.get("latent") or not p.get("vae"):
            return (p, torch.zeros((1, 64, 64, 3)))
        if bypass:
            return (p, nodes.NODE_CLASS_MAPPINGS["VAEDecode"]().decode(p["vae"], p["latent"])[0])
        # Resolve prompts — force re-encode to avoid ControlNet/IPAdapter conditioning leak
        resolved_pos, resolved_neg = fsd_resolve_prompts(p, positive_prompt, negative_prompt, prompt_mode, force_reencode=True)
        # Mark pipe as hires/second-pass active
        p["_fsd_hires_active"] = True
        base_img = nodes.NODE_CLASS_MAPPINGS["VAEDecode"]().decode(p["vae"], p["latent"])[0]
        model = nodes.NODE_CLASS_MAPPINGS["UpscaleModelLoader"]().load_model(upscale_model)[0]
        up_img = nodes.NODE_CLASS_MAPPINGS["ImageUpscaleWithModel"]().upscale(model, base_img)[0]
        B, H, W, C = base_img.shape
        target_w = int(W * scale_by); target_h = int(H * scale_by)
        up_img = fsd_resize(up_img, target_w, target_h, "Just resize")
        new_latent = {"samples": nodes.NODE_CLASS_MAPPINGS["VAEEncode"]().encode(p["vae"], up_img)[0]["samples"]}
        steps = hires_steps if hires_steps > 0 else p["steps"]
        s_name = p["sampler_name"] if sampler_name == "Use Base" else sampler_name
        sched = p["scheduler"] if scheduler == "Use Base" else scheduler
        # Use unpatched model if IPAdapter stored one (bypass_hires/bypass_sam3)
        hires_model = p.get("_fsd_model_pre_ipadapter", p["model"])
        sample_res = nodes.common_ksampler(model=hires_model, seed=seed, steps=steps, cfg=p["cfg"], sampler_name=s_name, scheduler=sched, positive=resolved_pos, negative=resolved_neg, latent=new_latent, denoise=denoise)
        p["latent"] = sample_res[0]
        return (p, nodes.NODE_CLASS_MAPPINGS["VAEDecode"]().decode(p["vae"], sample_res[0])[0])

class FSD_TiledUpscale:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "upscale_model": (folder_paths.get_filename_list("upscale_models"), ), "scale_by": ("FLOAT", {"default": 2.0, "min": 1.1, "max": 4.0, "step": 0.05}), "tile_width": ("INT", {"default": 512, "min": 256, "max": 1024, "step": 64}), "tile_height": ("INT", {"default": 512, "min": 256, "max": 1024, "step": 64}), "overlap": ("INT", {"default": 64, "min": 0, "max": 256, "step": 8}), "denoise": ("FLOAT", {"default": 0.35, "min": 0.0, "max": 1.0, "step": 0.01}), "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}), "positive_prompt": ("STRING", {"multiline": True, "default": ""}), "negative_prompt": ("STRING", {"multiline": True, "default": ""}), "prompt_mode": (["Replace", "Append", "If not empty"],)}}
    RETURN_TYPES = ("FSD_PIPE", "IMAGE"); FUNCTION = "apply"; CATEGORY = "FSD Pipe/Image"
    DESCRIPTION = "Upscale image using SD Ultimate Upscale with tile-based sampling. Prompt override supported."
    def apply(self, pipe, upscale_model, scale_by, tile_width, tile_height, overlap, denoise, seed, positive_prompt, negative_prompt, prompt_mode):
        p = pipe.copy(); p["seed"] = seed
        if not p.get("latent") or not p.get("vae"):
            return (p, torch.zeros((1, 64, 64, 3)))

        # Resolve prompts
        p["positive"], p["negative"] = fsd_resolve_prompts(p, positive_prompt, negative_prompt, prompt_mode)

        base_img = nodes.NODE_CLASS_MAPPINGS["VAEDecode"]().decode(p["vae"], p["latent"])[0]
        model = nodes.NODE_CLASS_MAPPINGS["UpscaleModelLoader"]().load_model(upscale_model)[0]
        up_img = nodes.NODE_CLASS_MAPPINGS["ImageUpscaleWithModel"]().upscale(model, base_img)[0]
        B, H, W, C = base_img.shape
        target_w, target_h = int(W * scale_by), int(H * scale_by)
        up_img = fsd_resize(up_img, target_w, target_h, "Just resize")
        final_image = torch.zeros_like(up_img)
        weight_map = torch.zeros((1, target_h, target_w, 1), device=up_img.device, dtype=torch.float32)
        stride_x = tile_width - overlap; stride_y = tile_height - overlap
        xs = list(range(0, target_w - tile_width + 1, stride_x)); ys = list(range(0, target_h - tile_height + 1, stride_y))
        if len(xs) == 0 or xs[-1] + tile_width < target_w: xs.append(max(0, target_w - tile_width))
        if len(ys) == 0 or ys[-1] + tile_height < target_h: ys.append(max(0, target_h - tile_height))
        window = torch.ones((tile_height, tile_width), device=up_img.device, dtype=torch.float32)
        for i in range(overlap):
            val = (i + 0.5) / max(1, overlap)
            window[i, :] *= val; window[-i-1, :] *= val; window[:, i] *= val; window[:, -i-1] *= val
        window = window.unsqueeze(0).unsqueeze(-1)
        
        # Iteration with seeded rng for stability
        for idx_y, y in enumerate(ys):
            for idx_x, x in enumerate(xs):
                tile = up_img[:, y:y+tile_height, x:x+tile_width, :]
                tile_latent = {"samples": nodes.NODE_CLASS_MAPPINGS["VAEEncode"]().encode(p["vae"], tile)[0]["samples"]}
                # Combine tile coordinates into the seed to keep tiles unique but deterministic
                tile_seed = seed + idx_y * 1000 + idx_x
                res = nodes.common_ksampler(model=p["model"], seed=tile_seed, steps=p["steps"], cfg=p["cfg"], sampler_name=p["sampler_name"], scheduler=p["scheduler"], positive=p.get("positive", []), negative=p.get("negative",[]), latent=tile_latent, denoise=denoise)
                tile_sampled = nodes.NODE_CLASS_MAPPINGS["VAEDecode"]().decode(p["vae"], res[0])[0]
                final_image[:, y:y+tile_height, x:x+tile_width, :] += tile_sampled * window
                weight_map[:, y:y+tile_height, x:x+tile_width, :] += window

        final_image /= weight_map.clamp(min=1e-5)
        p["latent"] = {"samples": nodes.NODE_CLASS_MAPPINGS["VAEEncode"]().encode(p["vae"], final_image)[0]["samples"]}
        return (p, final_image)

class FSD_VAEEncode:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "image": ("IMAGE",)}}
    RETURN_TYPES = ("FSD_PIPE", "LATENT")
    RETURN_NAMES = ("FSD_PIPE", "LATENT")
    FUNCTION = "apply"; CATEGORY = "FSD Pipe/Image"
    DESCRIPTION = "Encode image to latent using pipe VAE (standalone)"

    def apply(self, pipe, image):
        p = pipe.copy()
        if p.get("vae") is None:
            return (p, {"samples": torch.zeros((1, 4, 8, 8))})
        latent = nodes.NODE_CLASS_MAPPINGS["VAEEncode"]().encode(p["vae"], image)[0]
        p["latent"] = latent
        return (p, latent)

class FSD_VAEDecode:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",)}}
    RETURN_TYPES = ("FSD_PIPE", "IMAGE")
    RETURN_NAMES = ("FSD_PIPE", "IMAGE")
    FUNCTION = "apply"; CATEGORY = "FSD Pipe/Image"
    DESCRIPTION = "Decode latent to image using pipe VAE (standalone)"

    def apply(self, pipe):
        p = pipe.copy()
        if not p.get("latent") or p.get("vae") is None:
            return (p, torch.zeros((1, 64, 64, 3)))
        img = nodes.NODE_CLASS_MAPPINGS["VAEDecode"]().decode(p["vae"], p["latent"])[0]
        p["image"] = img
        return (p, img)

class FSD_LatentComposite:
    @classmethod
    def INPUT_TYPES(s): return {"required": {
        "pipe_src": ("FSD_PIPE",), "pipe_dst": ("FSD_PIPE",),
        "mask": ("MASK",),
        "x": ("INT", {"default": 0, "min": -8192, "max": 8192, "step": 8}),
        "y": ("INT", {"default": 0, "min": -8192, "max": 8192, "step": 8}),
    }}
    RETURN_TYPES = ("FSD_PIPE",)
    FUNCTION = "apply"; CATEGORY = "FSD Pipe/Image"
    DESCRIPTION = "Composite src pipe latent onto dst pipe latent using mask at (x, y)"

    def apply(self, pipe_src, pipe_dst, mask, x, y):
        p_dst = pipe_dst.copy()
        lat_src = pipe_src.get("latent", {}).get("samples") if pipe_src.get("latent") else None
        lat_dst = p_dst.get("latent", {}).get("samples") if p_dst.get("latent") else None
        if lat_src is None or lat_dst is None:
            return (p_dst,)

        x_lat = x // 8; y_lat = y // 8
        src_h, src_w = lat_src.shape[2], lat_src.shape[3]
        dst_h, dst_w = lat_dst.shape[2], lat_dst.shape[3]

        mask_rs = F.interpolate(mask.unsqueeze(1), size=(src_h, src_w), mode="bilinear")
        y1_d, x1_d = max(0, y_lat), max(0, x_lat)
        y2_d, x2_d = min(dst_h, y_lat + src_h), min(dst_w, x_lat + src_w)
        y1_s, x1_s = max(0, -y_lat), max(0, -x_lat)
        y2_s, x2_s = y1_s + (y2_d - y1_d), x1_s + (x2_d - x1_d)

        if y2_d <= y1_d or x2_d <= x1_d:
            return (p_dst,)

        result = lat_dst.clone()
        m = mask_rs[:, :, y1_s:y2_s, x1_s:x2_s]
        result[:, :, y1_d:y2_d, x1_d:x2_d] = (
            lat_src[:, :, y1_s:y2_s, x1_s:x2_s] * m +
            lat_dst[:, :, y1_d:y2_d, x1_d:x2_d] * (1 - m)
        )
        p_dst["latent"] = {"samples": result}
        return (p_dst,)


# ==========================================
#[FSD/3B. Standalone Autonomous Nodes — full self-contained generation]
# ==========================================
class FSD_Text2Img:
    """Autonomous Text-to-Image: pipe + prompts → image. All settings in one node."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "pipe": ("FSD_PIPE",),
                "positive": ("STRING", {"multiline": True, "default": ""}),
                "negative": ("STRING", {"multiline": True, "default": ""}),
                "syntax_mode": (["ComfyUI", "A1111", "ComfyUI+"], {"default": "ComfyUI"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 150}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 1.0, "max": 30.0, "step": 0.5}),
                "sampler_name": (comfy.samplers.KSampler.SAMPLERS, {"default": "euler"}),
                "scheduler": (comfy.samplers.KSampler.SCHEDULERS, {"default": "normal"}),
                "width": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 8}),
                "height": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 8}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 64}),
            },
            "optional": {
                "guidance": ("FLOAT", {"default": 3.5, "min": 0.0, "max": 100.0, "step": 0.1}),
            }
        }
    RETURN_TYPES = ("FSD_PIPE", "IMAGE")
    RETURN_NAMES = ("FSD_PIPE", "IMAGE")
    FUNCTION = "generate"
    CATEGORY = "FSD Pipe/Standalone"
    DESCRIPTION = "Autonomous Text-to-Image: encode prompts, generate image from scratch. One node = full txt2img workflow."

    def generate(self, pipe, positive, negative, syntax_mode, seed, steps, cfg, sampler_name, scheduler, width, height, batch_size, guidance=None):
        p = pipe.copy()
        model = p.get("model")
        clip = p.get("clip")
        vae = p.get("vae")

        if model is None:
            raise RuntimeError("FSD_Text2Img: model not found in pipe. Connect a pipe with a loaded model.")

        # Overwrite pipe settings
        p["seed"] = seed
        p["steps"] = steps
        p["cfg"] = cfg
        p["sampler_name"] = sampler_name
        p["scheduler"] = scheduler
        p["target_width"] = width
        p["target_height"] = height
        p["syntax_mode"] = syntax_mode
        p["pos_text"] = positive
        p["neg_text"] = negative
        if guidance is not None:
            p["guidance"] = guidance

        # Encode prompts — ComfyUI mode uses native CLIPTextEncode (1:1 match)
        if syntax_mode == "ComfyUI" and clip is not None:
            if positive.strip():
                pos_cond = clip.encode_from_tokens_scheduled(clip.tokenize(positive))
            else:
                pos_cond = clip.encode_from_tokens_scheduled(clip.tokenize(""))
            if negative.strip():
                neg_cond = clip.encode_from_tokens_scheduled(clip.tokenize(negative))
            else:
                neg_cond = clip.encode_from_tokens_scheduled(clip.tokenize(""))
        else:
            pos_cond, neg_cond = fsd_encode_prompts(p, clip, positive, negative, seed, syntax_mode)

        # Re-apply ControlNet if it was stored in the pipe by FSD_ControlNet
        cn_list = p.get("_fsd_controlnet", [])
        for cn_data in cn_list:
            cnet = cn_data["control_net_override"]
            if cnet is None:
                cnet = nodes.ControlNetLoader().load_controlnet(cn_data["control_net_name"])[0]
            pos_cond, neg_cond = nodes.NODE_CLASS_MAPPINGS["ControlNetApplyAdvanced"]().apply_controlnet(
                pos_cond, neg_cond, cnet, cn_data["image"],
                cn_data["strength"], cn_data["start_percent"], cn_data["end_percent"],
                vae=cn_data.get("vae")
            )

        p["positive"] = pos_cond
        p["negative"] = neg_cond

        # Create empty latent
        latent = {"samples": torch.zeros([batch_size, 4, height // 8, width // 8])}

        # Run native KSampler
        sample_res = nodes.common_ksampler(
            model=model, seed=seed, steps=steps, cfg=cfg,
            sampler_name=sampler_name, scheduler=scheduler,
            positive=pos_cond, negative=neg_cond,
            latent=latent, denoise=1.0
        )
        p["latent"] = sample_res[0]

        # Decode
        if vae is not None:
            image = nodes.NODE_CLASS_MAPPINGS["VAEDecode"]().decode(vae, sample_res[0])[0]
            p["image"] = image
            return (p, image)
        return (p, torch.zeros((batch_size, height, width, 3)))


class FSD_Img2Img_Standalone:
    """Autonomous Img2Img: pipe + image → image. Encode, sample, decode — all in one node."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "pipe": ("FSD_PIPE",),
                "image": ("IMAGE",),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "denoise": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 150}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 1.0, "max": 30.0, "step": 0.5}),
                "sampler_name": (comfy.samplers.KSampler.SAMPLERS, {"default": "euler"}),
                "scheduler": (comfy.samplers.KSampler.SCHEDULERS, {"default": "normal"}),
                "size_mode": (["Original Size", "Custom", "From Pipe"],),
                "width": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 8}),
                "height": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 8}),
                "resize_mode": (["Just resize", "Crop and resize", "Resize and fill"],),
                "positive_prompt": ("STRING", {"multiline": True, "default": ""}),
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
                "prompt_mode": (["Replace", "Append", "If not empty"],),
            },
        }
    RETURN_TYPES = ("FSD_PIPE", "IMAGE")
    RETURN_NAMES = ("FSD_PIPE", "IMAGE")
    FUNCTION = "apply"
    CATEGORY = "FSD Pipe/Standalone"
    DESCRIPTION = "Autonomous Img2Img: encode image → sample → decode. One node = full img2img workflow."

    def apply(self, pipe, image, seed, denoise, steps, cfg, sampler_name, scheduler, size_mode, width, height, resize_mode, positive_prompt, negative_prompt, prompt_mode):
        p = pipe.copy()
        model = p.get("model")
        clip = p.get("clip")
        vae = p.get("vae")

        if model is None:
            raise RuntimeError("FSD_Img2Img_Standalone: model not found in pipe. Connect a pipe with a loaded model.")

        # Overwrite pipe settings
        p["seed"] = seed
        p["steps"] = steps
        p["cfg"] = cfg
        p["sampler_name"] = sampler_name
        p["scheduler"] = scheduler

        B, H, W, C = image.shape
        if size_mode == "Original Size":
            tw, th = int(W), int(H)
        elif size_mode == "Custom":
            tw, th = width, height
        else:
            tw, th = p.get("target_width", 512), p.get("target_height", 512)
        p["target_width"] = tw
        p["target_height"] = th

        # Resize & encode
        resized = fsd_resize(image, tw, th, resize_mode)
        latent = {"samples": nodes.NODE_CLASS_MAPPINGS["VAEEncode"]().encode(vae, resized[:, :, :, :3])[0]["samples"]}

        # Resolve prompts
        pos_cond, neg_cond = fsd_resolve_prompts(p, positive_prompt, negative_prompt, prompt_mode)
        p["positive"] = pos_cond
        p["negative"] = neg_cond

        # Run native KSampler
        sample_res = nodes.common_ksampler(
            model=model, seed=seed, steps=steps, cfg=cfg,
            sampler_name=sampler_name, scheduler=scheduler,
            positive=pos_cond, negative=neg_cond,
            latent=latent, denoise=denoise
        )
        p["latent"] = sample_res[0]

        # Decode
        if vae is not None:
            image_out = nodes.NODE_CLASS_MAPPINGS["VAEDecode"]().decode(vae, sample_res[0])[0]
            p["image"] = image_out
            return (p, image_out)
        return (p, torch.zeros((1, th, tw, 3)))


class FSD_Upscale_Standalone:
    """Autonomous Upscale: pipe + image → upscaled image. Upscale model + optional re-sampling."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "pipe": ("FSD_PIPE",),
                "image": ("IMAGE",),
                "upscale_model": (folder_paths.get_filename_list("upscale_models"),),
                "scale_by": ("FLOAT", {"default": 2.0, "min": 1.1, "max": 4.0, "step": 0.05}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "denoise": ("FLOAT", {"default": 0.35, "min": 0.0, "max": 1.0, "step": 0.01}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 150}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 1.0, "max": 30.0, "step": 0.5}),
                "sampler_name": (comfy.samplers.KSampler.SAMPLERS, {"default": "euler"}),
                "scheduler": (comfy.samplers.KSampler.SCHEDULERS, {"default": "normal"}),
                "positive_prompt": ("STRING", {"multiline": True, "default": ""}),
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
                "prompt_mode": (["Replace", "Append", "If not empty"],),
            },
        }
    RETURN_TYPES = ("FSD_PIPE", "IMAGE")
    RETURN_NAMES = ("FSD_PIPE", "IMAGE")
    FUNCTION = "apply"
    CATEGORY = "FSD Pipe/Standalone"
    DESCRIPTION = "Autonomous Upscale: upscale model → optional re-sample pass. One node = full upscale workflow."

    def apply(self, pipe, image, upscale_model, scale_by, seed, denoise, steps, cfg, sampler_name, scheduler, positive_prompt, negative_prompt, prompt_mode):
        p = pipe.copy()
        model = p.get("model")
        clip = p.get("clip")
        vae = p.get("vae")

        if model is None:
            raise RuntimeError("FSD_Upscale_Standalone: model not found in pipe. Connect a pipe with a loaded model.")

        # Overwrite pipe settings
        p["seed"] = seed
        p["steps"] = steps
        p["cfg"] = cfg
        p["sampler_name"] = sampler_name
        p["scheduler"] = scheduler

        B, H, W, C = image.shape
        target_w = int(W * scale_by)
        target_h = int(H * scale_by)

        # Load upscale model
        up_model = nodes.NODE_CLASS_MAPPINGS["UpscaleModelLoader"]().load_model(upscale_model)[0]
        up_img = nodes.NODE_CLASS_MAPPINGS["ImageUpscaleWithModel"]().upscale(up_model, image)[0]
        up_img = fsd_resize(up_img, target_w, target_h, "Just resize")

        # Resolve prompts
        pos_cond, neg_cond = fsd_resolve_prompts(p, positive_prompt, negative_prompt, prompt_mode)
        p["positive"] = pos_cond
        p["negative"] = neg_cond

        if denoise > 0 and vae is not None:
            # Re-sample pass
            new_latent = {"samples": nodes.NODE_CLASS_MAPPINGS["VAEEncode"]().encode(vae, up_img)[0]["samples"]}
            sample_res = nodes.common_ksampler(
                model=model, seed=seed, steps=steps, cfg=cfg,
                sampler_name=sampler_name, scheduler=scheduler,
                positive=pos_cond, negative=neg_cond,
                latent=new_latent, denoise=denoise
            )
            p["latent"] = sample_res[0]
            if vae is not None:
                image_out = nodes.NODE_CLASS_MAPPINGS["VAEDecode"]().decode(vae, sample_res[0])[0]
                p["image"] = image_out
                return (p, image_out)

        # No denoise — just return upscaled image
        if vae is not None:
            p["latent"] = {"samples": nodes.NODE_CLASS_MAPPINGS["VAEEncode"]().encode(vae, up_img)[0]["samples"]}
        p["image"] = up_img
        return (p, up_img)


# ==========================================
#[FSD/5. Routing & Intermediates]
# ==========================================
class FSD_PipeSwitch:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe_A": ("FSD_PIPE",), "pipe_B": ("FSD_PIPE",), "use_B": ("BOOLEAN", {"default": False})}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "switch"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Select one of two pipes based on a boolean condition"
    def switch(self, pipe_A, pipe_B, use_B): return (pipe_B.copy() if use_B else pipe_A.copy(), )

class FSD_PipeDiverter:
    """Lazy router: one pipe input → two outputs. Only the selected output carries the pipe;
       the unselected output is an empty dict → downstream nodes won't execute."""
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "output_index": ("INT", {"default": 0, "min": 0, "max": 1, "step": 1})}}
    RETURN_TYPES = ("FSD_PIPE", "FSD_PIPE")
    RETURN_NAMES = ("pipe_A", "pipe_B")
    FUNCTION = "divert"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Lazy router: sends pipe to output A (index=0) or B (index=1). Only connected output triggers downstream."
    def divert(self, pipe, output_index):
        p = pipe.copy()
        if output_index == 0:
            return (p, {})
        return ({}, p)

class FSD_LazySwitch:
    """Lazy switch: two optional pipe inputs, only the selected one is used.
       Unconnected inputs are not computed — true lazy upstream evaluation."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {"select": (["A", "B"], {"default": "A"})},
            "optional": {"pipe_A": ("FSD_PIPE",), "pipe_B": ("FSD_PIPE",)}
        }
    RETURN_TYPES = ("FSD_PIPE",)
    FUNCTION = "switch"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Lazy switch: select pipe A or B. Only connected input is computed — unconnected branch never executes."

    def switch(self, select, pipe_A=None, pipe_B=None):
        src = pipe_A if select == "A" else pipe_B
        if src is not None:
            return (src.copy(),)
        return ({},)

class FSD_Bypass:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe_original": ("FSD_PIPE",), "pipe_modified": ("FSD_PIPE",), "bypass": ("BOOLEAN", {"default": True})}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "bypass_pipe"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Toggle: pass pipe through or bypass (emit pipe unchanged)"
    def bypass_pipe(self, pipe_original, pipe_modified, bypass): return (pipe_original.copy() if bypass else pipe_modified.copy(), )

class FSD_DynamicPipeSwitch:
    """Lazy switch with up to 20 optional pipe inputs. Only connected inputs are computed.
       'index' selects which pipe to output."""
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {"required": {"index": ("INT", {"default": 0, "min": 0, "max": 19})}, "optional": {}}
        for i in range(20):
            inputs["optional"][f"pipe_{i}"] = ("FSD_PIPE",)
        return inputs
    RETURN_TYPES = ("FSD_PIPE",)
    FUNCTION = "switch"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Dynamic lazy switch: up to 20 optional pipe inputs. Only connected inputs compute. Index selects output."

    def switch(self, index, **kwargs):
        src = kwargs.get(f"pipe_{index}")
        if src is not None:
            return (src.copy(),)
        return ({},)

class FSD_DynamicPipeDiverter:
    """Lazy diverter with up to 20 outputs. Only the selected output carries the pipe;
       unconnected outputs are not computed downstream."""
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "index": ("INT", {"default": 0, "min": 0, "max": 19})}}
    RETURN_TYPES = tuple(["FSD_PIPE"] * 20)
    RETURN_NAMES = tuple([f"out_{i}" for i in range(20)])
    FUNCTION = "divert"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Dynamic lazy diverter: 1 pipe → 20 outputs. Only out_{index} gets the pipe; unconnected outputs don't execute."

    def divert(self, pipe, index):
        p = pipe.copy()
        outs = [{} for _ in range(20)]
        if 0 <= index < 20:
            outs[index] = p
        return tuple(outs)

class FSD_RandomPipeSwitch:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe_A": ("FSD_PIPE",), "pipe_B": ("FSD_PIPE",), "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff})}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "switch"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Randomly select one of two pipes"
    def switch(self, pipe_A, pipe_B, seed): return (pipe_B.copy() if seed % 2 == 1 else pipe_A.copy(), )

class FSD_PipeBatchCombine:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe_A": ("FSD_PIPE",), "pipe_B": ("FSD_PIPE",)}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "combine"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Combine two pipes by repeating their latents to match batch sizes"
    def combine(self, pipe_A, pipe_B):
        p = pipe_A.copy()
        lat_A = pipe_A.get("latent", {}).get("samples", None)
        lat_B = pipe_B.get("latent", {}).get("samples", None)
        if lat_A is not None and lat_B is not None:
            merged = dict(pipe_A.get("latent", {}), samples=torch.cat((lat_A, lat_B), dim=0))
            p["latent"] = merged
        return (p, )

class FSD_OverrideSettings:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "override_steps": ("BOOLEAN", {"default": False}), "steps": ("INT", {"default": 20, "min": 1, "max": 150}), "override_cfg": ("BOOLEAN", {"default": False}), "cfg_scale": ("FLOAT", {"default": 7.0, "min": 1.0, "max": 30.0, "step": 0.5}), "override_sampler": ("BOOLEAN", {"default": False}), "sampler_name": (comfy.samplers.KSampler.SAMPLERS, {"default": "dpmpp_2m"}), "override_scheduler": ("BOOLEAN", {"default": False}), "scheduler": (comfy.samplers.KSampler.SCHEDULERS, {"default": "karras"})}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "override"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Override multiple pipe fields (seed, steps, cfg, scheduler, sampler, denoise)"
    def override(self, pipe, override_steps, steps, override_cfg, cfg_scale, override_sampler, sampler_name, override_scheduler, scheduler):
        p = pipe.copy()
        if override_steps: p["steps"] = steps
        if override_cfg: p["cfg"] = cfg_scale
        if override_sampler: p["sampler_name"] = sampler_name
        if override_scheduler: p["scheduler"] = scheduler
        return (p, )

class FSD_LatentScale:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "scale_factor": ("FLOAT", {"default": 1.5, "min": 0.1, "max": 4.0, "step": 0.05}), "upscale_method": (["bilinear", "nearest-exact", "bicubic", "area", "bislerp"],)}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "scale"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Scale latent dimensions by a multiplier factor"
    def scale(self, pipe, scale_factor, upscale_method):
        p = pipe.copy()
        if "latent" in p and isinstance(p.get("latent"), dict) and "samples" in p["latent"]:
            latent = p["latent"]["samples"]
            B, C, H, W = latent.shape
            upscaled = comfy.utils.common_upscale(latent, int(W * scale_factor), int(H * scale_factor), upscale_method, "disabled")
            p["latent"] = {"samples": upscaled}
            p["target_width"] = int(p.get("target_width", W * 8) * scale_factor)
            p["target_height"] = int(p.get("target_height", H * 8) * scale_factor)
        return (p, )

class FSD_SetDenoise:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01})}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "set_denoise"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Set the denoise value in the pipe"
    def set_denoise(self, pipe, denoise):
        p = pipe.copy(); p["denoise"] = denoise; return (p, )

class FSD_PipeAutoFix:
    """Explicitly fills missing pipe fields with safe defaults — bridge between partial pipes."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"pipe": ("FSD_PIPE",)}, "optional": {"model": ("MODEL",), "clip": ("CLIP",), "vae": ("VAE",), "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff})}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "fix"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Auto-fix common pipe issues (missing VAE from model, etc.)"
    def fix(self, pipe, model=None, clip=None, vae=None, seed=0):
        return (_ensure_pipe(pipe, model=model, clip=clip, vae=vae, seed=seed), )

class FSD_PipeBranch:
    """Creates a named branch of the pipe for parallel workflows. Tag survives merges."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"pipe": ("FSD_PIPE",), "branch_name": ("STRING", {"default": "Branch"})}}
    RETURN_TYPES = ("FSD_PIPE", "FSD_PIPE"); RETURN_NAMES = ("pipe_main", "pipe_branch")
    FUNCTION = "branch"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Split pipe into two parallel branches for independent processing"
    def branch(self, pipe, branch_name):
        main = pipe.copy(); main["_branch"] = "main"
        br = pipe.copy(); br["_branch"] = branch_name
        return (main, br)

class FSD_PipeMergeSelective:
    """Merge two pipes with field-level control over which fields come from which pipe."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "pipe_A": ("FSD_PIPE",), "pipe_B": ("FSD_PIPE",),
                "model_source": (["A", "B"], {"default": "A"}),
                "clip_source": (["A", "B"], {"default": "A"}),
                "vae_source": (["A", "B"], {"default": "A"}),
                "latent_source": (["A", "B", "None"], {"default": "A"}),
                "cond_source": (["A", "B", "Combine"], {"default": "Combine"}),
                "settings_source": (["A", "B"], {"default": "A"}),
                "text_source": (["A", "B"], {"default": "A"}),
            }
        }
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "merge"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Merge two pipes, picking fields from one or the other selectively"
    def merge(self, pipe_A, pipe_B, model_source, clip_source, vae_source, latent_source, cond_source, settings_source, text_source):
        a, b = pipe_A.copy(), pipe_B.copy()
        p = {}
        # Model/clip/vae
        p["model"] = b["model"] if model_source == "B" else a.get("model")
        p["clip"]  = b["clip"]  if clip_source == "B"  else a.get("clip")
        p["vae"]   = b["vae"]   if vae_source == "B"   else a.get("vae")
        # Latent
        if latent_source == "B":    p["latent"] = b.get("latent")
        elif latent_source == "None": p["latent"] = None
        else:                       p["latent"] = a.get("latent")
        # Conditioning
        if cond_source == "B":       p["positive"], p["negative"] = b.get("positive",[]), b.get("negative",[])
        elif cond_source == "Combine": p["positive"] = a.get("positive",[]) + b.get("positive",[]); p["negative"] = a.get("negative",[]) + b.get("negative",[])
        else:                        p["positive"], p["negative"] = a.get("positive",[]), a.get("negative",[])
        # Sampler settings
        src = b if settings_source == "B" else a
        p["steps"] = src.get("steps", 20); p["cfg"] = src.get("cfg", 7.0)
        p["sampler_name"] = src.get("sampler_name", "euler"); p["scheduler"] = src.get("scheduler", "normal")
        p["denoise"] = src.get("denoise", 1.0); p["seed"] = src.get("seed", 0)
        # Dimensions
        p["target_width"] = src.get("target_width", 512); p["target_height"] = src.get("target_height", 512)
        p["batch_size"] = src.get("batch_size", 1)
        # Text
        txt_src = b if text_source == "B" else a
        p["pos_text"] = txt_src.get("pos_text", ""); p["neg_text"] = txt_src.get("neg_text", "")
        p["syntax_mode"] = txt_src.get("syntax_mode", "ComfyUI")
        return (p,)

class FSD_PipePreview:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",)}}
    RETURN_TYPES = ("FSD_PIPE", "IMAGE"); FUNCTION = "preview"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Preview the pipe latent as an image"
    def preview(self, pipe):
        p = pipe.copy(); latent = p.get("latent", {})
        if latent and p.get("vae") is not None: image = nodes.NODE_CLASS_MAPPINGS["VAEDecode"]().decode(p["vae"], latent)[0]
        else: image = torch.zeros((1, 64, 64, 3)) 
        return (p, image)

class FSD_ClearLatent:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",)}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "clear"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Remove latent from pipe (useful for re-injection)"
    def clear(self, pipe):
        p = pipe.copy()
        if "latent" in p and isinstance(p.get("latent"), dict) and "samples" in p["latent"]:
            B, C, H, W = p["latent"]["samples"].shape
            p["latent"] = dict(p["latent"], samples=torch.zeros([B, C, H, W], device=p["latent"]["samples"].device))
            p["denoise"] = 1.0
        return (p, )

class FSD_SetLatentNoiseMask:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "mask": ("MASK",)}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "set_mask"; CATEGORY = "FSD Pipe/Routing"
    DESCRIPTION = "Attach a noise mask to the latent in the pipe"
    def set_mask(self, pipe, mask):
        p = pipe.copy()
        p["latent"] = nodes.SetLatentNoiseMask().set_mask(p.get("latent", {}), mask)[0]
        return (p, )


# ==========================================
#[FSD/6. Bridges & Variables]
# ==========================================
class FSD_PipeToKSampler:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",)}}
    RETURN_TYPES = ("FSD_PIPE", "MODEL", "CONDITIONING", "CONDITIONING", "LATENT")
    RETURN_NAMES = ("FSD_PIPE", "MODEL", "POSITIVE", "NEGATIVE", "LATENT")
    FUNCTION = "extract"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Convert pipe fields to KSampler-compatible inputs"
    def extract(self, pipe): return (pipe, pipe.get("model"), pipe.get("positive"), pipe.get("negative"), pipe.get("latent"))

class FSD_UnpackSettings:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",)}}
    RETURN_TYPES = ("FSD_PIPE", "INT", "FLOAT", "STRING", "STRING", "FLOAT")
    RETURN_NAMES = ("FSD_PIPE", "steps", "cfg", "sampler_name", "scheduler", "denoise")
    FUNCTION = "unpack_settings"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Extract sampler settings (seed, steps, cfg, etc.) from pipe as separate outputs"
    def unpack_settings(self, pipe): return (pipe, pipe.get("steps", 20), pipe.get("cfg", 7.0), pipe.get("sampler_name", "euler"), pipe.get("scheduler", "normal"), pipe.get("denoise", 1.0))

class FSD_UpdatePipeModel:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "model": ("MODEL",)}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "update"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Replace the model in a pipe"
    def update(self, pipe, model): p = pipe.copy(); p["model"] = model; return (p, )

class FSD_UpdatePipeLatent:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "latent": ("LATENT",)}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "update"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Replace the latent in a pipe"
    def update(self, pipe, latent): p = pipe.copy(); p["latent"] = latent; return (p, )

class FSD_UpdatePipeClip:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "clip": ("CLIP",)}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "update"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Replace the CLIP in a pipe"
    def update(self, pipe, clip): p = pipe.copy(); p["clip"] = clip; return (p, )

class FSD_UpdatePipeVae:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "vae": ("VAE",)}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "update"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Replace the VAE in a pipe"
    def update(self, pipe, vae): p = pipe.copy(); p["vae"] = vae; return (p, )

class FSD_UpdatePipePositive:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "positive": ("CONDITIONING",)}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "update"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Replace the positive conditioning in a pipe"
    def update(self, pipe, positive): p = pipe.copy(); p["positive"] = positive; return (p, )

class FSD_UpdatePipeNegative:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "negative": ("CONDITIONING",)}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "update"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Replace the negative conditioning in a pipe"
    def update(self, pipe, negative): p = pipe.copy(); p["negative"] = negative; return (p, )

class FSD_UpdatePipeSegs:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "segs": ("SEGS",)}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "update"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Inject SEGS (segmentation) into a pipe"
    def update(self, pipe, segs): p = pipe.copy(); p["segs"] = segs; return (p, )

class FSD_ExtractPipeSegs:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",)}}
    RETURN_TYPES = ("FSD_PIPE", "SEGS"); RETURN_NAMES = ("FSD_PIPE", "SEGS")
    FUNCTION = "extract"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Extract SEGS (segmentation) from a pipe"
    def extract(self, pipe): return (pipe, pipe.get("segs", None))

class FSD_PipeToBasicPipe_Impact:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",)}}
    RETURN_TYPES = ("FSD_PIPE", "BASIC_PIPE"); RETURN_NAMES = ("FSD_PIPE", "BASIC_PIPE")
    FUNCTION = "convert"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Convert FSD pipe to ImpactPack BasicPipe format"
    def convert(self, pipe): return (pipe, (pipe.get("model"), pipe.get("clip"), pipe.get("vae"), pipe.get("positive"), pipe.get("negative")))

class FSD_PackPipe:
    @classmethod
    def INPUT_TYPES(s): 
        return {
            "required": {"pipe": ("FSD_PIPE",)}, 
            "optional": {
                "model": ("MODEL",), "clip": ("CLIP",), "vae": ("VAE",), 
                "positive": ("CONDITIONING",), "negative": ("CONDITIONING",), 
                "latent": ("LATENT",), "image": ("IMAGE",), "mask": ("MASK",),
                "segs": ("SEGS",), "seed": ("INT",)
            }
        }
    RETURN_TYPES = ("FSD_PIPE",)
    FUNCTION = "pack"
    CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Pack model/clip/vae/positive/negative/latent into a pipe"

    def pack(self, pipe, model=None, clip=None, vae=None, positive=None, negative=None, latent=None, image=None, mask=None, segs=None, seed=None):
        new_pipe = pipe.copy()
        for k, v in zip(["model", "clip", "vae", "positive", "negative", "latent", "image", "mask", "segs", "seed"],[model, clip, vae, positive, negative, latent, image, mask, segs, seed]):
            if v is not None: new_pipe[k] = v
        return (new_pipe, )

class FSD_PipeEdit:
    @classmethod
    def INPUT_TYPES(s): 
        return {
            "required": {"pipe": ("FSD_PIPE",)}, 
            "optional": {
                "model": ("MODEL",), "clip": ("CLIP",), "vae": ("VAE",), 
                "positive": ("CONDITIONING",), "negative": ("CONDITIONING",), 
                "latent": ("LATENT",), "image": ("IMAGE",), "mask": ("MASK",)
            }
        }
    RETURN_TYPES = ("FSD_PIPE",)
    FUNCTION = "edit"
    CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Edit individual pipe fields using string key/value pairs"

    def edit(self, pipe, **kwargs):
        p = pipe.copy()
        for k, v in kwargs.items():
            if v is not None: p[k] = v
        return (p, )

class FSD_PipeMerge:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe_base": ("FSD_PIPE",), "pipe_override": ("FSD_PIPE",)}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "merge"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Merge two pipes: second pipe values override first"
    def merge(self, pipe_base, pipe_override):
        p = pipe_base.copy()
        p.update(pipe_override)
        return (p, )

class FSD_PipeInfo:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",)}}
    RETURN_TYPES = ("FSD_PIPE", "STRING"); RETURN_NAMES = ("FSD_PIPE", "INFO")
    FUNCTION = "info"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Print pipe contents as a text summary"
    def info(self, pipe):
        lines =[]
        for k, v in pipe.items():
            if isinstance(v, torch.Tensor): lines.append(f"{k}: Tensor {list(v.shape)}")
            elif isinstance(v, dict) and "samples" in v: lines.append(f"{k}: Latent {list(v['samples'].shape)}")
            elif isinstance(v, (str, int, float, bool)): lines.append(f"{k}: {v}")
            else: lines.append(f"{k}: {type(v).__name__}")
        return (pipe, "\n".join(lines))

class FSD_UnpackPipe:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",)}}
    RETURN_TYPES = ("FSD_PIPE", "MODEL", "CLIP", "VAE", "CONDITIONING", "CONDITIONING", "LATENT", "IMAGE", "MASK", "INT")
    RETURN_NAMES = ("FSD_PIPE", "MODEL", "CLIP", "VAE", "POSITIVE", "NEGATIVE", "LATENT", "IMAGE", "MASK", "SEED")
    FUNCTION = "unpack"
    CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Unpack all pipe fields as individual outputs"

    def unpack(self, pipe): 
        return (
            pipe, 
            pipe.get("model"), pipe.get("clip"), pipe.get("vae"), 
            pipe.get("positive"), pipe.get("negative"), pipe.get("latent"),
            pipe.get("image"), pipe.get("mask"), pipe.get("seed", 0)
        )

class FSD_PackBasicPipe:
    @classmethod
    def INPUT_TYPES(cls): return {"required": {}, "optional": {"model": ("MODEL",), "clip": ("CLIP",), "vae": ("VAE",), "positive": ("CONDITIONING",), "negative": ("CONDITIONING",)}}
    RETURN_TYPES = ("BASIC_PIPE",); RETURN_NAMES = ("basic_pipe",); FUNCTION = "pack"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Pack model/clip/vae/positive/negative into a basic pipe"
    def pack(self, model=None, clip=None, vae=None, positive=None, negative=None, **kwargs): return ((model, clip, vae, positive, negative),)

class FSD_UnpackBasicPipe:
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"basic_pipe": ("BASIC_PIPE",)}}
    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "CONDITIONING", "CONDITIONING"); RETURN_NAMES = ("model", "clip", "vae", "positive", "negative")
    FUNCTION = "unpack"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Unpack basic pipe into individual outputs"
    def unpack(self, basic_pipe, **kwargs):
        if isinstance(basic_pipe, tuple) and len(basic_pipe) >= 5: return basic_pipe[:5]
        return (None, None, None, None, None)

class FSD_EditBasicPipe:
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"basic_pipe": ("BASIC_PIPE",)}, "optional": {"model": ("MODEL",), "clip": ("CLIP",), "vae": ("VAE",), "positive": ("CONDITIONING",), "negative": ("CONDITIONING",)}}
    RETURN_TYPES = ("BASIC_PIPE",); RETURN_NAMES = ("basic_pipe",); FUNCTION = "edit"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Edit basic pipe fields using string key/value pairs"
    def edit(self, basic_pipe, model=None, clip=None, vae=None, positive=None, negative=None, **kwargs):
        m, c, v, p, n = None, None, None, None, None
        if isinstance(basic_pipe, tuple) and len(basic_pipe) >= 5: m, c, v, p, n = basic_pipe[:5]
        return (((model or m), (clip or c), (vae or v), (positive or p), (negative or n)),)

class FSD_PipeSetCustom:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",)}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "set_custom"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Set a custom field value in the pipe dictionary"
    def set_custom(self, pipe, **kwargs):
        p = pipe.copy()
        for key, value in kwargs.items():
            if value is not None: p[key] = value
        return (p, )

class FSD_PipeGetCustom:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",)}, "optional": {"key_1": ("STRING", {"default": "my_var_1"}), "key_2": ("STRING", {"default": ""}), "key_3": ("STRING", {"default": ""}), "key_4": ("STRING", {"default": ""})}}
    RETURN_TYPES = ("FSD_PIPE", ANY, ANY, ANY, ANY); RETURN_NAMES = ("FSD_PIPE", "VALUE_1", "VALUE_2", "VALUE_3", "VALUE_4")
    FUNCTION = "get_custom"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Get a custom field value from the pipe dictionary"
    def get_custom(self, pipe, key_1="", key_2="", key_3="", key_4=""):
        return (pipe, pipe.get(key_1, None) if key_1 else None, pipe.get(key_2, None) if key_2 else None, pipe.get(key_3, None) if key_3 else None, pipe.get(key_4, None) if key_4 else None)

class FSD_UniversalPackDynamic:
    @classmethod
    def INPUT_TYPES(cls): return {"required": {}}
    RETURN_TYPES = ("UNIVERSAL_PIPE",); RETURN_NAMES = ("pipe",); FUNCTION = "pack"; CATEGORY = "FSD Pipe/Bridge"
    DESCRIPTION = "Dynamically pack any set of inputs into a universal pipe"
    def pack(self, **kwargs): return (kwargs,)

# ==========================================
#[FSD/7. Text & Strings]
# ==========================================
class FSD_PromptTextAppend:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "positive_append": ("STRING", {"multiline": True, "default": ""}), "negative_append": ("STRING", {"multiline": True, "default": ""}), "mode": (["Append (Suffix)", "Prepend (Prefix)"],)}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "append"; CATEGORY = "FSD Text"
    DESCRIPTION = "Append text to the prompt (positive and/or negative)"
    def append(self, pipe, positive_append, negative_append, mode):
        p = pipe.copy(); pos = p.get("pos_text", ""); neg = p.get("neg_text", "")
        if mode == "Append (Suffix)":
            pos = pos + ", " + positive_append if pos else positive_append
            neg = neg + ", " + negative_append if neg else negative_append
        else:
            pos = positive_append + ", " + pos if pos else positive_append
            neg = negative_append + ", " + neg if neg else negative_append
        p["pos_text"] = pos; p["neg_text"] = neg

        # Apply updated text — native ComfyUI encode or scheduling parser
        syntax = p.get("syntax_mode", "ComfyUI")
        clip = p.get("clip")
        if syntax == "ComfyUI" and clip is not None:
            p["positive"] = clip.encode_from_tokens_scheduled(clip.tokenize(pos or ""))
            p["negative"] = clip.encode_from_tokens_scheduled(clip.tokenize(neg or ""))
        else:
            seed = p.get("seed", 0)
            p["positive"], p["negative"] = fsd_encode_prompts(p, clip, pos, neg, seed, syntax)
        return (p, )

class FSD_PromptTextReplace:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "find_text": ("STRING", {"default": ""}), "replace_text": ("STRING", {"default": ""})}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "replace"; CATEGORY = "FSD Text"
    DESCRIPTION = "Search-and-replace text in the prompt"
    def replace(self, pipe, find_text, replace_text):
        p = pipe.copy()
        pos = p.get("pos_text", "").replace(find_text, replace_text)
        neg = p.get("neg_text", "").replace(find_text, replace_text)
        p["pos_text"] = pos; p["neg_text"] = neg

        syntax = p.get("syntax_mode", "ComfyUI")
        clip = p.get("clip")
        if syntax == "ComfyUI" and clip is not None:
            p["positive"] = clip.encode_from_tokens_scheduled(clip.tokenize(pos or ""))
            p["negative"] = clip.encode_from_tokens_scheduled(clip.tokenize(neg or ""))
        else:
            seed = p.get("seed", 0)
            p["positive"], p["negative"] = fsd_encode_prompts(p, clip, pos, neg, seed, syntax)
        return (p, )

class FSD_PromptTextOverride:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",), "positive": ("STRING", {"multiline": True, "default": ""}), "negative": ("STRING", {"multiline": True, "default": ""})}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "override"; CATEGORY = "FSD Text"
    DESCRIPTION = "Fully override the prompt text (re-encodes conditioning)"
    def override(self, pipe, positive, negative):
        p = pipe.copy()
        p["pos_text"] = positive; p["neg_text"] = negative

        syntax = p.get("syntax_mode", "ComfyUI")
        clip = p.get("clip")
        if syntax == "ComfyUI" and clip is not None:
            p["positive"] = clip.encode_from_tokens_scheduled(clip.tokenize(positive or ""))
            p["negative"] = clip.encode_from_tokens_scheduled(clip.tokenize(negative or ""))
        else:
            seed = p.get("seed", 0)
            p["positive"], p["negative"] = fsd_encode_prompts(p, clip, positive, negative, seed, syntax)
        return (p, )

class FSD_PromptTextExtract:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"pipe": ("FSD_PIPE",)}}
    RETURN_TYPES = ("FSD_PIPE", "STRING", "STRING"); RETURN_NAMES = ("FSD_PIPE", "POSITIVE_TEXT", "NEGATIVE_TEXT")
    FUNCTION = "extract"; CATEGORY = "FSD Text"
    DESCRIPTION = "Extract raw prompt text strings from pipe"
    def extract(self, pipe): return (pipe, pipe.get("pos_text", ""), pipe.get("neg_text", ""))

class FSD_TriggerGate:
    """Conditional gate: passes pipe through only when gate is open.
       'open_mode' controls whether Open=True or Open=False passes."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "pipe": ("FSD_PIPE",),
            "gate_open": ("BOOLEAN", {"default": True}),
            "open_mode": (["Open=True passes", "Open=False passes"], {"default": "Open=True passes"}),
        }}
    RETURN_TYPES = ("FSD_PIPE", "BOOLEAN")
    RETURN_NAMES = ("FSD_PIPE", "PASSED")
    FUNCTION = "gate"; CATEGORY = "FSD Control"
    DESCRIPTION = "Pass pipe through only when gate is open (configurable open mode)"
    def gate(self, pipe, gate_open, open_mode):
        passes = gate_open if open_mode == "Open=True passes" else not gate_open
        p = pipe.copy() if passes else {}
        p["_gate_passed"] = passes
        return (p, passes)


class FSD_ConditionalRouter:
    """Route pipe to output A or B based on a condition (numeric threshold or bool)."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "pipe": ("FSD_PIPE",),
            "condition": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            "threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            "rule": (["condition >= threshold", "condition < threshold"], {"default": "condition >= threshold"}),
        }}
    RETURN_TYPES = ("FSD_PIPE", "FSD_PIPE", "BOOLEAN")
    RETURN_NAMES = ("pipe_if_true", "pipe_if_false", "match")
    FUNCTION = "route"; CATEGORY = "FSD Control"
    DESCRIPTION = "Route pipe to output depending on a boolean condition"
    def route(self, pipe, condition, threshold, rule):
        match = (condition >= threshold) if rule == "condition >= threshold" else (condition < threshold)
        if match:
            return (pipe.copy(), {}, True)
        else:
            return ({}, pipe.copy(), False)


class FSD_ValueReader:
    """Read any named value from the pipe and output it."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"pipe": ("FSD_PIPE",), "field_name": ("STRING", {"default": "seed"}), "default_value": ("STRING", {"default": "0"})}}
    RETURN_TYPES = ("FSD_PIPE", ANY)
    RETURN_NAMES = ("FSD_PIPE", "VALUE")
    FUNCTION = "read"; CATEGORY = "FSD Control"
    DESCRIPTION = "Read the value of a node widget by its S&R node ID"
    def read(self, pipe, field_name, default_value):
        p = pipe.copy()
        val = p.get(field_name)
        if val is None:
            try: val = eval(default_value)
            except: val = default_value
        return (p, val)


class FSD_ValueWriter:
    """Write any value into a named pipe field."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"pipe": ("FSD_PIPE",), "field_name": ("STRING", {"default": "custom_var"}), "value": (ANY,)},}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "write"; CATEGORY = "FSD Control"
    DESCRIPTION = "Write a value to a node widget by its S&R node ID"
    def write(self, pipe, field_name, value):
        p = pipe.copy(); p[field_name] = value; return (p,)


class FSD_PipeSnapshot:
    """Save pipe state for A/B comparison. Restore with FSD_PipeRestore."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"pipe": ("FSD_PIPE",), "snapshot_name": ("STRING", {"default": "snapshot"})}}
    RETURN_TYPES = ("FSD_PIPE", "STRING")
    RETURN_NAMES = ("FSD_PIPE", "SNAPSHOT_ID")
    FUNCTION = "snap"; CATEGORY = "FSD Control"
    DESCRIPTION = "Save a copy of pipe state for later restore"
    def snap(self, pipe, snapshot_name):
        import json, time
        p = pipe.copy()
        snap_id = f"{snapshot_name}_{int(time.time())}"
        # Store serializable fields
        ser = {}
        for k, v in p.items():
            if isinstance(v, (int, float, str, bool, list, tuple, dict, type(None))):
                try: json.dumps(v, default=str); ser[k] = v
                except: pass
        p["_snapshot"] = {"id": snap_id, "name": snapshot_name, "data": ser}
        return (p, snap_id)


class FSD_PipeRestore:
    """Restore previously saved snapshot fields into current pipe."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"pipe": ("FSD_PIPE",), "snapshot_pipe": ("FSD_PIPE",), "fields": ("STRING", {"default": "seed,steps,cfg", "placeholder": "comma-separated, empty=all"})}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "restore"; CATEGORY = "FSD Control"
    DESCRIPTION = "Restore pipe state saved by PipeSnapshot"
    def restore(self, pipe, snapshot_pipe, fields):
        snap = snapshot_pipe.get("_snapshot", {}).get("data", {})
        if not snap:
            return (pipe.copy(),)
        p = pipe.copy()
        want = {f.strip() for f in fields.split(",") if f.strip()} if fields.strip() else set(snap.keys())
        for k in want:
            if k in snap:
                p[k] = snap[k]
        return (p,)


class FSD_PipeCounter:
    """Counts number of times pipe passed through. Useful for loop control."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"pipe": ("FSD_PIPE",), "reset": ("BOOLEAN", {"default": False})}}
    RETURN_TYPES = ("FSD_PIPE", "INT")
    RETURN_NAMES = ("FSD_PIPE", "COUNT")
    FUNCTION = "count"; CATEGORY = "FSD Control"
    DESCRIPTION = "Count iterations with optional reset, output counter as pipe field"
    def count(self, pipe, reset):
        p = pipe.copy()
        cnt = p.get("_counter", 0)
        if reset: cnt = 0
        else: cnt += 1
        p["_counter"] = cnt
        return (p, cnt)


class FSD_DynamicPipe:
    """Build a pipe from arbitrary key-value pairs. Up to 6 dynamic fields.
       Keys starting with _ are treated as metadata, not model components."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "key_1": ("STRING", {"default": "model"}),
                "val_1": (ANY, {}),
                "key_2": ("STRING", {"default": "clip"}),
                "val_2": (ANY, {}),
                "key_3": ("STRING", {"default": "vae"}),
                "val_3": (ANY, {}),
                "key_4": ("STRING", {"default": "seed"}),
                "val_4": (ANY, {}),
                "key_5": ("STRING", {"default": ""}),
                "val_5": (ANY, {}),
                "key_6": ("STRING", {"default": ""}),
                "val_6": (ANY, {}),
            }
        }
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "build"; CATEGORY = "FSD Pipe/Dynamic"
    DESCRIPTION = "Build a pipe from dynamically defined key/value pairs"
    def build(self, key_1, val_1, key_2, val_2, key_3, val_3, key_4, val_4, key_5, val_5, key_6, val_6):
        p = _ensure_pipe({})
        for k, v in [(key_1, val_1), (key_2, val_2), (key_3, val_3), (key_4, val_4), (key_5, val_5), (key_6, val_6)]:
            if k and k.strip():
                p[k.strip()] = v
        return (p,)


class FSD_PipeKeys:
    """List all key-value pairs currently in the pipe as a readable string."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"pipe": ("FSD_PIPE",)}}
    RETURN_TYPES = ("FSD_PIPE", "STRING", "INT")
    RETURN_NAMES = ("FSD_PIPE", "KEYS_JSON", "COUNT")
    FUNCTION = "list_keys"; CATEGORY = "FSD Pipe/Dynamic"
    DESCRIPTION = "List all keys currently present in the pipe"
    def list_keys(self, pipe):
        import json
        p = pipe.copy()
        try:
            keys_str = json.dumps({k: str(v)[:120] for k, v in p.items()}, indent=2, default=str)
        except:
            keys_str = str(list(p.keys()))
        return (p, keys_str, len(p))


class FSD_PipeFilter:
    """Keep only specified fields from the pipe. Case-insensitive matching."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"pipe": ("FSD_PIPE",), "keep_keys": ("STRING", {"default": "model,clip,vae,positive,negative,seed", "multiline": False, "placeholder": "comma-separated keys"}),}}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "filter"; CATEGORY = "FSD Pipe/Dynamic"
    DESCRIPTION = "Keep only specified keys in the pipe, remove the rest"
    def filter(self, pipe, keep_keys):
        want = {k.strip().lower() for k in keep_keys.split(",") if k.strip()}
        p = {}
        for k, v in pipe.items():
            if k.lower() in want:
                p[k] = v
        return (p,)


class FSD_PipeRename:
    """Rename pipe fields: map old_key → new_key. Up to 3 renames."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "pipe": ("FSD_PIPE",),
            "old_1": ("STRING", {"default": ""}), "new_1": ("STRING", {"default": ""}),
            "old_2": ("STRING", {"default": ""}), "new_2": ("STRING", {"default": ""}),
            "old_3": ("STRING", {"default": ""}), "new_3": ("STRING", {"default": ""}),
        }}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "rename_fields"; CATEGORY = "FSD Pipe/Dynamic"
    DESCRIPTION = "Rename pipe keys (old > new mapping)"
    def rename_fields(self, pipe, old_1, new_1, old_2, new_2, old_3, new_3):
        p = pipe.copy()
        for old_k, new_k in [(old_1, new_1), (old_2, new_2), (old_3, new_3)]:
            if old_k and old_k.strip() and new_k and new_k.strip() and old_k.strip() in p:
                p[new_k.strip()] = p.pop(old_k.strip())
        return (p,)


class FSD_PipeDefault:
    """Set defaults: values only applied if key is missing or None."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "pipe": ("FSD_PIPE",),
            "field_1": ("STRING", {"default": "steps"}), "default_1": ("STRING", {"default": "20"}),
            "field_2": ("STRING", {"default": "cfg"}),   "default_2": ("STRING", {"default": "7.0"}),
            "field_3": ("STRING", {"default": ""}),       "default_3": ("STRING", {"default": ""}),
        }}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "set_defaults"; CATEGORY = "FSD Pipe/Dynamic"
    DESCRIPTION = "Set default values for pipe keys if they are missing or None"
    def set_defaults(self, pipe, field_1, default_1, field_2, default_2, field_3, default_3):
        p = pipe.copy()
        for field, dflt in [(field_1, default_1), (field_2, default_2), (field_3, default_3)]:
            if field and field.strip():
                k = field.strip()
                if p.get(k) is None:
                    try: p[k] = int(dflt)
                    except:
                        try: p[k] = float(dflt)
                        except: p[k] = dflt
        return (p,)


class FSD_PipeEval:
    """Evaluate a Python expression against pipe fields.
       Pipe keys are available as local variables. Returns the result.
       Example expression: 'steps * cfg' or 'pos_text.upper()' or 'seed + 100'"""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"pipe": ("FSD_PIPE",), "expression": ("STRING", {"default": "seed", "multiline": False, "placeholder": "e.g. steps * cfg"}),}}
    RETURN_TYPES = ("FSD_PIPE", ANY)
    RETURN_NAMES = ("FSD_PIPE", "RESULT")
    FUNCTION = "evaluate"; CATEGORY = "FSD Pipe/Dynamic"
    DESCRIPTION = "Evaluate a Python expression against pipe fields"
    def evaluate(self, pipe, expression):
        p = pipe.copy()
        result = None
        # Build safe locals from pipe (filter out non-serializable objects for safety)
        safe_locals = {}
        for k, v in p.items():
            if isinstance(v, (int, float, str, bool, list, tuple, dict, type(None))):
                safe_locals[k] = v
        try:
            result = eval(str(expression), {"__builtins__": {}}, safe_locals)
        except Exception as e:
            result = f"[Error] {e}"
        return (p, result)


class FSD_PipeMap:
    """Transform pipe fields using find/replace or prefix/suffix on text fields.
       Automatically applies to all STRING-type fields in the pipe."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "pipe": ("FSD_PIPE",),
            "operation": (["prefix", "suffix", "replace_all", "strip", "lower", "upper"], {"default": "replace_all"}),
            "find_text": ("STRING", {"default": ""}),
            "replace_text": ("STRING", {"default": ""}),
        }}
    RETURN_TYPES = ("FSD_PIPE",); FUNCTION = "map_fields"; CATEGORY = "FSD Pipe/Dynamic"
    DESCRIPTION = "Transform pipe fields using a field mapping definition"
    def map_fields(self, pipe, operation, find_text, replace_text):
        p = pipe.copy()
        for k, v in p.items():
            if not isinstance(v, str):
                continue
            if operation == "prefix":
                p[k] = find_text + v
            elif operation == "suffix":
                p[k] = v + find_text
            elif operation == "replace_all" and find_text:
                p[k] = v.replace(find_text, replace_text)
            elif operation == "strip":
                p[k] = v.strip()
            elif operation == "lower":
                p[k] = v.lower()
            elif operation == "upper":
                p[k] = v.upper()
        return (p,)


class FSD_PipeDump:
    """Export all pipe fields as strings (for debugging / logging / dashboard)."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"pipe": ("FSD_PIPE",)}}
    RETURN_TYPES = ("FSD_PIPE", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("FSD_PIPE", "ALL_KEYS", "KEY_VALUES", "COUNT", "SUMMARY")
    FUNCTION = "dump"; CATEGORY = "FSD Pipe/Dynamic"
    DESCRIPTION = "Dump all pipe fields as a JSON-like text for debugging"
    def dump(self, pipe):
        p = pipe.copy()
        import json
        all_keys = ", ".join(p.keys())
        kv_pairs = []
        for k, v in p.items():
            try: sv = str(v)[:100]
            except: sv = "<unprintable>"
            kv_pairs.append(f"{k}: {sv}")
        summary = f"Pipe: {len(p)} fields"
        if p.get("model"): summary += f", model=OK"
        if p.get("clip"): summary += f", clip=OK"
        if p.get("vae"): summary += f", vae=OK"
        if p.get("pos_text"): summary += f", pos={len(p.get('pos_text',''))}chars"
        if p.get("neg_text"): summary += f", neg={len(p.get('neg_text',''))}chars"
        return (p, all_keys, "\n".join(kv_pairs), len(p), summary)


# ==========================================

# NODE REGISTRATION MAPPINGS
# ==========================================
NODE_CLASS_MAPPINGS = {
    # 0. Setup
    "FSD_NativeCheckpointLoader": FSD_NativeCheckpointLoader,
    "FSD_NativeVAELoader": FSD_NativeVAELoader,
    "FSD_NativeEmptyLatent": FSD_NativeEmptyLatent,
    "FSD_AnimaLoader": FSD_AnimaLoader,
    "FSD_DanbooruGalleryPipe": FSD_DanbooruGalleryPipe,

    # 1. Core
    "FSD_TopPanel": FSD_TopPanel,
    "FSD_DiffusionLoader": FSD_DiffusionLoader,
    "FSD_Dimensions": FSD_Dimensions,
    "FSD_SamplerSettings": FSD_SamplerSettings,
    "FSD_Generate": FSD_Generate,
    "FSD_SaveImage": FSD_SaveImage,

    # 2. Conditioning
    "FSD_Prompts": FSD_Prompts,
    "FSD_ControlNet": FSD_ControlNet,
    "FSD_IPAdapter": FSD_IPAdapter,
    "FSD_ConditioningCombine": FSD_ConditioningCombine,

    # 3. Image
    "FSD_Img2Img": FSD_Img2Img,
    "FSD_Inpaint": FSD_Inpaint,
    "FSD_SAM3Detailer": FSD_SAM3Detailer,
    "FSD_HiresFix_Latent": FSD_HiresFix_Latent,
    "FSD_HiresFix_Pixel": FSD_HiresFix_Pixel,
    "FSD_TiledUpscale": FSD_TiledUpscale,
    "FSD_VAEEncode": FSD_VAEEncode,
    "FSD_VAEDecode": FSD_VAEDecode,
    "FSD_LatentComposite": FSD_LatentComposite,

    # 3B. Standalone
    "FSD_Text2Img": FSD_Text2Img,
    "FSD_Img2Img_Standalone": FSD_Img2Img_Standalone,
    "FSD_Upscale_Standalone": FSD_Upscale_Standalone,

    # 4. Routing
    "FSD_PipeSwitch": FSD_PipeSwitch,
    "FSD_PipeDiverter": FSD_PipeDiverter,
    "FSD_LazySwitch": FSD_LazySwitch,
    "FSD_DynamicPipeSwitch": FSD_DynamicPipeSwitch,
    "FSD_DynamicPipeDiverter": FSD_DynamicPipeDiverter,
    "FSD_Bypass": FSD_Bypass,
    "FSD_RandomPipeSwitch": FSD_RandomPipeSwitch,
    "FSD_PipeBatchCombine": FSD_PipeBatchCombine,
    "FSD_OverrideSettings": FSD_OverrideSettings,
    "FSD_LatentScale": FSD_LatentScale,
    "FSD_SetDenoise": FSD_SetDenoise,
    "FSD_ClearLatent": FSD_ClearLatent,
    "FSD_SetLatentNoiseMask": FSD_SetLatentNoiseMask,
    "FSD_PipeAutoFix": FSD_PipeAutoFix,
    "FSD_PipeBranch": FSD_PipeBranch,
    "FSD_PipeMergeSelective": FSD_PipeMergeSelective,
    "FSD_PipePreview": FSD_PipePreview,

    # 5. Bridge
    "FSD_PipeToKSampler": FSD_PipeToKSampler,
    "FSD_PipeToBasicPipe_Impact": FSD_PipeToBasicPipe_Impact,
    "FSD_UnpackSettings": FSD_UnpackSettings,
    "FSD_PipeInfo": FSD_PipeInfo,
    "FSD_PipeEdit": FSD_PipeEdit,
    "FSD_PipeMerge": FSD_PipeMerge,
    "FSD_PackPipe": FSD_PackPipe,
    "FSD_UnpackPipe": FSD_UnpackPipe,
    "FSD_PackBasicPipe": FSD_PackBasicPipe,
    "FSD_UnpackBasicPipe": FSD_UnpackBasicPipe,
    "FSD_EditBasicPipe": FSD_EditBasicPipe,
    "FSD_UniversalPackDynamic": FSD_UniversalPackDynamic,
    "FSD_UpdatePipeModel": FSD_UpdatePipeModel,
    "FSD_UpdatePipeClip": FSD_UpdatePipeClip,
    "FSD_UpdatePipeVae": FSD_UpdatePipeVae,
    "FSD_UpdatePipePositive": FSD_UpdatePipePositive,
    "FSD_UpdatePipeNegative": FSD_UpdatePipeNegative,
    "FSD_UpdatePipeLatent": FSD_UpdatePipeLatent,
    "FSD_UpdatePipeSegs": FSD_UpdatePipeSegs,
    "FSD_ExtractPipeSegs": FSD_ExtractPipeSegs,
    "FSD_PipeSetCustom": FSD_PipeSetCustom,
    "FSD_PipeGetCustom": FSD_PipeGetCustom,

    # 6. Text
    "FSD_PromptTextAppend": FSD_PromptTextAppend,
    "FSD_PromptTextReplace": FSD_PromptTextReplace,
    "FSD_PromptTextOverride": FSD_PromptTextOverride,
    "FSD_PromptTextExtract": FSD_PromptTextExtract,

    # 7. Control
    "FSD_TriggerGate": FSD_TriggerGate,
    "FSD_ConditionalRouter": FSD_ConditionalRouter,
    "FSD_ValueReader": FSD_ValueReader,
    "FSD_ValueWriter": FSD_ValueWriter,
    "FSD_PipeSnapshot": FSD_PipeSnapshot,
    "FSD_PipeRestore": FSD_PipeRestore,
    "FSD_PipeCounter": FSD_PipeCounter,

    # 8. Dynamic
    "FSD_DynamicPipe": FSD_DynamicPipe,
    "FSD_PipeKeys": FSD_PipeKeys,
    "FSD_PipeFilter": FSD_PipeFilter,
    "FSD_PipeRename": FSD_PipeRename,
    "FSD_PipeDefault": FSD_PipeDefault,
    "FSD_PipeEval": FSD_PipeEval,
    "FSD_PipeMap": FSD_PipeMap,
    "FSD_PipeDump": FSD_PipeDump,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    # 0. Setup
    "FSD_NativeCheckpointLoader": "Setup - Load Checkpoint",
    "FSD_NativeVAELoader": "Setup - Load VAE",
    "FSD_NativeEmptyLatent": "Setup - Empty Latent",
    "FSD_AnimaLoader": "Setup - Anima/Cosmos Loader",
    "FSD_DanbooruGalleryPipe": "Setup - Danbooru Gallery (Pipe)",

    # 1. Core
    "FSD_TopPanel": "Core - Load Checkpoint & VAE",
    "FSD_DiffusionLoader": "Core - SDXL Loader",
    "FSD_Dimensions": "Core - Dimensions",
    "FSD_SamplerSettings": "Core - Sampler",
    "FSD_Generate": "Core - Generate",
    "FSD_SaveImage": "Core - Save Image",

    # 2. Conditioning
    "FSD_Prompts": "Cond - Encode Prompts",
    "FSD_ControlNet": "Cond - ControlNet",
    "FSD_IPAdapter": "Cond - IPAdapter",
    "FSD_ConditioningCombine": "Cond - Combine",

    # 3. Image
    "FSD_Img2Img": "Image - Img2Img",
    "FSD_Inpaint": "Image - Inpaint",
    "FSD_SAM3Detailer": "Image - SAM3 Detailer",
    "FSD_HiresFix_Latent": "Image - HiresFix Latent",
    "FSD_HiresFix_Pixel": "Image - HiresFix Model",
    "FSD_TiledUpscale": "Image - SD Upscale",
    "FSD_VAEEncode": "Image - VAE Encode",
    "FSD_VAEDecode": "Image - VAE Decode",
    "FSD_LatentComposite": "Image - Latent Composite",

    # 3B. Standalone
    "FSD_Text2Img": "Standalone - Text to Image",
    "FSD_Img2Img_Standalone": "Standalone - Image to Image",
    "FSD_Upscale_Standalone": "Standalone - Upscale",

    # 4. Routing
    "FSD_PipeSwitch": "Route - Switch",
    "FSD_PipeDiverter": "Route - Diverter (Lazy)",
    "FSD_LazySwitch": "Route - Lazy Switch",
    "FSD_DynamicPipeSwitch": "Route - Dyn Switch (Lazy)",
    "FSD_DynamicPipeDiverter": "Route - Dyn Diverter (Lazy)",
    "FSD_Bypass": "Route - Bypass",
    "FSD_RandomPipeSwitch": "Route - Random Switch",
    "FSD_PipeBatchCombine": "Route - Batch Combine",
    "FSD_OverrideSettings": "Route - Override",
    "FSD_LatentScale": "Route - Latent Scale",
    "FSD_SetDenoise": "Route - Set Denoise",
    "FSD_ClearLatent": "Route - Clear Latent",
    "FSD_SetLatentNoiseMask": "Route - Noise Mask",
    "FSD_PipeAutoFix": "Route - Auto Fix",
    "FSD_PipeBranch": "Route - Branch",
    "FSD_PipeMergeSelective": "Route - Selective Merge",
    "FSD_PipePreview": "Route - Preview",

    # 5. Bridge
    "FSD_PipeToKSampler": "Bridge - To KSampler",
    "FSD_PipeToBasicPipe_Impact": "Bridge - To BasicPipe",
    "FSD_UnpackSettings": "Bridge - Unpack Settings",
    "FSD_PipeInfo": "Bridge - Info",
    "FSD_PipeEdit": "Bridge - Edit",
    "FSD_PipeMerge": "Bridge - Merge",
    "FSD_PackPipe": "Bridge - Pack All",
    "FSD_UnpackPipe": "Bridge - Unpack All",
    "FSD_PackBasicPipe": "Bridge - Pack Basic",
    "FSD_UnpackBasicPipe": "Bridge - Unpack Basic",
    "FSD_EditBasicPipe": "Bridge - Edit Basic",
    "FSD_UniversalPackDynamic": "Bridge - Universal Pack",
    "FSD_UpdatePipeModel": "Bridge - Inject Model",
    "FSD_UpdatePipeClip": "Bridge - Inject CLIP",
    "FSD_UpdatePipeVae": "Bridge - Inject VAE",
    "FSD_UpdatePipePositive": "Bridge - Inject Positive",
    "FSD_UpdatePipeNegative": "Bridge - Inject Negative",
    "FSD_UpdatePipeLatent": "Bridge - Inject Latent",
    "FSD_UpdatePipeSegs": "Bridge - Inject SEGS",
    "FSD_ExtractPipeSegs": "Bridge - Extract SEGS",
    "FSD_PipeSetCustom": "Bridge - Set Field",
    "FSD_PipeGetCustom": "Bridge - Get Field",

    # 6. Text
    "FSD_PromptTextAppend": "Text - Append",
    "FSD_PromptTextReplace": "Text - Replace",
    "FSD_PromptTextOverride": "Text - Override",
    "FSD_PromptTextExtract": "Text - Extract",

    # 7. Control
    "FSD_TriggerGate": "Ctrl - Gate",
    "FSD_ConditionalRouter": "Ctrl - Router",
    "FSD_ValueReader": "Ctrl - Read",
    "FSD_ValueWriter": "Ctrl - Write",
    "FSD_PipeSnapshot": "Ctrl - Snap",
    "FSD_PipeRestore": "Ctrl - Restore",
    "FSD_PipeCounter": "Ctrl - Counter",

    # 8. Dynamic
    "FSD_DynamicPipe": "Dynamic - Build",
    "FSD_PipeKeys": "Dynamic - Keys",
    "FSD_PipeFilter": "Dynamic - Filter",
    "FSD_PipeRename": "Dynamic - Rename",
    "FSD_PipeDefault": "Dynamic - Defaults",
    "FSD_PipeEval": "Dynamic - Eval",
    "FSD_PipeMap": "Dynamic - Map",
    "FSD_PipeDump": "Dynamic - Dump",
}