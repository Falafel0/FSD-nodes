from .utils import *

# ==========================================
#[FSD/10. Resolution Parser]
# ==========================================
class FSD_ResolutionParser:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "resolution": ("STRING", {"default": "1920x1080", "multiline": False}),
            }
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("width", "height")
    FUNCTION = "parse"
    CATEGORY = "FSD Utility"

    def parse(self, resolution):
        import re
        m = re.match(r"^\s*(\d+)\s*[x×XхХ]\s*(\d+)\s*$", resolution)
        if m:
            width = int(m.group(1))
            height = int(m.group(2))
            return (width, height)
        # fallback: try any two numbers separated by non-digits
        nums = re.findall(r"\d+", resolution)
        if len(nums) >= 2:
            return (int(nums[0]), int(nums[1]))
        return (0, 0)

# ==========================================
#[FSD/12. Switches & Gates]
# ==========================================
class FSD_DynamicSwitchANY:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {"index": ("INT", {"default": 0, "min": 0, "max": 19})},
            "optional": {}
        }
        for i in range(20):
            inputs["optional"][f"input_{i}"] = (ANY)
        return inputs

    RETURN_TYPES = (ANY,)
    FUNCTION = "execute"
    CATEGORY = "FSD Switch"

    def execute(self, index, **kwargs):
        return (kwargs.get(f"input_{index}"))


class FSD_DynamicDiverterANY:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"index": ("INT", {"default": 0, "min": 0, "max": 19})},
            "optional": {"value": (ANY)}
        }
    RETURN_TYPES = tuple([ANY] * 20)
    RETURN_NAMES = tuple([f"out_{i}" for i in range(20)])
    FUNCTION = "execute"
    CATEGORY = "FSD Switch"

    def execute(self, index, value=None, **kwargs):
        outs =[None] * 20
        if 0 <= index < 20: outs[index] = value
        return tuple(outs)


class FSD_BooleanSwitchANY:
    @classmethod
    def INPUT_TYPES(cls): return {
        "required": {"condition": ("BOOLEAN", {"default": True})},
        "optional": {"on_true": (ANY), "on_false": (ANY)}
    }
    RETURN_TYPES = (ANY,)
    RETURN_NAMES = ("output",)
    FUNCTION = "execute"
    CATEGORY = "FSD Switch"

    def execute(self, condition, on_true=None, on_false=None, **kwargs):
        return (on_true if condition else on_false)


class FSD_BooleanDiverterANY:
    @classmethod
    def INPUT_TYPES(cls): return {
        "required": {"condition": ("BOOLEAN", {"default": True})},
        "optional": {"value": (ANY)}
    }
    RETURN_TYPES = (ANY, ANY)
    RETURN_NAMES = ("out_true", "out_false")
    FUNCTION = "execute"
    CATEGORY = "FSD Switch"

    def execute(self, condition, value=None, **kwargs):
        return (value, None) if condition else (None, value)


class FSD_GateANY:
    @classmethod
    def INPUT_TYPES(cls): return {
        "required": {"open_gate": ("BOOLEAN", {"default": True})},
        "optional": {"value": (ANY)}
    }
    RETURN_TYPES = (ANY,)
    FUNCTION = "execute"
    CATEGORY = "FSD Switch"

    def execute(self, open_gate, value=None, **kwargs):
        return (value) if open_gate else (None)


