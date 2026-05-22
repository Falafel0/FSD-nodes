import os
import random
import re
import folder_paths
import comfy.sd
import comfy.samplers
import comfy.utils
import torch
import torch.nn.functional as F
import torchvision.transforms.functional as TF
import nodes

MAX_RESOLUTION = 8192

# ==========================================
# GLOBAL STATE & ANY TYPE
# ==========================================
GLOBAL_STACKS = {}
GLOBAL_SIGNALS = {}

def _reset_global_state():
    """Called before each prompt execution to clear transient state."""
    GLOBAL_STACKS.clear()
    GLOBAL_SIGNALS.clear()
    global _WORKFLOW_GROUPS, _WORKFLOW_NODES
    _WORKFLOW_GROUPS = {}
    _WORKFLOW_NODES = {}

# Hook into ComfyUI execution start via PromptServer
try:
    from server import PromptServer
    _orig_post_prompt = None
    if hasattr(PromptServer.instance, "post_prompt"):
        _orig_post_prompt = PromptServer.instance.post_prompt
        async def _patched_post_prompt(self, json_data):
            _reset_global_state()
            if _orig_post_prompt:
                await _orig_post_prompt(json_data)
        PromptServer.instance.post_prompt = _patched_post_prompt.__get__(PromptServer.instance)
except Exception:
    pass

class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False

ANY = AnyType("*")

# WORKFLOW GROUP CACHE — populated from extra_pnginfo during execution
_WORKFLOW_GROUPS = {}
_WORKFLOW_NODES = {}

def _load_workflow_cache(extra_pnginfo):
    """Populate group/node cache from workflow JSON in extra_pnginfo."""
    global _WORKFLOW_GROUPS, _WORKFLOW_NODES
    if not extra_pnginfo or not isinstance(extra_pnginfo, dict):
        return
    workflow = extra_pnginfo.get("workflow")
    if not workflow:
        return
    # Reset caches
    _WORKFLOW_GROUPS = {}
    _WORKFLOW_NODES = {}
    # Index nodes by id and title
    for node in workflow.get("nodes", []):
        nid = str(node.get("id", ""))
        ntype = node.get("type", "")
        ntitle = node.get("title", "")
        _WORKFLOW_NODES[nid] = {"type": ntype, "title": ntitle}
    # Parse groups — ComfyUI stores group→node mapping in extra.groupNodes or
    # derives it from bounding boxes; try groupNodes first, fall back to
    # recomputing from node positions.
    extra = workflow.get("extra", {})
    group_nodes = extra.get("groupNodes", {})
    if group_nodes:
        _WORKFLOW_GROUPS = {
            str(gname): [str(nid) for nid in nids]
            for gname, nids in group_nodes.items()
        }
    else:
        # Fallback: compute from bounding boxes
        for group in workflow.get("groups", []):
            gtitle = group.get("title", "")
            if not gtitle:
                continue
            bb = group.get("bounding") or group.get("bounding_box", [])
            if len(bb) < 4:
                continue
            gx, gy, gw, gh = bb[0], bb[1], bb[2], bb[3]
            inside = []
            for node in workflow.get("nodes", []):
                pos = node.get("pos", [])
                size = node.get("size", {})
                if len(pos) < 2:
                    continue
                nx, ny = pos[0], pos[1]
                nw = size.get("0", 140)
                nh = size.get("1", 100)
                # Node centre vs group rect
                if (gx <= nx + nw / 2 <= gx + gw and
                    gy <= ny + nh / 2 <= gy + gh):
                    inside.append(str(node.get("id", "")))
            _WORKFLOW_GROUPS[gtitle] = inside

def _get_nodes_in_group(group_name):
    return _WORKFLOW_GROUPS.get(group_name, [])

def _parse_multi_ids(multi_id_string):
    if not multi_id_string:
        return []
    return[x.strip() for x in multi_id_string.split(",") if x.strip()]


