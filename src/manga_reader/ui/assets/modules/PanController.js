/**
 * PanController Module
 * 
 * Manages pan gesture state and scrolling logic.
 * Requires viewport element reference to read/write scroll position.
 */
export class PanController {
    constructor(viewportEl) {
        this.viewportEl = viewportEl;
        this.isPanning = false;
        this.panStartX = 0;
        this.panStartY = 0;
        this.panScrollLeft = 0;
        this.panScrollTop = 0;
    }

    /**
     * Start a pan gesture.
     * 
     * @param {MouseEvent} event - The mousedown event
     * @returns {boolean} True if panning started, false otherwise
     */
    startPan(event) {
        if (!this.viewportEl) return false;

        // Only pan if content is actually scrollable
        if (!this.canPan()) {
            return false;
        }

        this.isPanning = true;
        this.viewportEl.classList.add("grabbing");
        this.panStartX = event.clientX;
        this.panStartY = event.clientY;
        this.panScrollLeft = this.viewportEl.scrollLeft;
        this.panScrollTop = this.viewportEl.scrollTop;
        return true;
    }

    /**
     * Continue a pan gesture (mouse move).
     * 
     * @param {MouseEvent} event - The mousemove event
     * @returns {boolean} True if panning was active, false otherwise
     */
    movePan(event) {
        if (!this.isPanning || !this.viewportEl) return false;

        const dx = event.clientX - this.panStartX;
        const dy = event.clientY - this.panStartY;
        this.viewportEl.scrollLeft = this.panScrollLeft - dx;
        this.viewportEl.scrollTop = this.panScrollTop - dy;
        return true;
    }

    /**
     * End a pan gesture.
     * 
     * @returns {boolean} True if was panning, false otherwise
     */
    endPan() {
        if (!this.isPanning || !this.viewportEl) return false;

        this.isPanning = false;
        this.viewportEl.classList.remove("grabbing");
        return true;
    }

    /**
     * Check if panning is currently active.
     * 
     * @returns {boolean} True if panning
     */
    isActive() {
        return this.isPanning;
    }

    /**
     * Check if content is scrollable (pan is possible).
     * 
     * @returns {boolean} True if content overflows viewport
     */
    canPan() {
        if (!this.viewportEl) return false;

        const canScrollH = this.viewportEl.scrollWidth > this.viewportEl.clientWidth;
        const canScrollV = this.viewportEl.scrollHeight > this.viewportEl.clientHeight;
        return canScrollH || canScrollV;
    }
}