# ==========================================
#[FSD/14. Signals & Mutators]
# ==========================================
class FSD_AdvancedNodeBypasser:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "state": ("BOOLEAN", {"default": False}),
                "action": (["Bypass", "Mute"], {"default": "Bypass"}),
                "target_type": (["Group Name", "Node Title", "Node Type", "Node IDs"], {"default": "Group Name"}),
                "match_type": (["Exact", "Contains", "Regex"], {"default": "Contains"}),
                "target": ("STRING", {"default": ""})
            },
            "hidden": {"extra_pnginfo": "EXTRA_PNGINFO"},

        }

    RETURN_TYPES = ()
    FUNCTION = "execute"
    CATEGORY = "FSD Signal"
    OUTPUT_NODE = True

    def execute(self, state, action, target_type, match_type, target, extra_pnginfo=None, **kwargs):
        if extra_pnginfo is not None:
            _load_workflow_cache(extra_pnginfo)
        mode_code = 2 if action == "Mute" else 4  # 2=Mute, 4=Bypass
        if not state:
            mode_code = 0  # restore

        # Build node ID list for backend API event.
        # Exact/Contains/Regex matching done fully on JS side; pass raw params.
        node_ids = []
        if target_type == "Node IDs":
            node_ids = _parse_multi_ids(target)
        elif target_type == "Group Name":
            node_ids = _get_nodes_in_group(target)

        try:
            from server import PromptServer
            PromptServer.instance.send_sync("fsd_mutate_state", {
                "mode": mode_code,
                "target_type": target_type,
                "match_type": match_type,
                "target": target,
                "group_name": target if target_type == "Group Name" else None,
                "nodes": node_ids if target_type == "Node IDs" else [],
            })
        except Exception:
            pass
        return ()


# ==========================================
#[FSD/9. Workflow Controls]
# ==========================================
class FSD_ToggleSwitch:
    """Dashboard toggle: ON/OFF with configurable labels, pass-through pipe."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "state": ("BOOLEAN", {"default": False}),
            "label_on": ("STRING", {"default": "ENABLED"}),
            "label_off": ("STRING", {"default": "DISABLED"}),
        }, "optional": { "pass_when_on": (ANY), "pass_when_off": (ANY)}}
    RETURN_TYPES = ("BOOLEAN", ANY)
    RETURN_NAMES = ("STATE", "PASSED_VALUE")
    FUNCTION = "toggle"; CATEGORY = "FSD Control"

    def toggle(self, state, label_on, label_off, pass_when_on=None, pass_when_off=None):
        p = {}
        p["_toggle_state"] = state
        p["_toggle_label"] = label_on if state else label_off
        passed = pass_when_on if state else pass_when_off
        # Sync state to UI
        try:
            from server import PromptServer
            PromptServer.instance.send_sync("fsd_mutate_state", {
                "node_type": "FSD_ToggleSwitch",
                "widget_name": "state", "value": state,
                "label": label_on if state else label_off
            })
        except: pass
        return (state, passed)


NODE_CLASS_MAPPINGS = {
    # 10. Resolution Parser
    "FSD_ResolutionParser": FSD_ResolutionParser,

    # 12. Switches & Gates
    "FSD_DynamicSwitchANY": FSD_DynamicSwitchANY,
    "FSD_DynamicDiverterANY": FSD_DynamicDiverterANY,
    "FSD_BooleanSwitchANY": FSD_BooleanSwitchANY,
    "FSD_BooleanDiverterANY": FSD_BooleanDiverterANY,
    "FSD_GateANY": FSD_GateANY,

    # 14. Signals & Mutators
    "FSD_AdvancedNodeBypasser": FSD_AdvancedNodeBypasser,

    # 9. Workflow Controls
    "FSD_ToggleSwitch": FSD_ToggleSwitch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    # 10. Resolution Parser
    "FSD_ResolutionParser": "Utility - Resolution Parser",

    # 12. Switches & Gates
    "FSD_DynamicSwitchANY": "Switch - Dynamic",
    "FSD_DynamicDiverterANY": "Switch - Diverter",
    "FSD_BooleanSwitchANY": "Switch - Boolean",
    "FSD_BooleanDiverterANY": "Switch - Bool Divert",
    "FSD_GateANY": "Switch - Gate",

    # 14. Signals & Mutators
    "FSD_AdvancedNodeBypasser": "Signal - Bypasser",

    # 9. Workflow Controls
    "FSD_ToggleSwitch": "Control - Toggle",
}
