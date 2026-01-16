"use strict";

import { TextFormatter } from './modules/TextFormatter.js';
import { ZoomController } from './modules/ZoomController.js';
import { PanController } from './modules/PanController.js';
import { LayoutManager } from './modules/LayoutManager.js';
import { PageRenderer } from './modules/PageRenderer.js';
import { PopupManager } from './modules/PopupManager.js';
import { ChannelBridge } from './modules/ChannelBridge.js';
import { EventRouter } from './modules/EventRouter.js';

class MangaViewer {
    constructor() {
        // Text utilities
        this.textFormatter = new TextFormatter();
        
        // Controllers (initialized in setup after DOM ready)
        this.zoomController = new ZoomController(0.2, 5.0, 0.1);
        this.panController = null; // Needs viewport element
        this.layoutManager = null; // Needs viewport and wrapper elements
        this.pageRenderer = null; // Needs textFormatter and bridge
        this.popupManager = null; // Needs viewport element
        this.channelBridge = new ChannelBridge();
        this.eventRouter = null; // Needs viewport element and callbacks

        // DOM refs
        this.viewportEl = null;
        this.wrapperEl = null;

        // Channel/state
        this.lastData = null;

        document.addEventListener("DOMContentLoaded", () => this.setup());
    }

    setup() {
        this.viewportEl = document.getElementById("viewport");
        this.wrapperEl = document.getElementById("content-wrapper");

        // Initialize modules with DOM elements
        this.panController = new PanController(this.viewportEl);
        this.layoutManager = new LayoutManager(this.viewportEl, this.wrapperEl);
        // pageRenderer is created when the channel bridge is ready (see initChannel)
        this.popupManager = new PopupManager(this.viewportEl, this.textFormatter, this.channelBridge);

        // Initialize event router with callbacks
        this.eventRouter = new EventRouter(this.viewportEl, {
            onResize: () => this.handleResize(),
            onGlobalClick: (e) => this.handleGlobalClick(e),
            onWheelZoom: (e) => this.handleWheelZoom(e),
            onPanStart: (e) => this.handlePanStart(e),
            onPanMove: (e) => this.handlePanMove(e),
            onPanEnd: () => this.handlePanEnd(),
            onWordClick: (e) => this.handleWordClick(e),
            onKeydown: (e) => this.handleNavigationKey(e)
        });

        this.makeBodyFocusable();
        this.initChannel();
        this.eventRouter.bindAll();
    }

    makeBodyFocusable() {
        if (document.body) {
            document.body.setAttribute("tabindex", "0");
            document.body.focus();
        }
    }

    initChannel() {
        this.channelBridge.initialize((connector) => {
            // Construct page renderer once the bridge is ready
            this.pageRenderer = new PageRenderer(this.textFormatter, connector);
        });
    }

    handleResize() {
        if (this.lastData) {
            this.recomputeScale();
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

        // Find the block and page containers for precise context
        const blockEl = wordSpan.closest(".ocr-block");
        const blockId = blockEl ? parseInt(blockEl.dataset.blockId || "-1", 10) : -1;
        const pageEl = wordSpan.closest(".page-container");
        const pageIndex = pageEl ? parseInt(pageEl.dataset.pageIndex || "-1", 10) : -1;

        console.log(`[JS] Word clicked: lemma="${lemma}", surface="${surface}", x=${rect.x}, y=${rect.y}`);

        // Emit signal to Python via ChannelBridge
        this.channelBridge.requestWordLookup(lemma, surface, rect.x, rect.y, pageIndex, blockId);
    }

    // Entry point called from Python
    updateView(data) {
        try {
            console.log("Received data update via runJavaScript.");
            this.lastData = data;
            this.zoomController.setScale(1.0);
            this.popupManager.hide();
            this.renderPages(data);
            this.layoutManager.resetScroll();
            this.recomputeScale();
        } catch (e) {
            console.error("Failed to render pages:", e);
        }
    }

    renderPages(data) {
        if (!this.wrapperEl) return;
        if (!this.pageRenderer) {
            throw new Error("PageRenderer not initialized; bridge not ready");
        }
        this.wrapperEl.innerHTML = "";

        const pages = data.pages;
        const gap = data.gap || 20;

        let totalWidth = 0;
        let maxHeight = 0;

        pages.forEach((page, index) => {
            const pageEl = this.pageRenderer.createPageElement(page);
            if (typeof page.pageIndex === "number") {
                pageEl.dataset.pageIndex = String(page.pageIndex);
            }
            this.wrapperEl.appendChild(pageEl);

            totalWidth += page.width;
            maxHeight = Math.max(maxHeight, page.height);

            if (index < pages.length - 1) {
                pageEl.style.marginRight = gap + "px";
                totalWidth += gap;
            }
        });

        this.layoutManager.setDimensions(totalWidth, maxHeight);
    }

    recomputeScale() {
        this.layoutManager.computeFitScale();
        this.applyScale();
    }

    applyScale() {
        this.layoutManager.applyLayout(this.zoomController.getScale());
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
        if (this.popupManager.contains(event.target)) {
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
            this.popupManager.hide();
            return;
        }

        if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
            event.preventDefault();
            event.stopPropagation();
            const dir = event.key === "ArrowLeft" ? "next" : "prev"; // RTL: left=next, right=prev
            this.channelBridge.requestNavigation(dir);
        }
    }

    handleGlobalClick(event) {
        if (!this.popupManager.isVisible()) return;
        if (event.target.classList && event.target.classList.contains("word")) return;
        if (this.popupManager.contains(event.target)) return;
        this.popupManager.hide();
    }

    clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }

    // Python interface methods (delegates to popupManager)
    showWordPopup(payload) {
        this.popupManager.show(payload);
    }

    hideWordPopup() {
        this.popupManager.hide();
    }

    markWordAsTracked() {
        this.popupManager.markWordAsTracked();
    }
}

// Instantiate and expose updateView for Python
const mangaViewer = new MangaViewer();
window.updateView = (data) => mangaViewer.updateView(data);
window.showWordPopup = (payload) => mangaViewer.showWordPopup(payload);
window.hideWordPopup = () => mangaViewer.hideWordPopup();
window.markWordAsTracked = () => mangaViewer.markWordAsTracked();