# ==========================================
# RESIZE & BLEND UTILS FOR FSD PIPES
# ==========================================
def fsd_resize(image, target_w, target_h, mode):
    B, H, W, C = image.shape
    if target_w <= 0 or target_h <= 0:
        target_w = max(1, target_w)
        target_h = max(1, target_h)
    if H <= 0 or W <= 0:
        return image
    img_moved = image.movedim(-1, 1) # (B, C, H, W)

    if mode == "Just resize":
        resized = F.interpolate(img_moved, size=(target_h, target_w), mode="bicubic", align_corners=False)

    elif mode == "Crop and resize":
        ratio_img = W / H
        ratio_tgt = target_w / target_h
        if ratio_img > ratio_tgt:
            new_W = int(H * ratio_tgt)
            offset = (W - new_W) // 2
            cropped = img_moved[:, :, :, offset:offset+new_W]
        else:
            new_H = int(W / ratio_tgt)
            offset = (H - new_H) // 2
            cropped = img_moved[:, :, offset:offset+new_H, :]
        resized = F.interpolate(cropped, size=(target_h, target_w), mode="bicubic", align_corners=False)

    elif mode == "Resize and fill":
        ratio_img = W / H
        ratio_tgt = target_w / target_h
        if ratio_img > ratio_tgt:
            new_W = target_w; new_H = int(target_w / ratio_img)
        else:
            new_H = target_h; new_W = int(target_h * ratio_img)

        resized_inner = F.interpolate(img_moved, size=(new_H, new_W), mode="bicubic", align_corners=False)
        bg = F.interpolate(img_moved, size=(target_h, target_w), mode="bicubic", align_corners=False)
        bg = TF.gaussian_blur(bg, kernel_size=[51, 51])

        y_off = (target_h - new_H) // 2
        x_off = (target_w - new_W) // 2
        bg[:, :, y_off:y_off+new_H, x_off:x_off+new_W] = resized_inner
        resized = bg

    return resized.movedim(1, -1).clamp(0, 1)

# ==========================================
# DYNAMIC PROMPT & SCHEDULING PARSER
# ==========================================
def _process_dynamic_prompt(pipe, text, seed, syntax_mode):
    rnd = random.Random(seed)

    # 1. Умное разделение (игнорирует разделители внутри () и <>)
    def smart_split(text, char):
        result =[]
        current = ""
        paren_depth = 0
        angle_depth = 0
        escape_next = False
        for c in text:
            if escape_next:
                current += c
                escape_next = False
                continue
            if c == '\\':
                current += c
                escape_next = True
                continue
            if c == '(': paren_depth += 1
            elif c == ')': paren_depth -= 1
            elif c == '<': angle_depth += 1
            elif c == '>': angle_depth -= 1

            if c == char and paren_depth == 0 and angle_depth == 0:
                result.append(current)
                current = ""
            else:
                current += c
        result.append(current)
        return result

    # 2. Random wildcards {A|B|C} (Без ограничений)
    prev_text = ""
    while text != prev_text and "{" in text:
        prev_text = text
        text = re.sub(r'\{([^{}]+)\}', lambda m: rnd.choice(smart_split(m.group(1), '|')), text)

    # 3. Трансляция весов A1111: [tag] -> (tag:0.909)
    if syntax_mode == "A1111":
        def repl_a1111(m):
            inner = m.group(1)
            opts = smart_split(inner, '|')
            parts = smart_split(inner, ':')
            # Если внутри есть команды расписания или чередования - оставляем парсеру ниже
            if len(opts) > 1 or len(parts) >= 2:
                return m.group(0)
            return f"({inner.strip()}:0.909)"
        text = re.sub(r'\[([^\[\]]+)\]', repl_a1111, text)

    # 4. Time Scheduling & Alternating
    total_steps = pipe.get("steps", 20)
    segments =[]
    start_step = 0
    prev_frame = None

    for step in range(total_steps):
        curr_text = text
        # Раскрываем скобки изнутри наружу (поддерживает любую вложенность)
        while True:
            def resolve_bracket(m):
                inner = m.group(1)

                # А) Чередование [A|B|C|D]
                opts = smart_split(inner, '|')
                if len(opts) > 1:
                    return opts[step % len(opts)]

                # Б) Расписание[A:B:C:step1:step2]
                parts = smart_split(inner, ':')
                if len(parts) >= 2:
                    num_floats = 0
                    # Ищем числа (шаги или проценты) с конца
                    for p in reversed(parts):
                        if p.strip() == "" and num_floats == 0:
                            break
                        try:
                            float(p)
                            num_floats += 1
                        except ValueError:
                            break

                    k = min(num_floats, len(parts) - 1)

                    if k > 0:
                        # Логика поведения в стиле A1111
                        if k == 1 and len(parts) == 2:
                            # [to:when] - Отложенный старт
                            texts = ["", parts[0]]
                            thresholds_str = [parts[1]]
                        elif k == 1 and len(parts) == 3 and parts[1].strip() == "":
                            #[from::when] - Ранняя остановка
                            texts = [parts[0], ""]
                            thresholds_str = [parts[2]]
                        else:
                            # [from:to:when] или [A:B:C:10:20]
                            thresholds_str = parts[-k:]
                            texts = parts[:-k]

                            # Если текст порвало из-за двоеточий внутри (которые не были в скобках)
                            diff = len(texts) - (k + 1)
                            if diff > 0:
                                joined_first = ":".join(texts[:diff+1])
                                texts =[joined_first] + texts[diff+1:]
                            elif diff < 0:
                                texts = [""] * abs(diff) + texts

                        # Конвертируем пороги в проценты от общего числа шагов
                        thresholds =[]
                        for p in thresholds_str:
                            val = float(p)
                            thresholds.append(val if val <= 1.0 else val / max(1, total_steps))

                        # Определяем текущий токен
                        curr_pct = step / max(1, total_steps)
                        text_index = sum(1 for t in thresholds if curr_pct >= t)
                        text_index = min(text_index, len(texts) - 1)

                        return texts[text_index]

                return f"__BRACKET_{inner}__"

            new_text = re.sub(r'\[([^\[\]]+)\]', resolve_bracket, curr_text)
            if new_text == curr_text: break
            curr_text = new_text

        curr_text = re.sub(r'__BRACKET_(.*?)__', r'[\1]', curr_text)

        # Собираем таймлайн (отрезки времени)
        if prev_frame is None:
            prev_frame = curr_text
        elif curr_text != prev_frame:
            segments.append((start_step, step, prev_frame))
            start_step = step
            prev_frame = curr_text

    segments.append((start_step, total_steps, prev_frame))
    return segments

