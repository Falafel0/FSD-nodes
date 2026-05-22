import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// MUTE & BYPASS + WIDGET MUTATOR LOGIC
api.addEventListener("fsd_mutate_state", (event) => {
    const data = event.detail;
    if (!app.graph) return;

    let changed = false;
    let nodes_to_mutate = new Set();

    // Collect target nodes
    if (data.group_name) {
        const group = app.graph._groups.find(g => g.title.trim() === data.group_name.trim());
        if (group) {
            group.recomputeInsideNodes();
            if (group._nodes) {
                for (const n of group._nodes) {
                    nodes_to_mutate.add(n);
                }
            }
        }
    }

    if (data.nodes && Array.isArray(data.nodes)) {
        for (const node_id of data.nodes) {
            const n = app.graph.getNodeById(Number(node_id)) || app.graph.getNodeById(String(node_id));
            if (n) nodes_to_mutate.add(n);
        }
    }

    // Also collect by node_ids (used by FSD_ApplyStateMutator)
    if (data.node_ids && Array.isArray(data.node_ids)) {
        for (const node_id of data.node_ids) {
            const n = app.graph.getNodeById(Number(node_id)) || app.graph.getNodeById(String(node_id));
            if (n) nodes_to_mutate.add(n);
        }
    }

    // If we have a widget mutation action (Set/Toggle/Increment)
    if (data.action && data.widget_name) {
        for (const node of nodes_to_mutate) {
            const widget = node.widgets?.find(w => w.name === data.widget_name);
            if (!widget) continue;

            const oldValue = widget.value;
            let newValue = data.new_value;

            if (data.action === "Toggle") {
                newValue = !oldValue;
            } else if (data.action === "Increment") {
                const step = widget.options?.step || 1;
                newValue = (typeof oldValue === 'number' ? oldValue : 0) + step;
            } else if (data.action === "Decrement") {
                const step = widget.options?.step || 1;
                newValue = (typeof oldValue === 'number' ? oldValue : 0) - step;
            }

            // Clamp to min/max if numeric
            if (typeof newValue === 'number') {
                if (widget.options?.min !== undefined) newValue = Math.max(widget.options.min, newValue);
                if (widget.options?.max !== undefined) newValue = Math.min(widget.options.max, newValue);
            }

            if (widget.value !== newValue || data.action === "Toggle") {
                widget.value = newValue;
                if (widget.callback) {
                    try { widget.callback(newValue); } catch(e) {}
                }
                changed = true;
            }
        }
    }

    // Mode mutation (mute/bypass)
    if (data.mode !== undefined) {
        for (const node of nodes_to_mutate) {
            let new_mode = data.mode;
            if (data.mode === 99) {
                new_mode = (node.mode === 4) ? 0 : 4;
            } else if (data.mode === 98) {
                new_mode = (node.mode === 2) ? 0 : 2;
            }
            if (node.mode !== new_mode) {
                node.mode = new_mode;
                changed = true;
            }
        }
    }

    if (changed) {
        app.graph.setDirtyCanvas(true);
    }
});
