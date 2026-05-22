import { app } from "../../scripts/app.js";
import { injectCSS } from "./styles.js";
import { Data } from "./data.js";
import { AC } from "./autocomplete.js";
import { AutoCycle } from "./autocycle.js";

const ANIMA_SIZE_KEY = "_anima_saved_size";

function isAnimaNode(node) {
    const cls = String(node?.comfyClass || node?.type || node?.constructor?.comfyClass || "");
    const title = String(node?.title || "");
    return cls === "AnimaStyleExplorer"
        || cls === "FSD_AnimaMultiArtist"
        || cls === "FSD_AnimaMultiArtist_Simple"
        || title.includes("Anima Style Explorer");
}

function isMultiArtistNode(node) {
    const cls = String(node?.comfyClass || node?.type || node?.constructor?.comfyClass || "");
    return cls === "FSD_AnimaMultiArtist" || cls === "FSD_AnimaMultiArtist_Simple";
}

function ensureWidgetArray(node) {
    if (!node) return [];
    if (!Array.isArray(node.widgets)) node.widgets = [];
    return node.widgets;
}

function ensureNodeProperties(node) {
    if (!node) return {};
    if (!node.properties || typeof node.properties !== "object") node.properties = {};
    return node.properties;
}

function normalizeSizePair(value) {
    if (!Array.isArray(value) || value.length < 2) return null;
    const width = Number(value[0]) || 0;
    const height = Number(value[1]) || 0;
    if (width <= 0 || height <= 0) return null;
    return [width, height];
}

function readStoredNodeSize(node) {
    const props = ensureNodeProperties(node);
    return normalizeSizePair(props[ANIMA_SIZE_KEY]);
}

function writeStoredNodeSize(node, value) {
    const normalized = normalizeSizePair(value);
    if (!normalized) return null;
    const props = ensureNodeProperties(node);
    props[ANIMA_SIZE_KEY] = normalized;
    return normalized;
}

function ensureResizePersistence(node) {
    if (!node || node._animaSizePersistenceAttached) return;
    node._animaSizePersistenceAttached = true;

    const originalSetSize = typeof node.setSize === "function" ? node.setSize.bind(node) : null;
    if (originalSetSize) {
        node.setSize = function (size) {
            const result = originalSetSize(size);
            const next = normalizeSizePair(this.size) || normalizeSizePair(size);
            if (next) writeStoredNodeSize(this, next);
            return result;
        };
    }

    const originalOnConfigure = typeof node.onConfigure === "function" ? node.onConfigure : null;
    node.onConfigure = function () {
        const result = originalOnConfigure?.apply(this, arguments);
        const incoming = arguments[0];
        const configured = normalizeSizePair(incoming?.properties?.[ANIMA_SIZE_KEY])
            || normalizeSizePair(incoming?.size)
            || normalizeSizePair(this.size);
        if (configured) writeStoredNodeSize(this, configured);
        return result;
    };

    const originalOnResize = typeof node.onResize === "function" ? node.onResize : null;
    node.onResize = function () {
        const result = originalOnResize?.apply(this, arguments);
        const resized = normalizeSizePair(arguments[0]) || normalizeSizePair(this.size);
        if (resized) writeStoredNodeSize(this, resized);
        return result;
    };

    if (!readStoredNodeSize(node)) {
        writeStoredNodeSize(node, node.size);
    }
}

function refreshNodeCanvas(node) {
    if (!node) return;
    try {
        node.setDirtyCanvas?.(true, true);
        app.graph?.setDirtyCanvas?.(true, true);
    } catch { }
}

function growNodeIfNeeded(node) {
    if (!node) return;
    try {
        const current = normalizeSizePair(node.size) || [0, 0];
        const stored = readStoredNodeSize(node) || current;
        const computed = Array.isArray(node.computeSize?.()) ? node.computeSize() : null;
        if (!computed || computed.length !== 2) {
            refreshNodeCanvas(node);
            return;
        }

        const next = [
            Math.max(stored[0], Number(computed[0]) || 0),
            Math.max(stored[1], Number(computed[1]) || 0),
        ];

        if (next[0] !== current[0] || next[1] !== current[1]) {
            node.setSize?.(next);
        }
        refreshNodeCanvas(node);
    } catch { }
}

