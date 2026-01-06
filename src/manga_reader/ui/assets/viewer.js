"use strict";

import { TextFormatter } from './modules/TextFormatter.js';
import { ZoomController } from './modules/ZoomController.js';
import { PanController } from './modules/PanController.js';

class MangaViewer {
    constructor() {
        // Text utilities
        this.textFormatter = new TextFormatter();
        
        // Controllers (initialized in setup after DOM ready)
        this.zoomController = new ZoomController(0.2, 5.0, 0.1);
        this.panController = null; // Needs viewport element

        // Layout and panning state
        this.layoutState = { totalWidth: 0, maxHeight: 0, fitScale: 1.0 };

        // DOM refs
        this.viewportEl = null;
        this.wrapperEl = null;
        this.popupEl = null;

        // Channel/state
        this.bridge = null;
        this.lastData = null;

        document.addEventListener("DOMContentLoaded", () => this.setup());
    }

    setup() {
        this.viewportEl = document.getElementById("viewport");
        this.wrapperEl = document.getElementById("content-wrapper");

        // Initialize PanController with viewport element
        this.panController = new PanController(this.viewportEl);

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

        window.addEventListener("click", (e) => this.handleGlobalClick(e));

        if (this.viewportEl) {
            this.viewportEl.addEventListener("wheel", (e) => this.handleWheelZoom(e), { passive: false });
            this.viewportEl.addEventListener("mousedown", (e) => this.handlePanStart(e));
            this.viewportEl.addEventListener("mousemove", (e) => this.handlePanMove(e));
            this.viewportEl.addEventListener("mouseup", () => this.handlePanEnd());
            this.viewportEl.addEventListener("mouseleave", () => this.handlePanEnd());
            
            // NEW: Delegate click handler for word spans
            this.viewportEl.addEventListener("click", (e) => this.handleWordClick(e));
        }

        const navHandler = (event) => this.handleNavigationKey(event);
        window.addEventListener("keydown", navHandler, { passive: false });
        document.addEventListener("keydown", navHandler, { passive: false, capture: true });
        if (document.body) {
            document.body.addEventListener("keydown", navHandler, { passive: false, capture: true });
        }
    }

    /**
     * Handle clicks on word spans to trigger dictionary lookup.
     * Only handles clicks on .word spans, not on regular OCR blocks.
     */
    handleWordClick(event) {
        // Check if the click target is a word span
        if (!event.target.classList.contains("word")) {
            return;
        }

        // Prevent default click handling for words
        event.stopPropagation();

        const wordSpan = event.target;
        const lemma = wordSpan.dataset.lemma;
        const surface = wordSpan.textContent;
        const rect = wordSpan.getBoundingClientRect();

        console.log(`[JS] Word clicked: lemma="${lemma}", surface="${surface}", x=${rect.x}, y=${rect.y}`);

        // Emit signal to Python via QWebChannel
        if (this.bridge && typeof this.bridge.requestWordLookup === "function") {
            this.bridge.requestWordLookup(lemma, surface, rect.x, rect.y, () => {});
        }
    }

    // Entry point called from Python
    updateView(data) {
        try {
            console.log("Received data update via runJavaScript.");
            this.lastData = data;
            this.zoomController.setScale(1.0);
            this.hideWordPopup();
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

        const totalScale = this.layoutState.fitScale * this.zoomController.getScale();
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
        this.zoomController.zoom(direction);

        this.applyScale();
    }

    handlePanStart(event) {
        if (event.button !== 0 || !this.viewportEl) return;

        // Don't pan if clicking inside the dictionary popup
        if (this.popupEl && this.popupEl.contains(event.target)) {
            return;
        }

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

        // Delegate to pan controller
        this.panController.startPan(event);
    }

    handlePanMove(event) {
        if (this.panController.movePan(event)) {
            // Only prevent default if actually panning (not selecting text)
            event.preventDefault();
        }
    }

    handlePanEnd() {
        this.panController.endPan();
    }

    handleNavigationKey(event) {
        if (event.key === "Escape") {
            this.hideWordPopup();
            return;
        }

        if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
            event.preventDefault();
            event.stopPropagation();
            const dir = event.key === "ArrowLeft" ? "next" : "prev"; // RTL: left=next, right=prev
            this.sendNavigation(dir);
        }
    }