def fsd_encode_prompts(pipe, clip, pos_text, neg_text, seed=0, syntax_mode="ComfyUI"):
    if not clip and not pos_text and not neg_text:
        return ([], [])
    pos_text = pos_text or ""; neg_text = neg_text or ""
    pos_segments = _process_dynamic_prompt(pipe, pos_text, seed, syntax_mode)
    neg_segments = _process_dynamic_prompt(pipe, neg_text, seed + 1, syntax_mode)

    if not clip:
        return ([], [])

    def encode_segs(segments):
        final_cond =[]
        guidance = pipe.get("guidance", 3.5)
        for start, end, seg_text in segments:
            start_pct = start / max(1, pipe.get("steps", 20))
            end_pct = end / max(1, pipe.get("steps", 20))

            tokens = clip.tokenize(seg_text)

            # Only pass start_percent/end_percent for dynamic scheduling (multiple segments
            # or non-full-range single segment). For full-range single prompts, omit them
            # to match native CLIPTextEncode behaviour — avoids sampler timestep_range
            # checks that may interfere with FLOW/FLUX model sigma schedules.
            if len(segments) > 1 or start_pct > 0.0 or end_pct < 1.0:
                add_dict = {"guidance": guidance, "start_percent": start_pct, "end_percent": end_pct}
            else:
                add_dict = {"guidance": guidance}

            result = clip.encode_from_tokens_scheduled(tokens, add_dict=add_dict)
            final_cond.extend(result)
        return final_cond

    return encode_segs(pos_segments), encode_segs(neg_segments)


def _ensure_pipe(pipe, model=None, clip=None, vae=None, seed=0):
    """Fill missing pipe fields with safe defaults. Ensures compatibility across all nodes."""
    if pipe is None:
        pipe = {}
    p = pipe.copy() if hasattr(pipe, 'copy') else dict(pipe)
    # Core components
    p.setdefault("model", model)
    p.setdefault("clip", clip)
    p.setdefault("vae", vae)
    # Sampler settings
    p.setdefault("steps", 20)
    p.setdefault("cfg", 7.0)
    p.setdefault("sampler_name", "euler")
    p.setdefault("scheduler", "normal")
    p.setdefault("denoise", 1.0)
    p.setdefault("seed", seed)
    # Dimensions
    p.setdefault("target_width", 512)
    p.setdefault("target_height", 512)
    p.setdefault("batch_size", 1)
    # Conditioning
    p.setdefault("positive", [])
    p.setdefault("negative", [])
    p.setdefault("guidance", 3.5)
    # Text
    p.setdefault("pos_text", "")
    p.setdefault("neg_text", "")
    p.setdefault("syntax_mode", "ComfyUI")
    # Latent
    p.setdefault("latent", None)
    return p