function ensureTagDisplayWidget(node) {
    if (!node || typeof node.addCustomWidget !== "function") return false;
    const widgets = ensureWidgetArray(node);
    const existing = widgets.find((widget) => String(widget?.name || "") === "_tag_display");
    if (existing) return false;

    node.addCustomWidget({
        name: "_tag_display",
        type: "anima_tag",
        value: "",
        draw(ctx, n, width, y) {
            const tag = n._currentTag;
            if (!tag) return;
            ctx.save();
            ctx.fillStyle = "#0f0f18";
            ctx.strokeStyle = "#1e1e30";
            ctx.lineWidth = 1;
            ctx.beginPath();
            if (typeof ctx.roundRect === "function") {
                ctx.roundRect(8, y + 2, width - 16, 20, 4);
            } else {
                ctx.rect(8, y + 2, width - 16, 20);
            }
            ctx.fill();
            ctx.stroke();
            ctx.fillStyle = "#606080";
            ctx.font = "500 10px 'JetBrains Mono',monospace";
            ctx.textAlign = "center";
            ctx.fillText(`@${tag.replace(/_/g, " ")}`, width / 2, y + 15);
            ctx.restore();
        },
        computeSize() { return [0, 26]; },
        serialize: false,
    });
    return true;
}

function ensureBadge() {
    if (document.getElementById("anima-badge")) return;
    const badge = document.createElement("div");
    badge.id = "anima-badge";
    const canvas = document.getElementById("graph-canvas");
    (canvas?.parentElement ?? document.body).appendChild(badge);
}

function attachTextareaAutocomplete(node, delay = 400) {
    setTimeout(() => {
        node.widgets?.forEach((widget) => {
            if (widget?.inputEl?.tagName === "TEXTAREA") {
                AC.attach(widget.inputEl);
            }
        });
    }, delay);
}

async function openStyleBrowser(node) {
    try {
        const mod = await import("./browser.js");
        const browser = mod?.Browser;
        if (!browser) throw new Error("Browser module unavailable");
        browser.open((artist) => AutoCycle.inject(node, artist), node);
        const cycleBtn = browser.cycleBtn?.();
        if (cycleBtn) cycleBtn.onclick = () => AutoCycle.toggle(node);
    } catch (error) {
        console.error("[AnimaStyleExplorer] Failed to load Style Browser", error);
        alert("Could not load Style Browser. Reload ComfyUI and check the browser console.");
    }
}

async function openMultiSelectBrowser(node) {
    try {
        const mod = await import("./anima_multi_select.js");
        const browser = mod?.MultiSelectBrowser;
        if (!browser) throw new Error("MultiSelectBrowser module unavailable");
        browser.open(node);
    } catch (error) {
        console.error("[AnimaMultiArtist] Failed to load Multi-Select Browser", error);
        alert("Could not load Multi-Select Browser. Reload ComfyUI and check the browser console.");
    }
}

