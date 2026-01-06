/**
 * LayoutManager Module
 * 
 * Manages content layout, fit-to-screen calculations, and CSS transformations.
 * Handles positioning and scaling of content within the viewport.
 */
export class LayoutManager {
    constructor(viewportEl, wrapperEl) {
        this.viewportEl = viewportEl;
        this.wrapperEl = wrapperEl;
        this.layoutState = {
            totalWidth: 0,
            maxHeight: 0,
            fitScale: 1.0
        };
    }

    /**
     * Update the layout dimensions (content size).
     * 
     * @param {number} totalWidth - Total width of all pages
     * @param {number} maxHeight - Maximum height among pages
     */
    setDimensions(totalWidth, maxHeight) {
        this.layoutState.totalWidth = totalWidth;
        this.layoutState.maxHeight = maxHeight;
    }

    /**
     * Compute the fit-to-screen scale factor.
     * 
     * @returns {number} The computed fit scale
     */
    computeFitScale() {
        if (!this.viewportEl || this.layoutState.totalWidth === 0 || this.layoutState.maxHeight === 0) {
            return 1.0;
        }

        const vWidth = this.viewportEl.clientWidth;
        const vHeight = this.viewportEl.clientHeight;

        let fit = Math.min(vWidth / this.layoutState.totalWidth, vHeight / this.layoutState.maxHeight);
        if (!Number.isFinite(fit) || fit <= 0) fit = 1.0;

        this.layoutState.fitScale = fit;
        return fit;
    }

    /**
     * Apply layout transformations (scale, position, margins).
     * 
     * @param {number} userScale - User zoom scale (from ZoomController)
     */
    applyLayout(userScale) {
        if (!this.wrapperEl || !this.viewportEl) return;

        this.wrapperEl.style.width = this.layoutState.totalWidth + "px";
        this.wrapperEl.style.height = this.layoutState.maxHeight + "px";

        const totalScale = this.layoutState.fitScale * userScale;
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

        // Reset scroll if content fits on screen
        if (scaledWidth <= this.viewportEl.clientWidth) this.viewportEl.scrollLeft = 0;
        if (scaledHeight <= this.viewportEl.clientHeight) this.viewportEl.scrollTop = 0;
    }

    /**
     * Reset viewport scroll to top-left.
     */
    resetScroll() {
        if (!this.viewportEl) return;
        this.viewportEl.scrollLeft = 0;
        this.viewportEl.scrollTop = 0;
    }

    /**
     * Get current layout state.
     * 
     * @returns {Object} Layout state with totalWidth, maxHeight, fitScale
     */
    getState() {
        return { ...this.layoutState };
    }
}
