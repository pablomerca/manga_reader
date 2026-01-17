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

    /**
     * Mark a lemma as tracked and update visual styling.
     * Delegates to PageRenderer which owns the word element styling.
     * 
     * @param {string} lemma - The lemma to mark as tracked
     */
    markLemmaAsTracked(lemma) {
        if (this.pageRenderer) {
            this.pageRenderer.markLemmaAsTracked(lemma);
        }
    }

    /**
     * Highlight a block at specific coordinates with a red rectangle overlay.
     * 
     * Draws a red rectangle on the canvas at the exact position of an OCR block.
     * Used for visual navigation when clicking context panel entries.
     * 
     * @param {number} x - X coordinate of the block (in original image pixels)
     * @param {number} y - Y coordinate of the block (in original image pixels)
     * @param {number} width - Width of the block
     * @param {number} height - Height of the block
     */
    highlightBlockAtCoordinates(x, y, width, height) {
        // Remove any previous highlight overlays
        const existingHighlight = document.getElementById('block-highlight-overlay');
        if (existingHighlight) {
            existingHighlight.remove();
        }

        const viewportEl = document.getElementById('viewport');
        if (!viewportEl) return;

        // Find the OCR block that matches these coordinates
        // The blocks are rendered with style.left and style.top matching x and y
        const ocrBlocks = document.querySelectorAll('.ocr-block');
        let targetBlock = null;
        
        for (const block of ocrBlocks) {
            const blockX = parseFloat(block.style.left) || 0;
            const blockY = parseFloat(block.style.top) || 0;
            // Match with some tolerance for floating point
            if (Math.abs(blockX - x) < 0.5 && Math.abs(blockY - y) < 0.5) {
                targetBlock = block;
                break;
            }
        }

        // If no exact match found, estimate position (fallback)
        let screenRect;
        if (targetBlock) {
            // Get the actual rendered position of the block
            screenRect = targetBlock.getBoundingClientRect();
        } else {
            // Fallback: calculate manually using the page image as reference
            const pageImages = document.querySelectorAll('.page-image');
            if (pageImages.length === 0) return;
            
            const pageImage = pageImages[0];
            const pageRect = pageImage.getBoundingClientRect();
            const viewportRect = viewportEl.getBoundingClientRect();
            
            const zoomScale = this.zoomController.getScale();
            const imageX = pageRect.left - viewportRect.left;
            const imageY = pageRect.top - viewportRect.top;
            
            const screenX = imageX + (x * zoomScale);
            const screenY = imageY + (y * zoomScale);
            const screenWidth = width * zoomScale;
            const screenHeight = height * zoomScale;
            
            // Create a fake rect object for consistency
            screenRect = {
                left: screenX + viewportRect.left,
                top: screenY + viewportRect.top,
                width: screenWidth,
                height: screenHeight
            };
        }

        // Calculate position within viewport
        const viewportRect = viewportEl.getBoundingClientRect();
        const blockX = screenRect.left - viewportRect.left;
        const blockY = screenRect.top - viewportRect.top;
        const blockWidth = screenRect.width;
        const blockHeight = screenRect.height;

        // Create canvas overlay for drawing the highlight
        const canvas = document.createElement('canvas');
        canvas.id = 'block-highlight-overlay';
        canvas.style.position = 'absolute';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.pointerEvents = 'none';
        canvas.style.zIndex = '1000';

        // Set canvas dimensions to viewport size
        canvas.width = viewportEl.clientWidth;
        canvas.height = viewportEl.clientHeight;

        // Draw the highlight rectangle
        const ctx = canvas.getContext('2d');
        if (ctx) {
            // Red rectangle with semi-transparent fill
            ctx.fillStyle = 'rgba(255, 0, 0, 0.15)';
            ctx.fillRect(blockX, blockY, blockWidth, blockHeight);

            // Red border
            ctx.strokeStyle = 'rgb(255, 0, 0)';
            ctx.lineWidth = 3;
            ctx.strokeRect(blockX, blockY, blockWidth, blockHeight);
        }

        // Append canvas to viewport
        viewportEl.appendChild(canvas);

        // Auto-remove highlight after 5 seconds
        setTimeout(() => {
            const highlight = document.getElementById('block-highlight-overlay');
            if (highlight) {
                highlight.style.opacity = '0';
                highlight.style.transition = 'opacity 0.3s ease-out';
                setTimeout(() => highlight.remove(), 300);
            }
        }, 5000);
    }
}


// Instantiate and expose updateView for Python
const mangaViewer = new MangaViewer();
window.updateView = (data) => mangaViewer.updateView(data);
window.showWordPopup = (payload) => mangaViewer.showWordPopup(payload);
window.hideWordPopup = () => mangaViewer.hideWordPopup();
window.markWordAsTracked = () => mangaViewer.markWordAsTracked();
window.markLemmaAsTracked = (lemma) => mangaViewer.markLemmaAsTracked(lemma);
window.highlightBlockAtCoordinates = (x, y, width, height) => 
    mangaViewer.highlightBlockAtCoordinates(x, y, width, height);