export function showSaveStyleModal({ positive, negative, onSaved }) {
    // Remove any existing modal
    const old = document.getElementById("anima-save-style-modal");
    if (old) old.remove();

    const modal = document.createElement("div");
    modal.id = "anima-save-style-modal";
    modal.innerHTML =
        '<div class="anima-save-backdrop"></div>' +
        '<div class="anima-save-window">' +
            '<div class="anima-save-hdr">' +
                '<span>Save as Style</span>' +
                '<button class="anima-save-close">&#10005;</button>' +
            '</div>' +
            '<div class="anima-save-body" id="anima-save-body"></div>' +
        '</div>';

    document.body.appendChild(modal);

    const body = modal.querySelector("#anima-save-body");
    const close = () => modal.remove();

    modal.querySelector(".anima-save-backdrop").addEventListener("click", close);
    modal.querySelector(".anima-save-close").addEventListener("click", close);

    // Step 1: pick or create database
    fetch("/styleselector/get_databases")
        .then(r => r.json())
        .then(data => {
            const databases = Array.isArray(data) ? data : (data.databases || []);
            if (!databases.length) {
                // No databases — create one
                body.innerHTML =
                    '<p class="anima-save-label">No databases found. Create one:</p>' +
                    '<input class="anima-save-input" id="anima-save-db-name" type="text" placeholder="Database name" autofocus/>' +
                    '<div class="anima-save-actions">' +
                        '<button class="anima-save-btn" id="anima-save-create-db">Create</button>' +
                        '<button class="anima-save-btn-cancel">Cancel</button>' +
                    '</div>';

                body.querySelector(".anima-save-btn-cancel").addEventListener("click", close);

                const dbInput = body.querySelector("#anima-save-db-name");
                body.querySelector("#anima-save-create-db").addEventListener("click", async () => {
                    const dbName = dbInput.value.trim();
                    if (!dbName) return;
                    try {
                        const r = await fetch("/styleselector/create_database", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ name: dbName }),
                        });
                        const d = await r.json();
                        if (d.status === "ok") {
                            showStyleNameStep(d.name);
                        } else {
                            alert("Error: " + (d.message || "Unknown"));
                        }
                    } catch (e) {
                        alert("Failed to create database.");
                    }
                });
                dbInput.addEventListener("keydown", (e) => {
                    if (e.key === "Enter") body.querySelector("#anima-save-create-db").click();
                });
                setTimeout(() => dbInput.focus(), 50);
            } else if (databases.length === 1) {
                showStyleNameStep(databases[0]);
            } else {
                // Multiple databases — pick one
                const listItems = databases.map(db =>
                    '<button class="anima-save-db-item" data-db="' + db + '">' + db + '</button>'
                ).join("");

                body.innerHTML =
                    '<p class="anima-save-label">Select database:</p>' +
                    '<div class="anima-save-db-list">' + listItems + '</div>';

                body.querySelectorAll(".anima-save-db-item").forEach(btn => {
                    btn.addEventListener("click", () => showStyleNameStep(btn.dataset.db));
                });
            }
        })
        .catch(() => {
            body.innerHTML = '<p class="anima-save-label">Failed to load databases.</p>';
        });

    function showStyleNameStep(database) {
        body.innerHTML =
            '<p class="anima-save-label">Database: <strong>' + database + '</strong></p>' +
            '<p class="anima-save-label">Style name:</p>' +
            '<input class="anima-save-input" id="anima-save-style-name" type="text" placeholder="Style name" autofocus/>' +
            '<div class="anima-save-actions">' +
                '<button class="anima-save-btn" id="anima-save-do">Save</button>' +
                '<button class="anima-save-btn-cancel">Cancel</button>' +
            '</div>';

        body.querySelector(".anima-save-btn-cancel").addEventListener("click", close);

        const nameInput = body.querySelector("#anima-save-style-name");
        body.querySelector("#anima-save-do").addEventListener("click", async () => {
            const styleName = nameInput.value.trim();
            if (!styleName) return;

            try {
                const r = await fetch("/styleselector/save_style", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        database: database,
                        name: styleName,
                        positive: positive,
                        negative: negative,
                    }),
                });
                const d = await r.json();
                if (d.status === "ok") {
                    onSaved?.();
                    close();
                    showToast("Style \"" + styleName + "\" saved to \"" + database + "\"");
                } else {
                    alert("Error: " + (d.message || "Unknown"));
                }
            } catch (e) {
                alert("Failed to save style.");
            }
        });
        nameInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") body.querySelector("#anima-save-do").click();
        });
        setTimeout(() => nameInput.focus(), 50);
    }
}

function showToast(msg) {
    const toast = document.createElement("div");
    toast.className = "anima-toast anima-toast-success";
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2500);
}

