import { api } from "../../scripts/api.js";
import { Data } from "./data.js";
import { escapeHtml, favoriteKeyFromItem, localFavoriteFromStyle } from "./browser_helpers.js";
import { thumbUrl, thumbUrlPair } from "./utils.js";
import { renderChunkedGrid } from "./browser_renderers.js";
import {
    loadLocalFavorites,
    mutateLocalFavorites,
    rebuildFavoriteMap,
} from "./browser_favorites.js";
import { showToast } from "./toast.js";

let el = null;
let grid = null;
let countEl = null;
let searchInput = null;
let onConfirm = null;
let selected = new Set();
let allArtists = [];
let filter = "";
let sort = "tag";
let _debounceTimer = null;
let _observer = null;
let _localFavorites = [];
let _favoriteMap = new Map();
let _favOnly = false;
let _localToken = "";

function ensureObserver() {
    if (_observer) return;
    _observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) entry.target._mount?.();
            else entry.target._unmount?.();
        });
    }, { root: el.querySelector(".body"), rootMargin: "400px" });
}

function ensureDOM() {
    if (el) {
        ensureObserver();
        return;
    }
    el = document.createElement("div");
    el.id = "anima-multi-browser";
    el.className = "hidden";
    el.innerHTML =
        '<div class="backdrop"></div>' +
        '<div class="window">' +
            '<div class="hdr">' +
                '<span class="hdr-title">Select Artists</span>' +
                '<div class="search-wrap">' +
                    '<i class="search-icon">@</i>' +
                    '<input class="search-input" type="text" placeholder="Search artists..." autocomplete="off" spellcheck="false"/>' +
                '</div>' +
                '<select class="hdr-select" style="margin-left:6px">' +
                    '<option value="tag">A - Z</option>' +
                    '<option value="works">Popularity</option>' +
                '</select>' +
                '<span class="hdr-count" style="margin-left:10px"></span>' +
                '<div class="hdr-gap"></div>' +
                '<button class="hdr-btn-txt" data-action="select-all">Select All</button>' +
                '<button class="hdr-btn-txt" data-action="clear">Clear</button>' +
                '<button class="hdr-btn-txt" data-action="fav-filter">☆ Favorites</button>' +
                '<button class="hdr-close" title="Close">&#10005;</button>' +
            '</div>' +
            '<div class="body">' +
                '<div class="anima-grid anima-multi-grid"></div>' +
            '</div>' +
            '<div class="ftr">' +
                '<span class="ftr-count ftr-selected"></span>' +
                '<div class="ftr-gap"></div>' +
                '<button class="ftr-confirm">Confirm Selection</button>' +
            '</div>' +
        '</div>';

    document.body.appendChild(el);

    grid = el.querySelector(".anima-multi-grid");
    searchInput = el.querySelector(".search-input");
    countEl = el.querySelector(".hdr-count");

    ensureObserver();

    // Events
    el.querySelector(".backdrop").addEventListener("click", close);
    el.querySelector(".hdr-close").addEventListener("click", close);

    el.querySelector("[data-action='select-all']").addEventListener("click", () => {
        const visible = getFilteredArtists();
        visible.forEach(a => selected.add(a.tag));
        updateFooter();
        // Rebuild so mounted cards get updated checkboxes
        rebuildGrid(allArtists);
    });

    el.querySelector("[data-action='clear']").addEventListener("click", () => {
        selected.clear();
        updateFooter();
        rebuildGrid(allArtists);
    });

    el.querySelector("[data-action='fav-filter']").addEventListener("click", () => {
        _favOnly = !_favOnly;
        const btn = el.querySelector("[data-action='fav-filter']");
        btn.textContent = _favOnly ? "★ Favorites" : "☆ Favorites";
        btn.classList.toggle("active", _favOnly);
        rebuildGrid(allArtists);
    });

    el.querySelector(".ftr-confirm").addEventListener("click", () => {
        if (onConfirm) {
            const tags = [...selected];
            onConfirm(tags);
        }
        close();
    });

    searchInput.addEventListener("input", () => {
        clearTimeout(_debounceTimer);
        _debounceTimer = setTimeout(() => {
            filter = searchInput.value.trim().toLowerCase();
            rebuildGrid(allArtists);
        }, 150);
    });

    el.querySelector(".hdr-select").addEventListener("change", (e) => {
        sort = e.target.value;
        rebuildGrid(allArtists);
    });

    el.addEventListener("keydown", (e) => {
        if (e.key === "Escape") close();
    });
}

