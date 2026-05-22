import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// ── Helpers ─────────────────────────────────────────────────────────

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// ── Node extension ──────────────────────────────────────────────────

app.registerExtension({
    name: "FSD.LoraStack",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "FSD_LoraStack") return;

        // ── Per-instance state ────────────────────────────────────────
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated?.apply(this, arguments);

            if (!this.properties || !this.properties.lora_gallery_id) {
                if (!this.properties) this.properties = {};
                this.properties.lora_gallery_id = "fsd-lora-" + Math.random().toString(36).substring(2, 11);
            }

            // Hidden gallery_id widget (for persistence)
            const gidWidget = this.addWidget("hidden_text", "lora_gallery_id_widget",
                this.properties.lora_gallery_id, () => {}, {});
            gidWidget.serializeValue = () => this.properties.lora_gallery_id;
            gidWidget.draw = () => {};
            gidWidget.computeSize = () => [0, 0];

            const HEADER_HEIGHT = 110;
            this.size = [700, 600];
            this.loraData = [];
            this.availableLoras = [];
            this.isLoading = false;
            this.currentPage = 1;
            this.totalPages = 1;

            const node = this;

            // Hidden selection_data widget
            const selWidget = this.addWidget("hidden_text", "selection_data",
                this.properties.selection_data || "[]", () => {}, { multiline: true });
            selWidget.serializeValue = () => node.properties["selection_data"] || "[]";
            selWidget.draw = () => {};
            selWidget.computeSize = () => [0, 0];

            // DOM container
            const domEl = document.createElement("div");
            domEl.className = "fsd-lora-container-wrapper";
            domEl.dataset.captureWheel = "true";
            domEl.addEventListener("wheel", e => e.stopPropagation());
            this.addDOMWidget("gallery", "div", domEl, {});

            const uid = "fsd-lora-gallery-" + this.id;

            domEl.innerHTML =
                '<style>' +
                    '#' + uid + ' .fsd-lora-container { display:flex; flex-direction:column; height:100%; font-family:sans-serif; overflow:hidden; }' +
                    '#' + uid + ' .fsd-lora-selected-list { flex-shrink:0; padding:5px; max-height:50%; overflow-y:auto; }' +
                    '#' + uid + ' .fsd-lora-controls { display:flex; flex-direction:column; padding:5px; gap:5px; flex-shrink:0; }' +
                    '#' + uid + ' .fsd-lora-controls-row { display:flex; gap:8px; align-items:center; }' +
                    '#' + uid + ' .fsd-lora-gallery { flex:1 1 0; min-height:0; overflow-y:auto; overflow-x:hidden; background-color:#1a1a1a; padding:5px; display:grid; grid-template-columns:repeat(auto-fill, minmax(140px, 1fr)); gap:6px; align-content:start; }' +
                    '#' + uid + ' .fsd-lora-card { cursor:pointer; border:3px solid transparent; border-radius:6px; background-color:var(--comfy-input-bg,#222); transition:border-color 0.2s; display:flex; flex-direction:column; position:relative; }' +
                    '#' + uid + ' .fsd-lora-card.selected { border-color:#00FFC9; }' +
                    '#' + uid + ' .fsd-lora-media { width:100%; height:130px; background-color:#111; border-radius:3px 3px 0 0; overflow:hidden; display:flex; align-items:center; justify-content:center; }' +
                    '#' + uid + ' .fsd-lora-media img, #' + uid + ' .fsd-lora-media video { width:100%; height:100%; object-fit:cover; }' +
                    '#' + uid + ' .fsd-lora-card-info { padding:3px 4px; flex-grow:1; display:flex; flex-direction:column; }' +
                    '#' + uid + ' .fsd-lora-card p { font-size:10px; margin:0; word-break:break-all; text-align:center; color:var(--node-text-color,#ccc); }' +
                    '#' + uid + ' .fsd-lora-card-triggers { font-size:9px; color:#a5a5a5; padding:1px 3px; text-align:center; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-height:12px; }' +
                    '#' + uid + ' .fsd-lora-card-tags { display:flex; flex-wrap:wrap; gap:2px; margin-top:auto; padding-top:3px; }' +
                    '#' + uid + ' .fsd-lora-card-tags .tag { background-color:#006699; color:#fff; padding:0 3px; font-size:9px; border-radius:2px; cursor:pointer; }' +
                    '#' + uid + ' .card-btn { position:absolute; width:20px; height:20px; background-color:rgba(0,0,0,0.5); color:white; border:none; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:12px; cursor:pointer; transition:all 0.2s; opacity:0; z-index:10; }' +
                    '#' + uid + ' .fsd-lora-card:hover .card-btn { opacity:1; }' +
                    '#' + uid + ' .card-btn:hover { background-color:rgba(0,0,0,0.8); }' +
                    '#' + uid + ' .sync-civitai-btn { top:4px; left:4px; }' +
                    '#' + uid + ' .sync-civitai-btn.loading { animation:fsd-spin 1s linear infinite; pointer-events:none; background-color:#4a90e2; }' +
                    '@keyframes fsd-spin { 0%{transform:rotate(0deg)} 100%{transform:rotate(360deg)} }' +
                    '#' + uid + ' .fsd-lora-gallery::-webkit-scrollbar { width:7px; }' +
                    '#' + uid + ' .fsd-lora-gallery::-webkit-scrollbar-track { background:#2a2a2a; border-radius:3px; }' +
                    '#' + uid + ' .fsd-lora-gallery::-webkit-scrollbar-thumb { background-color:#555; border-radius:3px; }' +
                    '#' + uid + ' .fsd-lora-lora-item { display:flex; align-items:center; gap:6px; margin-bottom:3px; padding:2px 4px; background:#22222255; border-radius:4px; }' +
                    '#' + uid + ' .fsd-lora-lora-item .lora-name { flex-grow:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-size:11px; color:var(--node-text-color,#ccc); }' +
                    '#' + uid + ' .fsd-lora-lora-item input[type=number] { width:55px; background-color:#333; border:1px solid #555; border-radius:3px; color:#ccc; font-size:11px; }' +
                    '#' + uid + ' .fsd-lora-lora-item .lora-label { font-size:9px; color:var(--node-text-color,#aaa); }' +
                    '#' + uid + ' .fsd-lora-lora-item .remove-lora-btn { background:#555; color:#fff; border:none; border-radius:10%; cursor:pointer; margin-left:auto; flex-shrink:0; font-size:12px; width:18px; height:18px; display:flex; align-items:center; justify-content:center; }' +
                    '#' + uid + ' .fsd-lora-lora-item .remove-lora-btn:hover { background:#ff4444; }' +
                    '#' + uid + ' .fsd-lora-trigger-expand { background:none; border:none; color:#aaa; cursor:pointer; font-size:10px; padding:0 2px; flex-shrink:0; }' +
                    '#' + uid + ' .fsd-lora-trigger-expand:hover { color:#fff; }' +
                    '#' + uid + ' .fsd-lora-trigger-popup { display:none; background:#1a1a1a; border:1px solid #444; border-radius:4px; padding:4px 6px; margin-top:2px; max-height:150px; overflow-y:auto; }' +
                    '#' + uid + ' .fsd-lora-trigger-popup.open { display:block; }' +
                    '#' + uid + ' .fsd-lora-trigger-item { display:flex; align-items:center; gap:4px; padding:1px 0; font-size:10px; color:#ccc; }' +
                    '#' + uid + ' .fsd-lora-trigger-item input[type=checkbox] { margin:0; }' +
                    '#' + uid + ' .fsd-lora-trigger-item label { cursor:pointer; }' +
                    '#' + uid + ' .fsd-lora-controls-row input[type=text], #' + uid + ' .fsd-lora-controls-row select { background:#222; color:#ccc; border:1px solid #555; padding:3px 6px; border-radius:3px; font-size:11px; }' +
                    '#' + uid + ' .fsd-lora-controls-row button { background:#444; color:#ccc; border:1px solid #555; padding:3px 8px; border-radius:3px; cursor:pointer; font-size:11px; }' +
                    '#' + uid + ' .fsd-lora-controls-row button:hover { background:#555; }' +
                    '#' + uid + ' .fsd-lora-container.gallery-collapsed .fsd-lora-gallery { display:none; }' +
                '</style>' +
                '<div id="' + uid + '" style="height:100%;">' +
                    '<div class="fsd-lora-container">' +
                        '<div class="fsd-lora-selected-list"></div>' +
                        '<div class="fsd-lora-controls">' +
                            '<div class="fsd-lora-controls-row">' +
                                '<button class="toggle-all-btn">Toggle All</button>' +
                                '<input type="text" class="search-input" placeholder="Filter by Name..." style="flex-grow:1;">' +
                                '<button class="save-preset-btn">Save Preset</button>' +
                                '<select class="preset-select" style="max-width:120px;"><option value="">Load Preset</option></select>' +
                                '<button class="clear-all-btn">Clear All</button>' +
                            '</div>' +
                            '<div class="fsd-lora-controls-row">' +
                                '<button class="tag-filter-mode-btn">OR</button>' +
                                '<input type="text" class="tag-filter-input" placeholder="Filter by Tag..." style="flex-grow:1;">' +
                                '<select class="folder-filter-select" style="max-width:120px;"><option value="">All Folders</option></select>' +
                                '<select class="base-model-filter-select" style="max-width:130px;"><option value="">All Models</option></select>' +
                                '<button class="toggle-gallery-btn">Hide Gallery</button>' +
                            '</div>' +
                        '</div>' +
                        '<div class="fsd-lora-gallery"><p>Loading LoRAs...</p></div>' +
                    '</div>' +
                '</div>';

            const container = domEl.querySelector(".fsd-lora-container");
            const selectedListEl = domEl.querySelector(".fsd-lora-selected-list");
            const galleryEl = domEl.querySelector(".fsd-lora-gallery");
            const searchInput = domEl.querySelector(".search-input");
            const tagFilterInput = domEl.querySelector(".tag-filter-input");
            const tagFilterModeBtn = domEl.querySelector(".tag-filter-mode-btn");
            const folderFilterSelect = domEl.querySelector(".folder-filter-select");
            const baseModelFilterSelect = domEl.querySelector(".base-model-filter-select");
            const toggleGalleryBtn = domEl.querySelector(".toggle-gallery-btn");
            const savePresetBtn = domEl.querySelector(".save-preset-btn");
            const presetSelect = domEl.querySelector(".preset-select");
            const toggleAllBtn = domEl.querySelector(".toggle-all-btn");
            const clearAllBtn = domEl.querySelector(".clear-all-btn");

            // ── API helpers ────────────────────────────────────────────

            const getLoras = async (filterTag = "", mode = "OR", folder = "", page = 1, selectedLoras = [], nameFilter = "", baseModel = "") => {
                if (node.isLoading) return;
                node.isLoading = true;
                try {
                    let url = "/fsd_lora/list?filter_tag=" + encodeURIComponent(filterTag) +
                        "&mode=" + mode + "&folder=" + encodeURIComponent(folder) +
                        "&page=" + page + "&name_filter=" + encodeURIComponent(nameFilter) +
                        "&base_model=" + encodeURIComponent(baseModel) +
                        "&per_page=50";
                    selectedLoras.forEach(l => url += "&selected_loras=" + encodeURIComponent(l));
                    const resp = await api.fetchApi(url);
                    const data = await resp.json();
                    node.totalPages = data.total_pages || 1;
                    node.currentPage = data.current_page || 1;
                    return data;
                } catch (e) {
                    console.error("FSD LoraStack: fetch error:", e);
                    return { loras: [], folders: [], total_pages: 1, current_page: 1 };
                } finally {
                    node.isLoading = false;
                }
            };

            const loadPresets = async () => {
                try {
                    const resp = await api.fetchApi("/fsd_lora/presets");
                    return await resp.json();
                } catch (e) { return {}; }
            };

            const savePreset = async (name, data) => {
                await api.fetchApi("/fsd_lora/save_preset", {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, data }),
                });
            };

            const deletePreset = async (name) => {
                await api.fetchApi("/fsd_lora/delete_preset", {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name }),
                });
            };

            const updateMetadata = async (loraName, data) => {
                await api.fetchApi("/fsd_lora/update_metadata", {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ lora_name: loraName, ...data }),
                });
            };

            // ── Selection sync ─────────────────────────────────────────

            const syncSelection = () => {
                const data = node.loraData.map(({ element, ...rest }) => rest);
                const json = JSON.stringify(data);
                node.setProperty("selection_data", json);
                const w = node.widgets.find(w => w.name === "selection_data");
                if (w) w.value = json;
            };

            const renderSelectedList = () => {
                selectedListEl.innerHTML = "";
                node.loraData.forEach((item, i) => {
                    const wrapper = document.createElement("div");

                    const row = document.createElement("div");
                    row.className = "fsd-lora-lora-item";
                    row.draggable = true;
                    row.dataset.index = i;

                    const tog = document.createElement("input");
                    tog.type = "checkbox";
                    tog.checked = item.on;
                    tog.title = "Enable/Disable this LoRA";
                    tog.addEventListener("change", e => { node.loraData[i].on = e.target.checked; syncSelection(); });

                    const nameEl = document.createElement("span");
                    nameEl.className = "lora-name";
                    nameEl.textContent = item.lora;
                    nameEl.title = item.lora;

                    const trigLabel = document.createElement("span");
                    trigLabel.className = "lora-label";
                    trigLabel.textContent = "Trig";
                    trigLabel.title = "Add trigger words to prompt";

                    const trigInput = document.createElement("input");
                    trigInput.type = "checkbox";
                    trigInput.checked = item.use_trigger !== false;
                    trigInput.title = "Toggle trigger words injection into pipe positive";
                    trigInput.addEventListener("change", e => { node.loraData[i].use_trigger = e.target.checked; syncSelection(); });

                    // Expand button for trigger word selection
                    const expandBtn = document.createElement("button");
                    expandBtn.className = "fsd-lora-trigger-expand";
                    expandBtn.textContent = "▶";
                    expandBtn.title = "Select individual trigger words";

                    const strLabel = document.createElement("span");
                    strLabel.className = "lora-label";
                    strLabel.textContent = "M";

                    const strInput = document.createElement("input");
                    strInput.type = "number";
                    strInput.value = item.strength;
                    strInput.min = -2; strInput.max = 2; strInput.step = 0.05;
                    strInput.addEventListener("change", e => { node.loraData[i].strength = parseFloat(e.target.value); syncSelection(); });

                    const clipLabel = document.createElement("span");
                    clipLabel.className = "lora-label";
                    clipLabel.textContent = "C";

                    const clipInput = document.createElement("input");
                    clipInput.type = "number";
                    clipInput.value = item.strength_clip != null ? item.strength_clip : item.strength;
                    clipInput.min = -2; clipInput.max = 2; clipInput.step = 0.05;
                    clipInput.addEventListener("change", e => { node.loraData[i].strength_clip = parseFloat(e.target.value); syncSelection(); });

                    const rmBtn = document.createElement("button");
                    rmBtn.className = "remove-lora-btn";
                    rmBtn.textContent = "✖";
                    rmBtn.title = "Remove";
                    rmBtn.addEventListener("click", () => {
                        node.loraData.splice(i, 1);
                        renderSelectedList();
                        syncSelection();
                        fetchAndRender(false);
                    });

                    row.appendChild(tog);
                    row.appendChild(nameEl);
                    row.appendChild(trigLabel);
                    row.appendChild(trigInput);
                    row.appendChild(expandBtn);
                    row.appendChild(strLabel);
                    row.appendChild(strInput);
                    row.appendChild(clipLabel);
                    row.appendChild(clipInput);
                    row.appendChild(rmBtn);

                    // Drag-and-drop
                    row.addEventListener("dragstart", e => { e.dataTransfer.setData("text/plain", i); row.classList.add("dragging"); });
                    row.addEventListener("dragend", () => row.classList.remove("dragging"));
                    row.addEventListener("dragover", e => e.preventDefault());
                    row.addEventListener("drop", e => {
                        e.preventDefault();
                        const from = parseInt(e.dataTransfer.getData("text/plain"));
                        if (from !== i) {
                            const [moved] = node.loraData.splice(from, 1);
                            node.loraData.splice(i, 0, moved);
                            syncSelection();
                            renderSelectedList();
                        }
                    });

                    wrapper.appendChild(row);

                    // Trigger words popup
                    const popup = document.createElement("div");
                    popup.className = "fsd-lora-trigger-popup";

                    // Get trigger words for this LoRA
                    const loraMeta = node.availableLoras.find(l => l.name === item.lora);
                    const allTriggersRaw = (loraMeta && loraMeta.trigger_words) ? loraMeta.trigger_words : "";
                    const allTriggers = allTriggersRaw ? allTriggersRaw.split(",").map(t => t.trim()).filter(t => t) : [];

                    if (allTriggers.length > 0) {
                        const selectedTriggers = item.selected_triggers || [];
                        // If selected_triggers is empty, all are selected by default (Python backward compat)
                        const isAllSelected = selectedTriggers.length === 0;

                        allTriggers.forEach(trig => {
                            const trigItem = document.createElement("div");
                            trigItem.className = "fsd-lora-trigger-item";

                            const cb = document.createElement("input");
                            cb.type = "checkbox";
                            cb.checked = isAllSelected || selectedTriggers.includes(trig);
                            cb.addEventListener("change", () => {
                                // Build new selected_triggers list
                                let cur = node.loraData[i].selected_triggers || [];
                                if (cur.length === 0) {
                                    // Was "all selected" — start with all triggers, then remove unchecked
                                    cur = [...allTriggers];
                                }
                                if (cb.checked) {
                                    if (!cur.includes(trig)) cur.push(trig);
                                } else {
                                    cur = cur.filter(t => t !== trig);
                                }
                                // If all selected, reset to empty (means "all")
                                if (cur.length === allTriggers.length) {
                                    cur = [];
                                }
                                node.loraData[i].selected_triggers = cur;
                                syncSelection();
                            });

                            const lbl = document.createElement("label");
                            lbl.textContent = trig;
                            lbl.title = trig;

                            trigItem.appendChild(cb);
                            trigItem.appendChild(lbl);
                            popup.appendChild(trigItem);
                        });
                    } else {
                        popup.textContent = "No trigger words";
                        popup.style.padding = "4px 6px";
                        popup.style.color = "#666";
                        popup.style.fontSize = "10px";
                    }

                    // Toggle popup on expand button click
                    expandBtn.addEventListener("click", (e) => {
                        e.stopPropagation();
                        const isOpen = popup.classList.toggle("open");
                        expandBtn.textContent = isOpen ? "▼" : "▶";
                    });

                    wrapper.appendChild(popup);
                    selectedListEl.appendChild(wrapper);
                });
            };

            // ── Gallery rendering ──────────────────────────────────────

            const renderCard = (lora) => {
                const card = document.createElement("div");
                card.className = "fsd-lora-card";
                card.dataset.loraName = lora.name;
                card.dataset.tags = (lora.tags || []).join(",");
                card.dataset.triggerWords = lora.trigger_words || "";
                card.dataset.baseModel = lora.base_model || "";

                // Check if selected
                const isSelected = node.loraData.some(d => d.lora === lora.name);
                if (isSelected) card.classList.add("selected");

                // Preview
                const media = document.createElement("div");
                media.className = "fsd-lora-media";
                if (lora.preview_url) {
                    if (lora.preview_type === "video") {
                        media.innerHTML = '<video muted loop playsinline src="' + lora.preview_url + '"></video>';
                        const vid = media.querySelector("video");
                        card.addEventListener("mouseenter", () => vid.play().catch(() => {}));
                        card.addEventListener("mouseleave", () => { vid.pause(); vid.currentTime = 0; });
                    } else {
                        media.innerHTML = '<img src="' + lora.preview_url + '" loading="lazy">';
                    }
                } else {
                    media.innerHTML = '<span style="color:#555;font-size:20px;">📦</span>';
                }
                card.appendChild(media);

                // Sync CivitAI button
                const syncBtn = document.createElement("button");
                syncBtn.className = "card-btn sync-civitai-btn";
                syncBtn.textContent = "☁️";
                syncBtn.title = "Sync CivitAI metadata";
                syncBtn.addEventListener("click", async (e) => {
                    e.stopPropagation();
                    syncBtn.textContent = "🔄";
                    syncBtn.classList.add("loading");
                    try {
                        const resp = await api.fetchApi("/fsd_lora/sync_civitai", {
                            method: "POST", headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ lora_name: lora.name }),
                        });
                        if (resp.ok) {
                            const result = await resp.json();
                            if (result.status === "ok" && result.metadata) {
                                const m = result.metadata;
                                const loraInData = node.availableLoras.find(ll => ll.name === lora.name);
                                if (loraInData) {
                                    loraInData.preview_url = m.preview_url || "";
                                    loraInData.preview_type = m.preview_type || "none";
                                    loraInData.trigger_words = m.trigger_words || "";
                                    loraInData.download_url = m.download_url || "";
                                    loraInData.tags = m.tags || [];
                                    loraInData.base_model = m.base_model || "";
                                }
                                // Refresh just this card
                                const newCard = renderCard(loraInData || lora);
                                card.replaceWith(newCard);
                            }
                        }
                    } catch (e) {
                        syncBtn.textContent = "❌";
                        setTimeout(() => { syncBtn.textContent = "☁️"; syncBtn.classList.remove("loading"); }, 2000);
                    }
                });
                card.appendChild(syncBtn);

                // Info
                const info = document.createElement("div");
                info.className = "fsd-lora-card-info";
                info.innerHTML =
                    '<p>' + escapeHtml(lora.name.split("/").pop().replace(/\.[^/.]+$/, "")) + '</p>' +
                    '<div class="fsd-lora-card-triggers" title="' + escapeHtml(lora.trigger_words || "") + '">' +
                        escapeHtml(lora.trigger_words || "No triggers") +
                    '</div>' +
                    (lora.base_model ? '<div style="font-size:8px;color:#666;text-align:center;padding:0 2px;" title="Base model">' + escapeHtml(lora.base_model) + '</div>' : '');
                card.appendChild(info);

                // Tags
                if (lora.tags && lora.tags.length) {
                    const tagsEl = document.createElement("div");
                    tagsEl.className = "fsd-lora-card-tags";
                    lora.tags.slice(0, 4).forEach(tag => {
                        const t = document.createElement("span");
                        t.className = "tag";
                        t.textContent = tag;
                        t.addEventListener("click", e => {
                            e.stopPropagation();
                            tagFilterInput.value = tag;
                            fetchAndRender(false);
                        });
                        tagsEl.appendChild(t);
                    });
                    card.appendChild(tagsEl);
                }

                // Click to add/remove
                card.addEventListener("click", () => {
                    const idx = node.loraData.findIndex(d => d.lora === lora.name);
                    if (idx >= 0) {
                        node.loraData.splice(idx, 1);
                    } else {
                        node.loraData.push({
                            lora: lora.name,
                            strength: 1.0,
                            strength_clip: 1.0,
                            on: true,
                            use_trigger: true,
                            selected_triggers: [],
                        });
                    }
                    syncSelection();
                    renderSelectedList();
                    // Toggle visual
                    card.classList.toggle("selected");
                });

                return card;
            };

            const renderGallery = (append = false) => {
                if (!append) galleryEl.innerHTML = "";
                const nameFilter = searchInput.value.toLowerCase();
                const toRender = node.availableLoras.filter(l =>
                    l.name.toLowerCase().includes(nameFilter)
                );
                const existing = new Set(
                    Array.from(galleryEl.querySelectorAll(".fsd-lora-card")).map(c => c.dataset.loraName)
                );
                toRender.forEach(lora => {
                    if (append && existing.has(lora.name)) return;
                    galleryEl.appendChild(renderCard(lora));
                });
            };

            // ── Data fetch ─────────────────────────────────────────────

            const fetchAndRender = async (append = false) => {
                if (!append) node.currentPage = 1;
                const tagFilter = tagFilterInput.value;
                const mode = tagFilterModeBtn.textContent;
                const folder = folderFilterSelect.value;
                const nameFilter = searchInput.value;
                const baseModel = baseModelFilterSelect.value;
                const selectedNames = node.loraData.map(d => d.lora);

                const data = await getLoras(tagFilter, mode, folder,
                    append ? (node.currentPage || 1) : 1, selectedNames, nameFilter, baseModel);

                if (!append) {
                    node.availableLoras = data.loras || [];
                    // Update folder dropdown
                    folderFilterSelect.innerHTML = '<option value="">All Folders</option>';
                    (data.folders || []).forEach(f => {
                        const opt = document.createElement("option");
                        opt.value = f;
                        opt.textContent = f === "." ? "(root)" : f;
                        folderFilterSelect.appendChild(opt);
                    });
                    // Update base model dropdown
                    baseModelFilterSelect.innerHTML = '<option value="">All Models</option>';
                    (data.base_models || []).forEach(bm => {
                        const opt = document.createElement("option");
                        opt.value = bm;
                        opt.textContent = bm || "(unknown)";
                        baseModelFilterSelect.appendChild(opt);
                    });
                    baseModelFilterSelect.value = baseModel;
                } else {
                    const existingNames = new Set(node.availableLoras.map(l => l.name));
                    (data.loras || []).forEach(l => {
                        if (!existingNames.has(l.name)) {
                            node.availableLoras.push(l);
                        }
                    });
                    node.currentPage = data.current_page;
                }

                renderGallery(append);

                // Load presets
                const presets = await loadPresets();
                presetSelect.innerHTML = '<option value="">Load Preset</option>';
                Object.keys(presets || {}).forEach(name => {
                    const opt = document.createElement("option");
                    opt.value = name;
                    opt.textContent = name;
                    presetSelect.appendChild(opt);
                });
            };

            // ── Event handlers ─────────────────────────────────────────

            galleryEl.addEventListener("scroll", () => {
                if (node.isLoading || node.currentPage >= node.totalPages) return;
                const { scrollTop, scrollHeight, clientHeight } = galleryEl;
                if (scrollHeight - scrollTop - clientHeight < 300) {
                    node.currentPage++;
                    fetchAndRender(true);
                }
            });

            searchInput.addEventListener("input", () => { node.currentPage = 1; fetchAndRender(false); });
            tagFilterInput.addEventListener("input", () => { node.currentPage = 1; fetchAndRender(false); });
            folderFilterSelect.addEventListener("change", () => { node.currentPage = 1; fetchAndRender(false); });
            baseModelFilterSelect.addEventListener("change", () => { node.currentPage = 1; fetchAndRender(false); });

            tagFilterModeBtn.addEventListener("click", () => {
                tagFilterModeBtn.textContent = tagFilterModeBtn.textContent === "OR" ? "AND" : "OR";
                fetchAndRender(false);
            });

            toggleGalleryBtn.addEventListener("click", () => {
                const collapsed = container.classList.toggle("gallery-collapsed");
                toggleGalleryBtn.textContent = collapsed ? "Show Gallery" : "Hide Gallery";
                // Resize node if collapsed
                if (collapsed) {
                    setTimeout(() => {
                        const controlsEl = domEl.querySelector(".fsd-lora-controls");
                        const contentH = selectedListEl.scrollHeight + controlsEl.offsetHeight;
                        node.size[1] = contentH + HEADER_HEIGHT;
                        node.setDirtyCanvas(true, true);
                    }, 0);
                } else {
                    node.size[1] = 600;
                    node.setDirtyCanvas(true, true);
                }
            });

            toggleAllBtn.addEventListener("click", () => {
                const allOn = node.loraData.every(d => d.on);
                node.loraData.forEach(d => d.on = !allOn);
                syncSelection();
                renderSelectedList();
            });

            clearAllBtn.addEventListener("click", () => {
                node.loraData = [];
                syncSelection();
                renderSelectedList();
                fetchAndRender(false);
            });

            savePresetBtn.addEventListener("click", async () => {
                const name = prompt("Preset name:");
                if (!name) return;
                await savePreset(name, node.loraData.map(({ element, ...rest }) => rest));
                const presets = await loadPresets();
                presetSelect.innerHTML = '<option value="">Load Preset</option>';
                Object.keys(presets || {}).forEach(n => {
                    const opt = document.createElement("option");
                    opt.value = n; opt.textContent = n;
                    presetSelect.appendChild(opt);
                });
            });

            presetSelect.addEventListener("change", async () => {
                const name = presetSelect.value;
                if (!name) return;
                const presets = await loadPresets();
                const data = presets[name];
                if (data) {
                    if (confirm("Delete preset '" + name + "'?")) {
                        await deletePreset(name);
                        presetSelect.value = "";
                        const p = await loadPresets();
                        presetSelect.innerHTML = '<option value="">Load Preset</option>';
                        Object.keys(p || {}).forEach(n => {
                            const opt = document.createElement("option");
                            opt.value = n; opt.textContent = n;
                            presetSelect.appendChild(opt);
                        });
                    } else {
                        node.loraData = data;
                        syncSelection();
                        renderSelectedList();
                        presetSelect.value = "";
                    }
                }
            });

            presetSelect.addEventListener("mousedown", async (e) => {
                const name = presetSelect.value;
                if (!name) return;
                e.preventDefault();
                const presets = await loadPresets();
                const data = presets[name];
                if (data) {
                    node.loraData = data;
                    syncSelection();
                    renderSelectedList();
                    presetSelect.value = "";
                }
            });

            // Load saved state from properties
            if (this.properties.selection_data) {
                try {
                    node.loraData = JSON.parse(this.properties.selection_data);
                } catch (e) {
                    node.loraData = [];
                }
            }
            renderSelectedList();
            fetchAndRender(false);

            return r;
        };

        // ── onConfigure (deserialization) ──────────────────────────────
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            const r = onConfigure?.apply(this, arguments);
            if (this.properties.selection_data) {
                try {
                    this.loraData = JSON.parse(this.properties.selection_data);
                } catch (e) {
                    this.loraData = [];
                }
            }
            return r;
        };
    },
});