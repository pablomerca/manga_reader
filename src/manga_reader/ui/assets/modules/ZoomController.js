/**
 * ZoomController Module
 * 
 * Manages zoom state and scale calculations.
 * Independent of DOM, layout, or rendering concerns.
 */
export class ZoomController {
    constructor(minScale = 0.2, maxScale = 5.0, step = 0.1) {
        this.MIN_SCALE = minScale;
        this.MAX_SCALE = maxScale;
        this.ZOOM_STEP = step;
        this.userScale = 1.0;
    }

    /**
     * Zoom in or out by one step.
     * 
     * @param {number} direction - Positive for zoom in, negative for zoom out
     * @returns {number} The new scale after zooming
     */
    zoom(direction) {
        const factor = 1 + this.ZOOM_STEP;
        const nextScale = direction > 0 
            ? this.userScale * factor 
            : this.userScale / factor;
        this.userScale = this.clamp(nextScale, this.MIN_SCALE, this.MAX_SCALE);
        return this.userScale;
    }

    /**
     * Set the user scale directly (e.g., reset to 1.0).
     * 
     * @param {number} scale - The scale value to set
     * @returns {number} The clamped scale
     */
    setScale(scale) {
        this.userScale = this.clamp(scale, this.MIN_SCALE, this.MAX_SCALE);
        return this.userScale;
    }

    /**
     * Get the current user scale.
     * 
     * @returns {number} Current scale value
     */
    getScale() {
        return this.userScale;
    }

    /**
     * Clamp a value between min and max.
     * 
     * @param {number} value - Value to clamp
     * @param {number} min - Minimum value
     * @param {number} max - Maximum value
     * @returns {number} Clamped value
     */
    clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }
}