def fsd_resolve_prompts(pipe, pos_field, neg_field, prompt_mode, force_reencode=False):
    """Resolve final prompts for override nodes.

    ComfyUI mode uses native CLIPTextEncode (no scheduling/guidance).
    A1111/ComfyUI+ modes use the dynamic prompt parser with scheduling.

    Args:
        pipe: FSD_PIPE dict
        pos_field: positive text from node widget
        neg_field: negative text from node widget
        prompt_mode: "Replace", "Append", "If not empty"
        force_reencode: if True, always re-encode from text even if prompts
                       match pipe text (prevents ControlNet/IPAdapter conditioning
                       from leaking into HiresFix/SAM3Detailer second pass)

    Returns:
        (pos_cond, neg_cond) — encoded conditioning tensors
    """
    pipe_pos = pipe.get("pos_text", "") or ""
    pipe_neg = pipe.get("neg_text", "") or ""

    if prompt_mode == "Replace":
        final_pos = pos_field or pipe_pos
        final_neg = neg_field or pipe_neg
    elif prompt_mode == "Append":
        final_pos = (pipe_pos + " " + pos_field).strip() if pos_field else pipe_pos
        final_neg = (pipe_neg + " " + neg_field).strip() if neg_field else pipe_neg
    else:  # "If not empty"
        final_pos = pos_field if (pos_field or "").strip() else pipe_pos
        final_neg = neg_field if (neg_field or "").strip() else pipe_neg

    if not force_reencode and final_pos == pipe_pos and final_neg == pipe_neg:
        return pipe.get("positive", []), pipe.get("negative", [])

    syntax_mode = pipe.get("syntax_mode", "ComfyUI")
    if syntax_mode == "ComfyUI":
        clip = pipe.get("clip")
        if clip is None:
            pos_cond, neg_cond = ([], [])
        else:
            pos_cond = clip.encode_from_tokens_scheduled(clip.tokenize(final_pos or ""))
            neg_cond = clip.encode_from_tokens_scheduled(clip.tokenize(final_neg or ""))
    else:
        pos_cond, neg_cond = fsd_encode_prompts(
            pipe, pipe.get("clip"),
            final_pos, final_neg,
            pipe.get("seed", 0),
            syntax_mode
        )

    # Re-apply ControlNet if it was stored in the pipe by FSD_ControlNet
    # (skip when force_reencode — HiresFix/SAM3 second pass must be clean)
    if not force_reencode:
        cn_list = pipe.get("_fsd_controlnet", [])
        for cn_data in cn_list:
            cnet = cn_data["control_net_override"]
            if cnet is None:
                cnet = nodes.ControlNetLoader().load_controlnet(cn_data["control_net_name"])[0]
            pos_cond, neg_cond = nodes.NODE_CLASS_MAPPINGS["ControlNetApplyAdvanced"]().apply_controlnet(
                pos_cond, neg_cond, cnet, cn_data["image"],
                cn_data["strength"], cn_data["start_percent"], cn_data["end_percent"],
                vae=cn_data.get("vae")
            )

    return (pos_cond, neg_cond)


def fsd_native_resolve_prompts(pipe, pos_field, neg_field, prompt_mode):
    """Resolve final prompts like fsd_resolve_prompts, but encode via native CLIPTextEncode.

    Used when syntax_mode == 'ComfyUI' — tokenize+encode without scheduling/guidance,
    producing conditioning identical to nodes.CLIPTextEncode.

    Args:
        pipe: FSD_PIPE dict
        pos_field: positive text from node widget
        neg_field: negative text from node widget
        prompt_mode: "Replace", "Append", "If not empty"

    Returns:
        (pos_cond, neg_cond) — native clip.encode_from_tokens_scheduled conditioning
    """
    clip = pipe.get("clip")
    if clip is None:
        return ([], [])
    pipe_pos = pipe.get("pos_text", "") or ""
    pipe_neg = pipe.get("neg_text", "") or ""

    if prompt_mode == "Replace":
        final_pos = pos_field or pipe_pos
        final_neg = neg_field or pipe_neg
    elif prompt_mode == "Append":
        final_pos = (pipe_pos + " " + pos_field).strip() if pos_field else pipe_pos
        final_neg = (pipe_neg + " " + neg_field).strip() if neg_field else pipe_neg
    else:  # "If not empty"
        final_pos = pos_field if (pos_field or "").strip() else pipe_pos
        final_neg = neg_field if (neg_field or "").strip() else pipe_neg

    pos_cond = clip.encode_from_tokens_scheduled(clip.tokenize(final_pos or ""))
    neg_cond = clip.encode_from_tokens_scheduled(clip.tokenize(final_neg or ""))
    return (pos_cond, neg_cond)
