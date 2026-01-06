"use strict";

// Global state
let bridge = null;
let lastData = null;
let viewportEl = null;

// Zoom state (fit-to-window scale is recalculated on resize, userScale is driven by Ctrl+wheel)
const ZOOM_STEP = 0.1;
const MIN_USER_SCALE = 0.2;
const MAX_USER_SCALE = 5.0;
let userScale = 1.0;

// Layout cache to avoid recomputing dimensions when only zoom changes
const layoutState = {
    totalWidth: 0,
    maxHeight: 0,
    fitScale: 1.0,
};

"use strict";

class MangaViewer {
    constructor() {
        // Zoom state
        this.ZOOM_STEP = 0.1;
        this.MIN_USER_SCALE = 0.2;
        this.MAX_USER_SCALE = 5.0;
        this.userScale = 1.0;

        // Layout and panning state
        this.layoutState = { totalWidth: 0, maxHeight: 0, fitScale: 1.0 };
        this.isPanning = false;
        this.panStartX = 0;
        this.panStartY = 0;
        this.panScrollLeft = 0;
        this.panScrollTop = 0;

        // DOM refs
        this.viewportEl = null;
        this.wrapperEl = null;

        // Channel/state
        this.bridge = null;
        this.lastData = null;

        document.addEventListener("DOMContentLoaded", () => this.setup());
    }

    setup() {
        this.viewportEl = document.getElementById("viewport");
        this.wrapperEl = document.getElementById("content-wrapper");

        this.makeBodyFocusable();
        this.initChannel();
        this.bindEvents();
    }

    makeBodyFocusable() {
        if (document.body) {
            document.body.setAttribute("tabindex", "0");
            document.body.focus();
        }
    }

    initChannel() {
        if (typeof qt !== "undefined" && qt.webChannelTransport) {
            new QWebChannel(qt.webChannelTransport, (channel) => {
                console.log("QWebChannel connected.");
                this.bridge = channel.objects.connector;
                if (!this.bridge) {
                    console.error("Connector object not found in WebChannel objects:", channel.objects);
                    return;
                }
                console.log("Bridge object found:", this.bridge);
            });
        } else {
            console.error("Qt WebChannel not found! Ensure this is running inside QWebEngineView.");
        }
    }

    bindEvents() {
        window.addEventListener("resize", () => {
            if (this.lastData) this.recomputeScale();
        });

        if (this.viewportEl) {
            this.viewportEl.addEventListener("wheel", (e) => this.handleWheelZoom(e), { passive: false });
            this.viewportEl.addEventListener("mousedown", (e) => this.handlePanStart(e));
            this.viewportEl.addEventListener("mousemove", (e) => this.handlePanMove(e));
            this.viewportEl.addEventListener("mouseup", () => this.handlePanEnd());
            this.viewportEl.addEventListener("mouseleave", () => this.handlePanEnd());
            
            // NEW: Delegate click handler for noun spans
            this.viewportEl.addEventListener("click", (e) => this.handleNounClick(e));
        }

        const navHandler = (event) => this.handleNavigationKey(event);
        window.addEventListener("keydown", navHandler, { passive: false });
        document.addEventListener("keydown", navHandler, { passive: false, capture: true });
        if (document.body) {
            document.body.addEventListener("keydown", navHandler, { passive: false, capture: true });
        }
    }

    /**
     * Handle clicks on noun spans to trigger dictionary lookup.
     * Only handles clicks on .noun spans, not on regular OCR blocks.
     */
    handleNounClick(event) {
        // Check if the click target is a noun span
        if (!event.target.classList.contains("noun")) {
            return;
        }

        // Prevent default click handling for nouns
        event.stopPropagation();

        const nounSpan = event.target;
        const lemma = nounSpan.dataset.lemma;
        const surface = nounSpan.textContent;
        const rect = nounSpan.getBoundingClientRect();

        console.log(`[JS] Noun clicked: lemma="${lemma}", surface="${surface}", x=${rect.x}, y=${rect.y}`);

        // Emit signal to Python via QWebChannel
        if (this.bridge && typeof this.bridge.requestNounLookup === "function") {
            this.bridge.requestNounLookup(lemma, surface, rect.x, rect.y, () => {});
        }
    }

    // Entry point called from Python
    updateView(data) {
        try {
            console.log("Received data update via runJavaScript.");
            this.lastData = data;
            this.userScale = 1.0;
            this.renderPages(data);
            this.resetViewportScroll();
            this.recomputeScale();
        } catch (e) {
            console.error("Failed to render pages:", e);
        }
    }