async function saveAsStyle(node) {
    const widgets = node.widgets || [];
    const positive = widgets.find(w => w.name === "positive")?.value || "";
    const negative = widgets.find(w => w.name === "negative")?.value || "";

    showSaveStyleModal({ positive, negative });
}

function ensureButtonWidget(node, name, callback) {
    const widgets = ensureWidgetArray(node);
    let widget = widgets.find((item) => String(item?.name || "") === name && String(item?.type || "") === "button");
    if (widget) {
        widget.callback = callback;
        return false;
    }
    if (typeof node.addWidget !== "function") return false;
    widget = node.addWidget("button", name, null, callback);
    return !!widget;
}

function moveWidgetsToBottom(node, names = []) {
    const widgets = ensureWidgetArray(node);
    if (!widgets.length) return false;

    const wanted = names
        .map((name) => widgets.find((widget) => String(widget?.name || "") === name))
        .filter(Boolean);
    if (!wanted.length) return false;

    const others = widgets.filter((widget) => !wanted.includes(widget));
    const next = [...others, ...wanted];
    const changed = next.some((widget, index) => widget !== widgets[index]);
    if (!changed) return false;

    widgets.length = 0;
    widgets.push(...next);
    return true;
}

function patchNode(node, force = false) {
    if (!node || (!force && !isAnimaNode(node))) return;
    ensureResizePersistence(node);

    if (isMultiArtistNode(node)) {
        // Multi-Artist nodes: "Browse Artists" + "Save as Style" buttons
        const addedBtn = ensureButtonWidget(node, "Browse Artists", () => {
            openMultiSelectBrowser(node);
        });

        const addedSave = ensureButtonWidget(node, "Save as Style", () => {
            saveAsStyle(node);
        });

        if (addedBtn || addedSave) {
            setTimeout(() => growNodeIfNeeded(node), 120);
            setTimeout(() => growNodeIfNeeded(node), 320);
        }
        return;
    }

    // Original AnimaStyleExplorer
    const addedRandom = ensureButtonWidget(node, "Random Style", () => {
        Data.random().then((artist) => {
            if (artist) AutoCycle.inject(node, artist);
        }).catch(() => { });
    });

    const addedBrowser = ensureButtonWidget(node, "Style Browser", () => {
        openStyleBrowser(node);
    });

    const addedTag = ensureTagDisplayWidget(node);
    moveWidgetsToBottom(node, ["_tag_display", "Style Browser", "Random Style"]);
    ensureBadge();

    growNodeIfNeeded(node);

    if (addedRandom || addedBrowser || addedTag) {
        setTimeout(() => growNodeIfNeeded(node), 120);
        setTimeout(() => growNodeIfNeeded(node), 320);
    }
}

function schedulePatch(node, force = false) {
    patchNode(node, force);
    setTimeout(() => patchNode(node, force), 80);
    setTimeout(() => patchNode(node, force), 260);
    setTimeout(() => patchNode(node, force), 900);
}

app.registerExtension({
    name: "AnimaStyleExplorer",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        const isOurNode = nodeData.name === "AnimaStyleExplorer"
            || nodeData.name === "FSD_AnimaMultiArtist"
            || nodeData.name === "FSD_AnimaMultiArtist_Simple";
        if (!isOurNode) return;
        injectCSS();

        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            origOnNodeCreated?.apply(this, arguments);
            schedulePatch(this, true);
            attachTextareaAutocomplete(this, 400);
        };
    },

    nodeCreated(node) {
        schedulePatch(node);
        attachTextareaAutocomplete(node, 500);
    },

    loadedGraphNode(node) {
        schedulePatch(node);
        attachTextareaAutocomplete(node, 160);
    },

    setup() {
        [60, 220, 700, 1400].forEach((delay) => {
            setTimeout(() => {
                const nodes = app.graph?._nodes || [];
                for (const node of nodes) {
                    patchNode(node);
                }
            }, delay);
        });
    },
});