// ── Card renderer (called per-item by renderChunkedGrid) ───────────

function renderMultiCard(artist) {
    const tag = String(artist.tag || "");
    const isChecked = selected.has(tag);
    const isFav = _isFavorited(artist);
    const { primary: imgUrl, fallback: fallbackUrl } = thumbUrlPair(artist);
    const initChar = escapeHtml((tag[0] || "?").toUpperCase());

    const card = document.createElement("div");
    card.className = "anima-card anima-multi-card" + (isChecked ? " selected" : "");

    const imgHtml = imgUrl
        ? '<img loading="lazy" src="' + escapeHtml(imgUrl) + '" alt="' + escapeHtml(tag) + '"' +
          (fallbackUrl ? ' onerror="var f=this.getAttribute(\'data-fallback\');if(f&&this.src!==f){this.src=f;this.removeAttribute(\'data-fallback\');}else{this.style.display=\'none\';this.parentElement.classList.add(\'no-img\');}" data-fallback="' + escapeHtml(fallbackUrl) + '"' : ' onerror="this.style.display=\'none\';this.parentElement.classList.add(\'no-img\')"') +
          '/>'
        : "";

    card.innerHTML =
        '<div class="anima-card-img" data-init="' + initChar + '">' +
            imgHtml +
            '<div class="anima-card-check">' +
                '<input type="checkbox" ' + (isChecked ? "checked" : "") + '/>' +
            '</div>' +
        '</div>' +
        '<div class="anima-card-meta">' +
            '<span class="anima-card-tag">@' + escapeHtml(tag.replace(/_/g, " ")) + '</span>' +
            (artist.works ? '<span class="anima-card-works">' + Number(artist.works).toLocaleString() + ' works</span>' : "") +
            '<button class="anima-card-fav' + (isFav ? ' fav-active' : '') + '" title="' + (isFav ? 'Remove from favorites' : 'Add to favorites') + '">' +
                (isFav ? '★' : '☆') +
            '</button>' +
        '</div>';

    const checkbox = card.querySelector("input[type='checkbox']");
    const favBtn = card.querySelector(".anima-card-fav");

    card.addEventListener("click", (e) => {
        if (e.target === checkbox || e.target === favBtn || favBtn.contains(e.target)) return;
        toggleOne(card, tag);
    });

    checkbox.addEventListener("change", () => {
        if (checkbox.checked) selected.add(tag);
        else selected.delete(tag);
        card.classList.toggle("selected", checkbox.checked);
        updateFooter();
    });

    favBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        favBtn.disabled = true;
        try {
            await _toggleFavorite(artist, favBtn);
        } finally {
            favBtn.disabled = false;
        }
    });

    return card;
}

function toggleOne(card, tag) {
    if (selected.has(tag)) {
        selected.delete(tag);
        card.classList.remove("selected");
        card.querySelector("input[type='checkbox']").checked = false;
    } else {
        selected.add(tag);
        card.classList.add("selected");
        card.querySelector("input[type='checkbox']").checked = true;
    }
    updateFooter();
}

// ── Filter / sort helpers ──────────────────────────────────────────

function getFilteredArtists() {
    let list = allArtists;
    if (_favOnly) {
        list = list.filter(a => _isFavorited(a));
    }
    if (!filter) return list;
    return list.filter(a => {
        const s = (a.tag + " " + (a.name || "")).toLowerCase();
        return s.includes(filter);
    });
}

function getSortedArtists(list) {
    const copy = [...list];
    if (sort === "works") {
        copy.sort((a, b) => (b.works || 0) - (a.works || 0));
    } else {
        copy.sort((a, b) => (a.tag || "").localeCompare(b.tag || ""));
    }
    return copy;
}

// ── Favorites helpers ────────────────────────────────────────────

function _isFavorited(artist) {
    const key = favoriteKeyFromItem(artist);
    return key ? _favoriteMap.has(key) : false;
}

async function _loadFavorites() {
    // Fetch local token for POST requests
    if (!_localToken) {
        try {
            const r = await api.fetchApi("/anima/fullet_auth_status");
            const data = await r.json().catch(() => ({}));
            _localToken = String(data?.localToken || "");
        } catch (_) { }
    }
    _localFavorites = await loadLocalFavorites(api);
    _favoriteMap = rebuildFavoriteMap(_localFavorites, []);
}

function _localHeaders() {
    if (!_localToken) return {};
    return { "x-anima-local-token": _localToken };
}