    handleGlobalClick(event) {
        if (!this.popupEl) return;
        if (event.target.classList && event.target.classList.contains("word")) return;
        if (this.popupEl.contains(event.target)) return;
        this.hideWordPopup();
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
                
                // Filter words that belong to this line
                const lineStart = currentOffset;
                const lineEnd = currentOffset + lineText.length;
                const lineWords = block.words ? block.words.filter(word => {
                    return word.start < lineEnd && word.end > lineStart;
                }).map(word => ({
                    // Adjust offsets to be relative to this line
                    surface: word.surface,
                    lemma: word.lemma,
                    start: Math.max(0, word.start - lineStart),
                    end: Math.min(lineText.length, word.end - lineStart)
                })) : [];
                
                // Wrap words in this line
                if (lineWords.length > 0) {
                    lineEl.innerHTML = this.textFormatter.wrapWordsInText(lineText, lineWords);
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

    clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }

    showWordPopup(payload) {
        if (!payload || !this.viewportEl) return;

        if (this.popupEl) {
            this.popupEl.remove();
        }

        const popup = document.createElement("div");
        popup.className = "dictionary-popup";

        const safeSurface = this.textFormatter.escapeHtml(payload.surface || "");
        const safeReading = this.textFormatter.escapeHtml(payload.reading || "");
        const senses = Array.isArray(payload.senses) ? payload.senses : [];
        const notFound = Boolean(payload.notFound);

        const header = `<div class="dict-header"><div class="dict-surface">${safeSurface}</div><div class="dict-reading">${safeReading}</div></div>`;

        let sensesHtml = "";
        if (!notFound && senses.length > 0) {
            sensesHtml = senses
                .map((sense, idx) => {
                    const glosses = Array.isArray(sense.glosses) ? sense.glosses.map((g) => this.textFormatter.escapeHtml(g)).join("; ") : "";
                    const pos = Array.isArray(sense.pos) ? sense.pos.filter(Boolean).join(", ") : "";
                    const posPart = pos ? `<span class="dict-pos">${this.textFormatter.escapeHtml(pos)}</span>` : "";
                    return `<div class="dict-sense"><div class="dict-sense-title">${idx + 1}${posPart ? " · " + posPart : ""}</div><div class="dict-gloss">${glosses}</div></div>`;
                })
                .join("");
        } else {
            sensesHtml = `<div class="dict-empty">No definition found.</div>`;
        }

        popup.innerHTML = `${header}<div class="dict-body">${sensesHtml}</div>`;

        const popupWidth = 360;
        const popupHeight = 240;
        const anchorX = payload.mouseX || 0;
        const anchorY = payload.mouseY || 0;
        const viewportRect = this.viewportEl.getBoundingClientRect();
        const offset = 12;

        let left = anchorX + offset;
        if (left + popupWidth > viewportRect.right) {
            left = anchorX - popupWidth - offset;
        }
        left = this.clamp(left, viewportRect.left + 8, viewportRect.right - popupWidth - 8);

        let top = anchorY + offset;
        if (top + popupHeight > viewportRect.bottom) {
            top = anchorY - popupHeight - offset;
        }
        top = this.clamp(top, viewportRect.top + 8, viewportRect.bottom - popupHeight - 8);

        popup.style.width = `${popupWidth}px`;
        popup.style.maxHeight = `${popupHeight}px`;
        popup.style.left = `${left}px`;
        popup.style.top = `${top}px`;
        popup.style.position = "fixed";

        this.viewportEl.appendChild(popup);
        this.popupEl = popup;
    }

    hideWordPopup() {
        if (!this.popupEl) return;
        this.popupEl.remove();
        this.popupEl = null;
    }
}

// Instantiate and expose updateView for Python
const mangaViewer = new MangaViewer();
window.updateView = (data) => mangaViewer.updateView(data);
window.showWordPopup = (payload) => mangaViewer.showWordPopup(payload);
window.hideWordPopup = () => mangaViewer.hideWordPopup();