    renderPages(data) {
        if (!this.wrapperEl) return;
        this.wrapperEl.innerHTML = "";

        const pages = data.pages;
        const gap = data.gap || 20;

        let totalWidth = 0;
        let maxHeight = 0;

        pages.forEach((page, index) => {
            const pageEl = this.createPageElement(page);
            this.wrapperEl.appendChild(pageEl);

            totalWidth += page.width;
            maxHeight = Math.max(maxHeight, page.height);

            if (index < pages.length - 1) {
                pageEl.style.marginRight = gap + "px";
                totalWidth += gap;
            }
        });

        this.layoutState.totalWidth = totalWidth;
        this.layoutState.maxHeight = maxHeight;
    }

    recomputeScale() {
        if (!this.viewportEl || !this.wrapperEl || this.layoutState.totalWidth === 0 || this.layoutState.maxHeight === 0) return;

        const vWidth = this.viewportEl.clientWidth;
        const vHeight = this.viewportEl.clientHeight;

        let fit = Math.min(vWidth / this.layoutState.totalWidth, vHeight / this.layoutState.maxHeight);
        if (!Number.isFinite(fit) || fit <= 0) fit = 1.0;

        this.layoutState.fitScale = fit;
        this.applyScale();
    }

    applyScale() {
        if (!this.wrapperEl || !this.viewportEl) return;

        this.wrapperEl.style.width = this.layoutState.totalWidth + "px";
        this.wrapperEl.style.height = this.layoutState.maxHeight + "px";

        const totalScale = this.layoutState.fitScale * this.userScale;
        this.wrapperEl.style.transform = `scale(${totalScale})`;
        this.wrapperEl.style.transformOrigin = "top left";

        const scaledWidth = this.layoutState.totalWidth * totalScale;
        const scaledHeight = this.layoutState.maxHeight * totalScale;
        const hPad = Math.max((this.viewportEl.clientWidth - scaledWidth) / 2, 0);
        const vPad = Math.max((this.viewportEl.clientHeight - scaledHeight) / 2, 0);

        this.wrapperEl.style.marginLeft = `${hPad}px`;
        this.wrapperEl.style.marginRight = `${hPad}px`;
        this.wrapperEl.style.marginTop = `${vPad}px`;
        this.wrapperEl.style.marginBottom = `${vPad}px`;

        if (scaledWidth <= this.viewportEl.clientWidth) this.viewportEl.scrollLeft = 0;
        if (scaledHeight <= this.viewportEl.clientHeight) this.viewportEl.scrollTop = 0;
    }

    handleWheelZoom(event) {
        if (!event.ctrlKey && !event.metaKey) return;

        event.preventDefault();

        const direction = event.deltaY < 0 ? 1 : -1;
        const factor = 1 + this.ZOOM_STEP;
        const nextScale = direction > 0 ? this.userScale * factor : this.userScale / factor;
        this.userScale = this.clamp(nextScale, this.MIN_USER_SCALE, this.MAX_USER_SCALE);

        this.applyScale();
    }

    handlePanStart(event) {
        if (event.button !== 0 || !this.viewportEl) return;

        // Check if clicked element is within an OCR line (includes noun spans, text content, etc.)
        let target = event.target;
        let isInOCRLine = false;
        
        // Traverse up the DOM tree to see if we're inside an ocr-line
        while (target && target !== this.viewportEl) {
            if (target.classList && target.classList.contains("ocr-line")) {
                isInOCRLine = true;
                break;
            }
            target = target.parentElement;
        }
        
        // Don't pan if clicking within an OCR line (text selection area)
        if (isInOCRLine) {
            return;
        }

        // Only pan if content is actually scrollable (zoomed in beyond viewport)
        const canScrollH = this.viewportEl.scrollWidth > this.viewportEl.clientWidth;
        const canScrollV = this.viewportEl.scrollHeight > this.viewportEl.clientHeight;
        if (!canScrollH && !canScrollV) {
            return; // Content fits on screen, don't pan
        }

        this.isPanning = true;
        this.viewportEl.classList.add("grabbing");
        this.panStartX = event.clientX;
        this.panStartY = event.clientY;
        this.panScrollLeft = this.viewportEl.scrollLeft;
        this.panScrollTop = this.viewportEl.scrollTop;
    }

    handlePanMove(event) {
        if (!this.isPanning || !this.viewportEl) return;
        // Only prevent default if actually panning (not selecting text)
        event.preventDefault();
        const dx = event.clientX - this.panStartX;
        const dy = event.clientY - this.panStartY;
        this.viewportEl.scrollLeft = this.panScrollLeft - dx;
        this.viewportEl.scrollTop = this.panScrollTop - dy;
    }