async function _toggleFavorite(artist, anchorEl) {
    const entry = localFavoriteFromStyle(artist);
    if (!entry) return;

    const already = _favoriteMap.has(entry.key);
    const result = already
        ? await mutateLocalFavorites(api, _localHeaders(), { action: "remove", key: entry.key })
        : await mutateLocalFavorites(api, _localHeaders(), { action: "upsert", item: entry });

    if (!result.ok) {
        showToast(result.error || "Could not update favorite", "error", 2000, { anchor: anchorEl });
        return;
    }

    _localFavorites = Array.isArray(result.items) ? result.items : _localFavorites;
    _favoriteMap = rebuildFavoriteMap(_localFavorites, []);

    const nextState = !already;
    showToast(nextState ? "Added to favorites" : "Removed from favorites", "success", 1500, { anchor: anchorEl });

    // Rebuild grid so all cards reflect new favorite state
    rebuildGrid(allArtists);
}

// ── Grid rebuild using renderChunkedGrid ───────────────────────────

function rebuildGrid(artists) {
    if (!grid) return;

    const filtered = getFilteredArtists();
    const sorted = getSortedArtists(filtered);

    renderChunkedGrid({
        grid,
        observer: _observer,
        items: sorted,
        chunkSize: 40,
        minHeight: "120px",
        renderItem: renderMultiCard,
        append: false,
    });

    updateFooter();
}

function updateFooter() {
    const footerEl = el.querySelector(".ftr-selected");
    if (footerEl) {
        footerEl.textContent = selected.size + " artist" + (selected.size !== 1 ? "s" : "") + " selected";
    }
    if (countEl) {
        const visible = filter ? getFilteredArtists().length : allArtists.length;
        countEl.textContent = visible + " / " + allArtists.length + " artists";
    }
}

// ── Public API ──────────────────────────────────────────────────────

async function open(nodeOrCallback, confirmCallback) {
    ensureDOM();

    // Trigger background image download (non-blocking)
    try {
        api.fetchApi("/anima/download_images", { method: "POST" }).catch(() => {});
    } catch (_) {}

    if (typeof nodeOrCallback === "function") {
        onConfirm = nodeOrCallback;
    } else {
        onConfirm = (tagList) => {
            const widgets = nodeOrCallback.widgets || [];
            const posWidget = widgets.find(w => w.name === "positive");
            const addAtWidget = widgets.find(w => w.name === "add_at_prefix");
            const addAt = addAtWidget ? addAtWidget.value !== false : true;
            const prefix = addAt ? "@" : "";
            const tags = tagList.map(t => prefix + t).join(", ");

            if (posWidget) {
                const current = String(posWidget.value || "").trim();
                posWidget.value = tags + (current ? ", " + current : "");
                posWidget.callback?.(posWidget.value);
            }
            nodeOrCallback.setDirtyCanvas?.(true, true);
        };
    }

    // Parse existing artists from the positive prompt
    selected.clear();
    if (nodeOrCallback && !Array.isArray(nodeOrCallback) && nodeOrCallback.widgets) {
        const posWidget = nodeOrCallback.widgets.find(w => w.name === "positive");
        if (posWidget && posWidget.value) {
            const match = String(posWidget.value).match(/^(@?\w+(?:,\s*@?\w+)*)/);
            if (match) {
                match[1].split(/[,\s]+/).forEach(t => {
                    t = t.trim().replace(/^@/, "");
                    if (t) selected.add(t);
                });
            }
        }
    }

    grid.innerHTML = '<div class="anima-empty"><div class="anima-spinner"></div><span>Loading artists...</span></div>';
    el.classList.remove("hidden");
    searchInput.value = "";
    filter = "";
    searchInput.focus();

    try {
        allArtists = await Data.all();
        await _loadFavorites();
        rebuildGrid(allArtists);
    } catch (e) {
        grid.innerHTML = '<div class="anima-empty"><span>Failed to load artists.</span></div>';
        console.error("[MultiSelectBrowser] Load error:", e);
    }
}

function close() {
    if (!el) return;
    el.classList.add("hidden");
    onConfirm = null;
    selected.clear();
    allArtists = [];
    _localFavorites = [];
    _favoriteMap = new Map();
    _favOnly = false;
    _localToken = "";
    if (_observer) _observer.disconnect();
    _observer = null;
    if (grid) grid.innerHTML = "";
    clearTimeout(_debounceTimer);
}

export const MultiSelectBrowser = { open, close };
