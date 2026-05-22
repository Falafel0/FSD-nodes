export function injectCSS() {
    if (document.getElementById("anima-css")) return;
    const s = document.createElement("style");
    s.id = "anima-css";
    s.textContent = `
/* ===== FSD Unified Theme ===== */
:root {
    --fsd-accent: var(--fg-color, #d0d0e0);
    --fsd-accent-dim: color-mix(in srgb, var(--fsd-accent) 40%, transparent);
    --fsd-radius: 7px;
    --fsd-radius-sm: 5px;
    --fsd-gap: 8px;
}

/* Normalize all FSD node UIs to ComfyUI native look */
.danbooru-controls > button,
.danbooru-controls > div,
.danbooru-settings-button,
.danbooru-refresh-button,
.danbooru-filter-button,
.danbooru-category-button,
.danbooru-ranking-button,
.danbooru-favorites-button {
    border-radius: var(--fsd-radius-sm) !important;
    font-family: var(--comfy-font-family, sans-serif) !important;
    font-size: 11px !important;
}

.danbooru-controls > .danbooru-search-container > .danbooru-search-input,
.danbooru-search-input,
input[class*="danbooru"] {
    border-radius: var(--fsd-radius-sm) !important;
    font-family: var(--comfy-font-family, monospace) !important;
    font-size: 12px !important;
}

.styleselector-root *,
#anima-browser *,
#anima-multi-browser *,
#anima-save-style-modal * {
    font-family: var(--comfy-font-family, sans-serif);
}

.styleselector-image-card,
.styleselector-root button,
.styleselector-root select,
.styleselector-root input {
    border-radius: var(--fsd-radius-sm) !important;
}

.styleselector-root .styleselector-gallery {
    border-radius: var(--fsd-radius) !important;
}

/* ===== KikoTools — normalise to ComfyUI theme ===== */
[class*="kiko-dialog"],
[class*="kikotools-dialog"],
[class*="kikotools-autocomplete"],
[class*="kikotools-settings"],
[class*="kikotools-container"],
.kiko-save-image-preview,
.kiko-gallery-card,
.kiko-timer-container,
.kiko-toggle-viewer-btn,
.kiko-format-indicator {
    font-family: var(--comfy-font-family, sans-serif) !important;
}

[class*="kiko-dialog"],
[class*="kikotools-dialog"] {
    border-radius: var(--fsd-radius) !important;
    background: var(--comfy-menu-bg) !important;
    border: 1px solid var(--input-border-color) !important;
}

.kiko-settings-button,
.kiko-toggle-viewer-btn,
.kikotools-settings-row button,
.kikotools-autocomplete-item {
    border-radius: var(--fsd-radius-sm) !important;
    font-size: 11px !important;
}

.kiko-gallery-card {
    border-radius: var(--fsd-radius-sm) !important;
    background: var(--comfy-input-bg);
    border: 1px solid var(--border-color);
}

/* ===== Global components — normalise ===== */
.mce-toast-container .mce-toast {
    font-family: var(--comfy-font-family, sans-serif) !important;
    border-radius: var(--fsd-radius-sm) !important;
    background: var(--comfy-menu-bg) !important;
    border: 1px solid var(--input-border-color) !important;
    color: var(--comfy-input-text) !important;
}

.mce-toast-close, .status-close {
    border-radius: var(--fsd-radius-sm) !important;
}

.gem-execution-status-bar {
    font-family: var(--comfy-font-family, sans-serif) !important;
    border-radius: var(--fsd-radius-sm) !important;
}

/* ===== Global autocomplete — normalise ===== */
.autocomplete-suggestion-item {
    font-family: var(--comfy-font-family, sans-serif) !important;
    border-radius: var(--fsd-radius-sm) !important;
}

/* ===== Style Selector modal — normalise ===== */
.styleselector-modal-overlay {
    border-radius: var(--fsd-radius) !important;
}

/* ===== Anima Style Explorer — Native ComfyUI theme ===== */

#anima-browser { position:fixed; inset:0; z-index:99998; display:flex; align-items:center; justify-content:center; font-family:var(--comfy-font-family, sans-serif); }
#anima-browser.hidden { display:none; }
#anima-browser .backdrop { position:absolute; inset:0; background:rgba(0,0,0,.8); backdrop-filter:blur(10px); }
#anima-browser .window { position:relative; z-index:1; width:min(96vw,1160px); height:min(93vh,880px); background:var(--comfy-menu-bg); border:1px solid var(--border-color); border-radius:14px; display:flex; flex-direction:column; overflow:hidden; box-shadow:0 40px 100px #000c; animation:anima-in .2s cubic-bezier(.22,1,.36,1); }
@keyframes anima-in { from{opacity:0;transform:translateY(16px) scale(.97)} to{opacity:1;transform:none} }

#anima-browser .hdr { display:flex; align-items:center; gap:8px; padding:11px 14px; border-bottom:1px solid var(--border-color); flex-shrink:0; }
#anima-browser .hdr-title { font-size:13px; font-weight:600; color:var(--fg-color); letter-spacing:.02em; white-space:nowrap; }
#anima-browser .hdr-pill { background:var(--comfy-input-bg); border:1px solid var(--input-border-color); color:var(--fg-color); font-size:9.5px; font-family:monospace; padding:2px 7px; border-radius:20px; opacity:0.7; }
#anima-browser .hdr-gap { flex:1; }
#anima-browser .search-wrap { position:relative; flex:1; max-width:300px; }
#anima-browser .search-icon { position:absolute; left:9px; top:50%; transform:translateY(-50%); color:var(--input-border-color); font-size:11px; pointer-events:none; font-style:normal; font-family:monospace; }
#anima-browser .search-input { width:100%; padding:7px 10px 7px 27px; background:var(--comfy-input-bg); border:1px solid var(--input-border-color); border-radius:7px; color:var(--comfy-input-text); font-family:monospace; font-size:12px; outline:none; transition:border-color .15s; box-sizing:border-box; }
#anima-browser .search-input::placeholder { opacity:0.35; }
#anima-browser .search-input:focus { border-color:var(--fg-color); opacity:0.6; }
#anima-browser .hdr-select { padding:6px 8px; background:var(--comfy-input-bg); border:1px solid var(--input-border-color); border-radius:7px; color:var(--comfy-input-text); font-size:11px; cursor:pointer; outline:none; }
#anima-browser .hdr-btn { width:29px; height:29px; display:flex; align-items:center; justify-content:center; background:var(--comfy-input-bg); border:1px solid var(--input-border-color); border-radius:7px; color:var(--fg-color); cursor:pointer; font-size:13px; transition:all .12s; flex-shrink:0; opacity:0.6; }
#anima-browser .hdr-btn:hover { background:var(--comfy-menu-bg); opacity:1; }
#anima-browser .hdr-close { width:29px; height:29px; display:flex; align-items:center; justify-content:center; background:transparent; border:1px solid var(--border-color); border-radius:7px; color:var(--fg-color); cursor:pointer; font-size:13px; transition:all .12s; flex-shrink:0; opacity:0.5; }
#anima-browser .hdr-close:hover { background:rgba(255,80,80,0.1); border-color:rgba(255,100,100,0.4); color:#f88888; opacity:1; }
#anima-browser .hdr-btn-txt { background:var(--comfy-input-bg); border:1px solid var(--input-border-color); color:var(--fg-color); font-family:var(--comfy-font-family,sans-serif); font-size:10px; font-weight:600; padding:6px 12px; border-radius:6px; cursor:pointer; transition:all .15s; margin-right:4px; }
#anima-browser .hdr-btn-txt:hover { background:var(--comfy-menu-bg); color:var(--fg-color); opacity:1; }
#anima-browser .hdr-btn-txt.disabled { opacity:0.5; pointer-events:none; }

#anima-browser .cycle-bar { display:flex; align-items:center; gap:8px; padding:7px 14px; border-bottom:1px solid var(--border-color); background:var(--comfy-menu-bg); flex-shrink:0; }
#anima-browser .cycle-label { font-size:10.5px; color:var(--fg-color); font-family:monospace; white-space:nowrap; }
.anima-play-btn { display:flex; align-items:center; gap:5px; padding:5px 14px; border-radius:6px; cursor:pointer; font-family:var(--comfy-font-family,sans-serif); font-size:11px; font-weight:600; border:1px solid var(--input-border-color); background:var(--comfy-input-bg); color:var(--fg-color); transition:all .15s; white-space:nowrap; }
.anima-play-btn:hover { background:var(--comfy-menu-bg); opacity:1; }
.anima-play-btn.running { background:rgba(255,80,80,0.12); border-color:rgba(255,100,100,0.35); color:#f88888; }
.anima-swipe-btn { display:flex; align-items:center; gap:6px; padding:5px 12px; border-radius:6px; cursor:pointer; font-family:var(--comfy-font-family,sans-serif); font-size:11px; font-weight:600; border:1px solid var(--input-border-color); background:var(--comfy-input-bg); color:var(--fg-color); transition:all .15s; white-space:nowrap; }
.anima-swipe-btn:hover { background:var(--comfy-menu-bg); opacity:1; }
.anima-cycle-status { font-size:10.5px; color:var(--fg-color); font-family:monospace; opacity:0.7; }
.anima-cycle-status.active { opacity:1; }
#anima-browser .cycle-gap { flex:1; }
#anima-browser .cycle-search { position:relative; width:220px; margin-left:12px; }
#anima-browser .cycle-search i { position:absolute; left:8px; top:50%; transform:translateY(-50%); color:var(--input-border-color); font-size:10px; font-family:monospace; font-style:normal; pointer-events:none; }
#anima-browser .cycle-search input { width:100%; padding:5px 8px 5px 22px; background:var(--comfy-input-bg); border:1px solid var(--input-border-color); border-radius:6px; color:var(--comfy-input-text); font-size:11px; font-family:monospace; outline:none; transition:border-color .15s; }
#anima-browser .cycle-search input:focus { border-color:var(--fg-color); opacity:0.6; }
#anima-browser .cycle-hint { font-size:10px; color:var(--fg-color); font-family:var(--comfy-font-family,sans-serif); opacity:0.7; font-style:italic; }

#anima-browser .body { flex:1; overflow-y:auto; padding:12px; scrollbar-width:thin; scrollbar-color:var(--border-color) transparent; }
#anima-browser .body::-webkit-scrollbar { width:5px; }
#anima-browser .body::-webkit-scrollbar-thumb { background:var(--border-color); border-radius:3px; }

.anima-grid { }
.anima-chunk { display:grid; grid-template-columns:repeat(auto-fill,minmax(142px,1fr)); gap:7px; width:100%; contain:content; }
.anima-empty { grid-column:1/-1; display:flex; flex-direction:column; align-items:center; gap:10px; padding:60px; color:var(--fg-color); opacity:0.3; font-size:12px; }
.anima-net-gate { color:var(--fg-color); text-align:center; opacity:0.8; }
.anima-net-gate strong { font-family:monospace; font-size:18px; letter-spacing:.08em; color:var(--fg-color); }
.anima-net-gate span { max-width:420px; line-height:1.5; color:var(--fg-color); opacity:0.7; }

.hdr-toggle-wrap { display:inline-flex; align-items:center; gap:10px; margin-right:6px; background:var(--comfy-input-bg); padding:5px 10px 5px 12px; border-radius:10px; border:1px solid var(--input-border-color); }
.hdr-toggle-label { font-size:10.5px; font-weight:600; color:var(--fg-color); letter-spacing:.01em; background:transparent; padding:0; border:none; margin-right:0; white-space:nowrap; }
.hdr-toggle-hint { display:none; }
.hdr-switch { position:relative; display:inline-block; width:34px; height:20px; transition:transform 0.18s cubic-bezier(0.175, 0.885, 0.32, 1.275); flex-shrink:0; }
.hdr-switch input { opacity:0; width:0; height:0; }
.hdr-slider { position:absolute; cursor:pointer; inset:0; background-color:var(--comfy-input-bg); transition:.2s; border-radius:999px; border:1px solid var(--input-border-color); }
.hdr-slider:before { position:absolute; content:''; height:12px; width:12px; left:3px; bottom:3px; background-color:var(--fg-color); opacity:0.6; transition:.2s; border-radius:50%; }
.hdr-switch:hover { transform:scale(1.08); }
input:checked + .hdr-slider { background-color:var(--comfy-menu-bg); border-color:var(--fg-color); opacity:0.5; }
input:checked + .hdr-slider:before { transform:translateX(14px); opacity:1; }

.hdr-data-btns { display:flex; align-items:center; gap:8px; margin-left:10px; border-left:1px solid var(--border-color); padding-left:10px; }
.hdr-settings-wrap { position:relative; display:flex; align-items:center; }
.hdr-settings-wrap #anima-settings-gear { font-size:15px; color:var(--fg-color); opacity:0.6; }
.hdr-settings-wrap:hover #anima-settings-gear,
.hdr-settings-wrap:focus-within #anima-settings-gear { opacity:1; }
.hdr-settings-menu {
    position:absolute;
    top:calc(100% + 6px);
    right:0;
    min-width:170px;
    padding:6px;
    border-radius:8px;
    border:1px solid var(--border-color);
    background:var(--comfy-menu-bg);
    box-shadow:0 14px 28px rgba(0,0,0,.45);
    display:flex;
    flex-direction:column;
    gap:6px;
    opacity:0;
    transform:translateY(-6px) scale(.98);
    pointer-events:none;
    transition:opacity .14s ease, transform .14s ease;
    z-index:40;
}
.hdr-settings-wrap:hover .hdr-settings-menu,
.hdr-settings-wrap:focus-within .hdr-settings-menu {
    opacity:1;
    transform:translateY(0) scale(1);
    pointer-events:auto;
}
.hdr-settings-item { width:100%; margin-right:0; text-align:left; }
.hdr-settings-option {
    display:flex;
    align-items:center;
    gap:8px;
    padding:6px 8px;
    border:1px solid var(--input-border-color);
    border-radius:6px;
    color:var(--fg-color);
    font-size:10px;
    font-family:var(--comfy-font-family,sans-serif);
    cursor:pointer;
    background:var(--comfy-input-bg);
}
.hdr-settings-option:hover { background:var(--comfy-menu-bg); }
.hdr-settings-option input { width:13px; height:13px; accent-color:var(--fg-color); }

.anima-spinner { width:24px; height:24px; border:2px solid var(--border-color); border-top-color:var(--fg-color); opacity:0.6; border-radius:50%; animation:anima-spin .6s linear infinite; }
@keyframes anima-spin { to { transform:rotate(360deg); } }

.anima-card { border-radius:8px; overflow:hidden; background:var(--comfy-input-bg); border:1px solid var(--border-color); cursor:pointer; transition:transform .15s,border-color .15s,box-shadow .15s; }
.anima-card:hover { transform:translateY(-2px); border-color:var(--fg-color); opacity:0.5; box-shadow:0 6px 20px #0009; }
.anima-card.selected { border-color:var(--fg-color); box-shadow:0 0 0 2px var(--fg-color); opacity:0.15; }
.anima-card-img { position:relative; aspect-ratio:1; overflow:hidden; background:var(--comfy-menu-bg); }
.anima-card-img img { width:100%; height:100%; object-fit:cover; display:block; transition:transform .25s; }
.anima-card:hover .anima-card-img img { transform:scale(1.06); }
.anima-card-img.no-img { display:flex; align-items:center; justify-content:center; }
.anima-card-img.no-img::after { content:attr(data-init); font-family:monospace; font-size:26px; font-weight:700; color:var(--border-color); text-transform:uppercase; }
.anima-card-overlay { position:absolute; inset:0; background:rgba(0,0,0,.65); display:flex; align-items:center; justify-content:center; opacity:0; transition:opacity .18s; }
.anima-uniqueness-rank { position:absolute; top:8px; left:8px; min-width:44px; height:28px; padding:0 10px; border-radius:999px; background:rgba(0,0,0,.55); border:1px solid var(--border-color); color:var(--fg-color); font-family:monospace; font-size:10px; font-weight:700; display:flex; align-items:center; justify-content:center; box-shadow:0 10px 30px #0009; z-index:2; }
.anima-card:hover .anima-card-overlay { opacity:1; }
.anima-card-pick { background:var(--comfy-input-bg); border:1px solid var(--input-border-color); color:var(--fg-color); font-family:var(--comfy-font-family,sans-serif); font-weight:500; font-size:11px; padding:6px 13px; border-radius:6px; cursor:pointer; transition:all .12s; }
.anima-card-pick:hover { background:var(--comfy-menu-bg); opacity:1; }
.anima-card-fav { background:var(--comfy-input-bg); border:1px solid var(--input-border-color); color:var(--fg-color); font-family:var(--comfy-font-family,sans-serif); font-weight:500; font-size:10px; padding:6px 10px; border-radius:6px; cursor:pointer; transition:all .12s; margin-left:8px; }
.anima-card-fav:hover { background:var(--comfy-menu-bg); opacity:1; }
.anima-multi-card .anima-card-fav { display:inline-block; width:auto; height:auto; padding:1px 5px; margin:0; margin-left:6px; border:1px solid var(--input-border-color); border-radius:4px; background:var(--comfy-input-bg); color:var(--fg-color); font-size:10px; line-height:1.5; cursor:pointer; vertical-align:middle; }
.anima-multi-card .anima-card-fav:hover { background:var(--comfy-menu-bg); }
.anima-multi-card .anima-card-fav.fav-active { color:#fbbf24; border-color:#fbbf24; }
.anima-card-meta { padding:6px 8px 8px; }
.anima-card-tag { display:block; font-size:10px; font-weight:500; font-family:monospace; color:var(--fg-color); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.anima-card-works { display:block; font-size:9px; color:var(--fg-color); font-family:monospace; margin-top:2px; opacity:0.5; }

#anima-browser .ftr { display:flex; align-items:center; gap:10px; padding:8px 14px; border-top:1px solid var(--border-color); flex-shrink:0; }
#anima-browser .ftr-count { font-size:10px; font-family:monospace; color:var(--fg-color); opacity:0.6; }
#anima-browser .ftr-gap { flex:1; }
#anima-browser .ftr-link { font-size:10px; font-family:monospace; color:var(--fg-color); text-decoration:none; transition:color .12s; opacity:0.6; }
#anima-browser .ftr-link:hover { opacity:1; }

#anima-ac { position:fixed; z-index:99999; background:var(--comfy-menu-bg); border:1px solid var(--border-color); border-radius:8px; overflow:hidden; max-height:260px; overflow-y:auto; box-shadow:0 12px 36px #000a; font-family:var(--comfy-font-family,sans-serif); min-width:240px; scrollbar-width:thin; }
#anima-ac.hidden { display:none; }
.anima-ac-row { display:flex; align-items:center; gap:8px; padding:6px 10px; cursor:pointer; border-bottom:1px solid var(--border-color); transition:background .1s; }
.anima-ac-row:last-child { border-bottom:none; }
.anima-ac-row:hover,.anima-ac-row.on { background:var(--comfy-input-bg); }
.anima-ac-thumb { width:30px; height:30px; border-radius:4px; object-fit:cover; background:var(--comfy-input-bg); flex-shrink:0; }
.anima-ac-tag { flex:1; font-size:11.5px; font-family:monospace; color:var(--fg-color); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.anima-ac-works { font-size:9.5px; font-family:monospace; color:var(--fg-color); opacity:0.3; white-space:nowrap; }

#anima-badge { position:absolute; background:var(--comfy-menu-bg); border:1px solid var(--border-color); color:var(--fg-color); font-family:monospace; font-size:10px; font-weight:500; padding:3px 10px; border-radius:5px; pointer-events:none; white-space:nowrap; z-index:10001; display:none; opacity:0.7; }

#anima-swipe { position:fixed; inset:0; z-index:100000; display:flex; align-items:center; justify-content:center; font-family:var(--comfy-font-family,sans-serif); }
#anima-swipe.hidden { display:none; }
#anima-swipe .backdrop { position:absolute; inset:0; background:rgba(0,0,0,.82); backdrop-filter:blur(12px); }
#anima-swipe .swipe-header { position:absolute; top:18px; left:0; width:100%; display:flex; align-items:center; justify-content:space-between; padding:0 20px; color:var(--fg-color); z-index:2; }
#anima-swipe .swipe-title { position:absolute; left:50%; transform:translateX(-50%); text-align:center; font-size:24px; font-weight:700; text-shadow:0 2px 8px rgba(0,0,0,.5); }
#anima-swipe .swipe-counter { font-size:12px; font-family:monospace; background:rgba(0,0,0,.4); padding:6px 12px; border-radius:999px; border:1px solid var(--border-color); color:var(--fg-color); user-select:none; }
#anima-swipe .swipe-close { width:38px; height:38px; border-radius:10px; background:rgba(0,0,0,.25); border:1px solid var(--border-color); color:var(--fg-color); cursor:pointer; font-size:16px; line-height:1; display:flex; align-items:center; justify-content:center; transition:background .15s,color .15s,transform .15s; }
#anima-swipe .swipe-close:hover { background:rgba(0,0,0,.45); opacity:1; transform:scale(1.05); }
#anima-swipe .swipe-container { position:relative; width:100%; height:100%; display:flex; align-items:center; justify-content:center; z-index:1; overflow:hidden; }
#anima-swipe .swipe-container.swipe-transition .swipe-image { transition:transform .3s ease, opacity .3s ease, filter .3s ease; }
#anima-swipe .swipe-image { max-height:85vh; max-width:85vw; object-fit:contain; border-radius:14px; box-shadow:0 10px 40px rgba(0,0,0,.35); }
#anima-swipe .swipe-image--current { transform:scale(1); opacity:1; z-index:3; cursor:pointer; }
#anima-swipe .swipe-image--prev, #anima-swipe .swipe-image--next { position:absolute; opacity:.5; filter:blur(8px); z-index:2; cursor:pointer; }
#anima-swipe .swipe-image--prev { transform:scale(.8) translateX(-50vw); }
#anima-swipe .swipe-image--next { transform:scale(.8) translateX(50vw); }
#anima-swipe .swipe-hint { position:absolute; bottom:18px; z-index:2; font-size:12px; color:var(--fg-color); opacity:0.7; background:rgba(0,0,0,.35); padding:6px 12px; border-radius:999px; border:1px solid var(--border-color); font-family:monospace; user-select:none; }

.anima-fullet-auth { font-size:10px; font-family:monospace; color:var(--fg-color); margin-right:6px; opacity:0.7; }
.anima-fullet-auth.connected { opacity:1; }
#anima-fullet-upload.disabled { opacity:0.5; pointer-events:none; }

.anima-fullet-card { border-radius:10px; overflow:hidden; background:var(--comfy-input-bg); border:1px solid var(--border-color); display:flex; flex-direction:column; min-height:280px; transition:transform .15s,border-color .15s,box-shadow .15s; }
.anima-fullet-card:hover { border-color:var(--fg-color); opacity:0.5; box-shadow:0 8px 24px #0009; transform:translateY(-2px); }
.anima-fullet-card { min-height:unset; }
.anima-fullet-img { aspect-ratio:1.2; background:var(--comfy-menu-bg); position:relative; overflow:hidden; }
.anima-fullet-img img { width:100%; height:100%; object-fit:cover; display:block; }
.anima-fullet-img.no-img { display:flex; align-items:center; justify-content:center; }
.anima-fullet-img.no-img::after { content:attr(data-init); font-family:monospace; font-size:24px; color:var(--border-color); }
.anima-fullet-meta { display:flex; flex-direction:column; gap:5px; padding:10px 10px 11px; }
.anima-fullet-artist { font-family:monospace; font-size:11px; color:var(--fg-color); }
.anima-fullet-user { font-family:monospace; font-size:10px; color:var(--fg-color); opacity:0.5; }
.anima-fullet-prompt { display:none !important; }
.anima-fullet-actions { display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
.anima-fullet-actions:first-of-type { margin-top:auto; }
.anima-fullet-actions + .anima-fullet-actions { margin-top:6px; }
.anima-fullet-actions-main { margin-top:6px; }
.anima-fullet-actions-main .anima-card-pick { width:100%; }
.anima-fullet-actions-secondary { margin-top:2px; }
.anima-fullet-mini,
.anima-fullet-mini-link {
    display:inline-flex;
    align-items:center;
    justify-content:center;
    min-height:26px;
    padding:4px 8px;
    border-radius:6px;
    text-decoration:none;
}
.anima-fullet-mini { background:var(--comfy-input-bg); border:1px solid var(--input-border-color); color:var(--fg-color); font-family:monospace; font-size:10px; cursor:pointer; transition:all .12s; }
.anima-fullet-mini:hover { background:var(--comfy-menu-bg); opacity:1; }
.anima-fullet-mini-link { color:var(--fg-color); border:1px solid var(--input-border-color); background:var(--comfy-input-bg); font-family:monospace; font-size:10px; }
.anima-fullet-mini-link:hover { background:var(--comfy-menu-bg); opacity:1; }

#anima-toast-host {
    position:fixed;
    right:18px;
    bottom:18px;
    z-index:100120;
    display:flex;
    flex-direction:column;
    gap:8px;
    pointer-events:none;
}
.anima-toast {
    min-width:200px;
    max-width:340px;
    padding:8px 11px;
    border-radius:8px;
    border:1px solid var(--border-color);
    background:var(--comfy-menu-bg);
    color:var(--fg-color);
    font-size:11px;
    font-family:var(--comfy-font-family,sans-serif);
    box-shadow:0 10px 24px rgba(0,0,0,.45);
    opacity:0;
    transform:translateY(8px);
    transition:opacity .16s ease, transform .16s ease;
}
.anima-toast.show { opacity:1; transform:translateY(0); }
.anima-toast-success { border-color:rgba(100,200,130,0.4); background:var(--comfy-menu-bg); color:var(--fg-color); }
.anima-toast-error { border-color:rgba(240,100,110,0.4); background:var(--comfy-menu-bg); color:var(--fg-color); }
.anima-inline-toast {
    position:absolute;
    left:50%;
    top:50%;
    transform:translate(-50%, -46%) scale(.92);
    min-width:128px;
    max-width:calc(100% - 18px);
    padding:10px 14px;
    border-radius:999px;
    border:1px solid var(--border-color);
    background:var(--comfy-menu-bg);
    color:var(--fg-color);
    font-size:11px;
    font-family:var(--comfy-font-family,sans-serif);
    font-weight:600;
    letter-spacing:.01em;
    box-shadow:0 16px 34px rgba(0,0,0,.42);
    backdrop-filter:blur(8px);
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    opacity:0;
    transition:opacity .16s ease, transform .16s ease;
    pointer-events:none;
    z-index:5;
}
.anima-inline-toast.show { opacity:1; transform:translate(-50%, -50%) scale(1); }
.anima-inline-toast-success { border-color:rgba(100,200,130,0.4); }
.anima-inline-toast-error { border-color:rgba(240,100,110,0.4); }
.anima-upload-modal {
    position:absolute;
    inset:0;
    z-index:30;
    display:flex;
    align-items:center;
    justify-content:center;
    padding:18px;
    background:rgba(5, 8, 14, 0.78);
    backdrop-filter:blur(8px);
}
.anima-upload-modal.hidden { display:none; }
.anima-upload-panel {
    width:min(940px, 100%);
    max-height:100%;
    display:flex;
    flex-direction:column;
    border-radius:14px;
    border:1px solid var(--border-color);
    background:var(--comfy-menu-bg);
    box-shadow:0 28px 70px rgba(0,0,0,.42);
    overflow:hidden;
}
.anima-upload-header {
    display:flex;
    align-items:flex-start;
    justify-content:space-between;
    gap:14px;
    padding:16px 18px 14px;
    border-bottom:1px solid var(--border-color);
}
.anima-upload-copy { display:flex; flex-direction:column; gap:5px; }
.anima-upload-copy strong {
    font-size:14px;
    color:var(--fg-color);
    letter-spacing:.01em;
}
.anima-upload-copy span {
    max-width:560px;
    font-size:11px;
    line-height:1.5;
    color:var(--fg-color);
    opacity:0.7;
}
.anima-upload-tools { display:flex; align-items:center; gap:8px; }
.anima-upload-options {
    display:grid;
    grid-template-columns:repeat(2, minmax(0, 1fr));
    gap:10px;
    padding:0 18px 14px;
    border-bottom:1px solid var(--border-color);
}
.anima-upload-option {
    display:grid;
    grid-template-columns:auto 1fr;
    grid-template-rows:auto auto;
    column-gap:10px;
    row-gap:2px;
    align-items:center;
    padding:10px 12px;
    border:1px solid var(--input-border-color);
    border-radius:10px;
    background:var(--comfy-input-bg);
    cursor:pointer;
}
.anima-upload-option:hover {
    border-color:var(--fg-color);
    opacity:0.6;
    background:var(--comfy-menu-bg);
}
.anima-upload-option input {
    grid-row:1 / span 2;
    width:14px;
    height:14px;
    accent-color:var(--fg-color);
}
.anima-upload-option-title {
    font-size:11px;
    font-weight:600;
    color:var(--fg-color);
}
.anima-upload-option small {
    color:var(--fg-color);
    opacity:0.6;
    font-size:10px;
    line-height:1.4;
}
.anima-upload-body {
    padding:16px 18px 18px;
    overflow:auto;
    min-height:260px;
    max-height:min(72vh, 720px);
}
.anima-upload-grid {
    display:grid;
    grid-template-columns:repeat(auto-fill, minmax(190px, 1fr));
    gap:12px;
}
.anima-upload-empty {
    min-height:260px;
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
    gap:10px;
    text-align:center;
    color:var(--fg-color);
    opacity:0.6;
}
.anima-upload-empty strong {
    font-size:13px;
    color:var(--fg-color);
    opacity:1;
}
.anima-upload-empty span {
    max-width:460px;
    font-size:11px;
    line-height:1.5;
}
.anima-upload-empty-loading strong,
.anima-upload-empty-loading span { opacity:0.8; }
.anima-upload-card {
    display:flex;
    flex-direction:column;
    background:var(--comfy-input-bg);
    border:1px solid var(--border-color);
    border-radius:12px;
    overflow:hidden;
    box-shadow:0 10px 28px rgba(0,0,0,.24);
    transition:transform .14s ease, border-color .14s ease, box-shadow .14s ease;
}
.anima-upload-card:hover {
    transform:translateY(-2px);
    border-color:var(--fg-color);
    opacity:0.6;
    box-shadow:0 16px 34px rgba(0,0,0,.32);
}
.anima-upload-thumb {
    position:relative;
    aspect-ratio:1.08;
    background:var(--comfy-menu-bg);
    overflow:hidden;
}
.anima-upload-thumb img {
    width:100%;
    height:100%;
    object-fit:cover;
    display:block;
}
.anima-upload-thumb.no-img {
    display:flex;
    align-items:center;
    justify-content:center;
}
.anima-upload-thumb.no-img::after {
    content:attr(data-init);
    font-family:monospace;
    font-size:28px;
    color:var(--border-color);
}
.anima-upload-badge {
    position:absolute;
    left:10px;
    top:10px;
    max-width:calc(100% - 20px);
    padding:5px 8px;
    border-radius:999px;
    background:rgba(0,0,0,0.7);
    border:1px solid var(--border-color);
    color:var(--fg-color);
    font-size:10px;
    font-family:monospace;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    backdrop-filter:blur(8px);
}
.anima-upload-meta {
    display:flex;
    flex-direction:column;
    gap:8px;
    padding:11px;
}
.anima-upload-row {
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:10px;
}
.anima-upload-artist {
    font-family:monospace;
    font-size:10px;
    color:var(--fg-color);
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
}
.anima-upload-time {
    font-family:monospace;
    font-size:9px;
    color:var(--fg-color);
    opacity:0.5;
    white-space:nowrap;
}
.anima-upload-prompt {
    min-height:46px;
    margin:0;
    color:var(--fg-color);
    opacity:0.7;
    font-size:10px;
    line-height:1.45;
    display:-webkit-box;
    -webkit-line-clamp:3;
    -webkit-box-orient:vertical;
    overflow:hidden;
}
.anima-upload-action {
    width:100%;
    min-height:30px;
    border-radius:8px;
    border:1px solid var(--input-border-color);
    background:var(--comfy-input-bg);
    color:var(--fg-color);
    font-size:10.5px;
    font-weight:600;
    cursor:pointer;
    transition:all .14s ease;
}
.anima-upload-action:hover {
    background:var(--comfy-menu-bg);
    opacity:1;
}
.anima-upload-action:disabled {
    opacity:.65;
    cursor:wait;
}
`;

s.textContent += `
.anima-key-modal {
    position:absolute;
    inset:0;
    z-index:31;
    display:flex;
    align-items:center;
    justify-content:center;
    padding:18px;
    background:rgba(5, 8, 14, 0.78);
    backdrop-filter:blur(8px);
}
.anima-key-modal.hidden { display:none; }
.anima-key-panel {
    width:min(640px, 100%);
    border-radius:14px;
    border:1px solid var(--border-color);
    background:var(--comfy-menu-bg);
    box-shadow:0 28px 70px rgba(0,0,0,.42);
    overflow:hidden;
}
.anima-key-header {
    display:flex;
    align-items:flex-start;
    justify-content:space-between;
    gap:14px;
    padding:16px 18px 14px;
    border-bottom:1px solid var(--border-color);
}
.anima-key-copy { display:flex; flex-direction:column; gap:5px; }
.anima-key-copy strong {
    font-size:14px;
    color:var(--fg-color);
    letter-spacing:.01em;
}
.anima-key-copy span {
    font-size:11px;
    line-height:1.55;
    color:var(--fg-color);
    opacity:0.7;
    max-width:520px;
}
.anima-key-body {
    padding:16px 18px 8px;
    display:flex;
    flex-direction:column;
    gap:12px;
}
.anima-key-link {
    display:inline-flex;
    align-self:flex-start;
    min-height:28px;
    padding:6px 10px;
    border-radius:8px;
    border:1px solid var(--input-border-color);
    background:var(--comfy-input-bg);
    color:var(--fg-color);
    text-decoration:none;
    font-size:10.5px;
    font-weight:600;
}
.anima-key-link:hover {
    background:var(--comfy-menu-bg);
    opacity:1;
}
.anima-key-field {
    display:flex;
    flex-direction:column;
    gap:6px;
}
.anima-key-field span {
    color:var(--fg-color);
    font-size:11px;
    font-weight:600;
}
.anima-key-field textarea {
    width:100%;
    resize:vertical;
    min-height:84px;
    padding:12px 14px;
    border-radius:12px;
    border:1px solid var(--input-border-color);
    background:var(--comfy-input-bg);
    color:var(--comfy-input-text);
    font-family:monospace;
    font-size:11px;
    line-height:1.5;
    box-sizing:border-box;
}
.anima-key-hint {
    margin:0;
    color:var(--fg-color);
    opacity:0.7;
    font-size:10.5px;
    line-height:1.5;
}
.anima-key-actions {
    display:flex;
    justify-content:flex-end;
    padding:0 18px 18px;
}

/* ===== Anima Multi-Select Browser ===== */
#anima-multi-browser { position:fixed; inset:0; z-index:99998; display:flex; align-items:center; justify-content:center; font-family:var(--comfy-font-family, sans-serif); }
#anima-multi-browser.hidden { display:none; }
#anima-multi-browser .backdrop { position:absolute; inset:0; background:rgba(0,0,0,.8); backdrop-filter:blur(10px); }
#anima-multi-browser .window { position:relative; z-index:1; width:min(96vw,1160px); height:min(93vh,880px); background:var(--comfy-menu-bg); border:1px solid var(--border-color); border-radius:14px; display:flex; flex-direction:column; overflow:hidden; box-shadow:0 40px 100px #000c; animation:anima-in .2s cubic-bezier(.22,1,.36,1); }
#anima-multi-browser .hdr { display:flex; align-items:center; gap:8px; padding:11px 14px; border-bottom:1px solid var(--border-color); flex-shrink:0; }
#anima-multi-browser .hdr-title { font-size:13px; font-weight:600; color:var(--fg-color); letter-spacing:.02em; white-space:nowrap; }
#anima-multi-browser .hdr-count { font-size:10px; color:var(--fg-color); opacity:0.5; font-family:monospace; }
#anima-multi-browser .hdr-gap { flex:1; }
#anima-multi-browser .search-wrap { position:relative; flex:1; max-width:300px; }
#anima-multi-browser .search-icon { position:absolute; left:9px; top:50%; transform:translateY(-50%); color:var(--input-border-color); font-size:11px; pointer-events:none; font-style:normal; font-family:monospace; }
#anima-multi-browser .search-input { width:100%; padding:7px 10px 7px 27px; background:var(--comfy-input-bg); border:1px solid var(--input-border-color); border-radius:7px; color:var(--comfy-input-text); font-family:monospace; font-size:12px; outline:none; transition:border-color .15s; box-sizing:border-box; }
#anima-multi-browser .search-input::placeholder { opacity:0.35; }
#anima-multi-browser .search-input:focus { border-color:var(--fg-color); opacity:0.6; }
#anima-multi-browser .hdr-select { padding:6px 8px; background:var(--comfy-input-bg); border:1px solid var(--input-border-color); border-radius:7px; color:var(--comfy-input-text); font-size:11px; cursor:pointer; outline:none; }
#anima-multi-browser .hdr-btn-txt { background:var(--comfy-input-bg); border:1px solid var(--input-border-color); color:var(--fg-color); font-family:var(--comfy-font-family,sans-serif); font-size:10px; font-weight:600; padding:6px 12px; border-radius:6px; cursor:pointer; transition:all .15s; }
#anima-multi-browser .hdr-btn-txt:hover { background:var(--comfy-menu-bg); opacity:1; }
#anima-multi-browser .hdr-close { width:29px; height:29px; display:flex; align-items:center; justify-content:center; background:transparent; border:1px solid var(--border-color); border-radius:7px; color:var(--fg-color); cursor:pointer; font-size:13px; transition:all .12s; flex-shrink:0; opacity:0.5; }
#anima-multi-browser .hdr-close:hover { background:rgba(255,80,80,0.1); border-color:rgba(255,100,100,0.4); color:#f88888; opacity:1; }
#anima-multi-browser .body { flex:1; overflow-y:auto; padding:12px; }
#anima-multi-browser .anima-grid { }
#anima-multi-browser .anima-empty { grid-column:1/-1; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:60px 20px; color:var(--fg-color); opacity:0.5; font-size:13px; gap:12px; }
#anima-multi-browser .ftr { display:flex; align-items:center; gap:10px; padding:10px 14px; border-top:1px solid var(--border-color); flex-shrink:0; }
#anima-multi-browser .ftr-count { font-size:11px; color:var(--fg-color); opacity:0.6; font-family:monospace; }
#anima-multi-browser .ftr-gap { flex:1; }
#anima-multi-browser .ftr-confirm { background:var(--comfy-input-bg); border:1px solid var(--input-border-color); color:var(--fg-color); font-family:var(--comfy-font-family,sans-serif); font-size:11px; font-weight:600; padding:8px 20px; border-radius:7px; cursor:pointer; transition:all .15s; }
#anima-multi-browser .ftr-confirm:hover { background:var(--comfy-menu-bg); border-color:var(--fg-color); opacity:1; }

/* Multi-select card check overlay */
.anima-multi-card { cursor:pointer; position:relative; }
.anima-multi-card .anima-card-check { position:absolute; top:4px; right:4px; z-index:2; }
.anima-multi-card .anima-card-check input[type="checkbox"] { width:16px; height:16px; accent-color:var(--fg-color); cursor:pointer; opacity:0.85; }
.anima-multi-card.selected { outline:2px solid var(--fg-color); outline-offset:-2px; border-radius:7px; }
.anima-multi-card.selected .anima-card-check input[type="checkbox"] { opacity:1; }
.anima-multi-card:hover .anima-card-check input[type="checkbox"] { opacity:1; }

/* ===== Save-as-Style modal ===== */
#anima-save-style-modal { position:fixed; inset:0; z-index:99999; display:flex; align-items:center; justify-content:center; font-family:var(--comfy-font-family, sans-serif); }
.anima-save-backdrop { position:absolute; inset:0; background:rgba(0,0,0,.75); backdrop-filter:blur(6px); }
.anima-save-window { position:relative; z-index:1; width:min(90vw,420px); background:var(--comfy-menu-bg); border:1px solid var(--border-color); border-radius:12px; box-shadow:0 30px 80px #000c; animation:anima-in .18s cubic-bezier(.22,1,.36,1); overflow:hidden; }
.anima-save-hdr { display:flex; align-items:center; justify-content:space-between; padding:12px 14px; border-bottom:1px solid var(--border-color); }
.anima-save-hdr span { font-size:13px; font-weight:600; color:var(--fg-color); }
.anima-save-close { width:26px; height:26px; display:flex; align-items:center; justify-content:center; background:transparent; border:1px solid var(--border-color); border-radius:6px; color:var(--fg-color); cursor:pointer; font-size:12px; opacity:0.5; }
.anima-save-close:hover { background:rgba(255,80,80,0.1); border-color:rgba(255,100,100,0.4); color:#f88888; opacity:1; }
.anima-save-body { padding:16px; display:flex; flex-direction:column; gap:10px; }
.anima-save-label { margin:0; font-size:12px; color:var(--fg-color); opacity:0.75; }
.anima-save-label strong { opacity:1; }
.anima-save-input { width:100%; padding:8px 10px; background:var(--comfy-input-bg); border:1px solid var(--input-border-color); border-radius:7px; color:var(--comfy-input-text); font-family:monospace; font-size:12px; outline:none; box-sizing:border-box; }
.anima-save-input:focus { border-color:var(--fg-color); opacity:0.6; }
.anima-save-db-list { display:flex; flex-direction:column; gap:4px; max-height:200px; overflow-y:auto; }
.anima-save-db-item { width:100%; padding:9px 12px; background:var(--comfy-input-bg); border:1px solid var(--input-border-color); border-radius:7px; color:var(--fg-color); font-family:var(--comfy-font-family,sans-serif); font-size:12px; cursor:pointer; text-align:left; transition:all .12s; }
.anima-save-db-item:hover { background:var(--comfy-menu-bg); border-color:var(--fg-color); }
.anima-save-actions { display:flex; gap:8px; justify-content:flex-end; margin-top:4px; }
.anima-save-btn { padding:7px 18px; background:var(--comfy-input-bg); border:1px solid var(--input-border-color); border-radius:7px; color:var(--fg-color); font-family:var(--comfy-font-family,sans-serif); font-size:11px; font-weight:600; cursor:pointer; transition:all .12s; }
.anima-save-btn:hover { background:var(--comfy-menu-bg); border-color:var(--fg-color); }
.anima-save-btn-cancel { padding:7px 14px; background:transparent; border:1px solid transparent; border-radius:7px; color:var(--fg-color); opacity:0.5; font-family:var(--comfy-font-family,sans-serif); font-size:11px; cursor:pointer; transition:all .12s; }
.anima-save-btn-cancel:hover { opacity:1; border-color:var(--border-color); }
`;
    document.head.appendChild(s);
}