    handlePanEnd() {
        if (!this.isPanning || !this.viewportEl) return;
        this.isPanning = false;
        this.viewportEl.classList.remove("grabbing");
    }

    handleNavigationKey(event) {
        if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
            event.preventDefault();
            event.stopPropagation();
            const dir = event.key === "ArrowLeft" ? "next" : "prev"; // RTL: left=next, right=prev
            this.sendNavigation(dir);
        }
    }

    sendNavigation(direction) {
        if (this.bridge && typeof this.bridge.requestNavigation === "function") {
            this.bridge.requestNavigation(direction, () => {});
        }
    }

    resetViewportScroll() {
        if (!this.viewportEl) return;
        this.viewportEl.scrollLeft = 0;
        this.viewportEl.scrollTop = 0;
    }

    createPageElement(pageData) {
        const container = document.createElement("div");
        container.className = "page-container";
        container.style.width = pageData.width + "px";
        container.style.height = pageData.height + "px";

        const img = document.createElement("img");
        img.className = "page-image";
        img.src = pageData.imageUrl;
        container.appendChild(img);

        if (pageData.blocks) {
            pageData.blocks.forEach((block) => {
                const blockEl = this.createBlockElement(block);
                container.appendChild(blockEl);
            });
        }
        return container;
    }

    createBlockElement(block) {
        const el = document.createElement("div");
        el.className = "ocr-block";
        el.style.left = block.x + "px";
        el.style.top = block.y + "px";
        el.style.width = block.width + "px";
        el.style.height = block.height + "px";

        el.onclick = () => {
            if (this.bridge && typeof this.bridge.blockClicked === "function") {
                this.bridge.blockClicked(block.id, () => {});
            }
        };

        if (block.lines) {
            // Process each line with adjusted noun offsets
            let currentOffset = 0;
            
            block.lines.forEach((lineText) => {
                const lineEl = document.createElement("div");
                lineEl.className = "ocr-line";
                
                // Filter nouns that belong to this line
                const lineStart = currentOffset;
                const lineEnd = currentOffset + lineText.length;
                const lineNouns = block.nouns ? block.nouns.filter(noun => {
                    return noun.start < lineEnd && noun.end > lineStart;
                }).map(noun => ({
                    // Adjust offsets to be relative to this line
                    surface: noun.surface,
                    lemma: noun.lemma,
                    start: Math.max(0, noun.start - lineStart),
                    end: Math.min(lineText.length, noun.end - lineStart)
                })) : [];
                
                // Wrap nouns in this line
                if (lineNouns.length > 0) {
                    lineEl.innerHTML = this.wrapNounsInText(lineText, lineNouns);
                } else {
                    lineEl.textContent = lineText;
                }
                
                lineEl.style.fontSize = block.fontSize + "px";
                el.appendChild(lineEl);
                
                currentOffset = lineEnd;
            });
        }
        return el;
    }

    /**
     * Wraps noun tokens in HTML spans for highlighting and interaction.
     * Works on the full block text with correct offsets.
     */
    wrapNounsInText(text, nouns) {
        if (!nouns || nouns.length === 0) {
            return this.escapeHtml(text);
        }

        // Sort nouns by start offset
        const sortedNouns = [...nouns].sort((a, b) => a.start - b.start);

        let result = "";
        let lastIndex = 0;

        for (const noun of sortedNouns) {
            // Add text before the noun
            if (noun.start > lastIndex) {
                result += this.escapeHtml(text.substring(lastIndex, noun.start));
            }

            // Add the noun with span
            const nounText = text.substring(noun.start, noun.end);
            const escapedLemma = this.escapeAttr(noun.lemma);
            result += `<span class="noun" data-lemma="${escapedLemma}">${this.escapeHtml(nounText)}</span>`;

            lastIndex = noun.end;
        }

        // Add remaining text
        if (lastIndex < text.length) {
            result += this.escapeHtml(text.substring(lastIndex));
        }

        return result;
    }

    /**
     * Escapes HTML special characters to prevent XSS.
     */
    escapeHtml(text) {
        const map = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;",
        };
        return text.replace(/[&<>"']/g, (m) => map[m]);
    }

    /**
     * Escapes HTML attribute values.
     */
    escapeAttr(text) {
        return text.replace(/"/g, "&quot;");
    }

    clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }
}

// Instantiate and expose updateView for Python
const mangaViewer = new MangaViewer();
window.updateView = (data) => mangaViewer.updateView(data);
