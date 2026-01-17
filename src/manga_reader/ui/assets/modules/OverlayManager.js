/**
 * OverlayManager Module
 * 
 * Manages visual overlay elements (highlights, annotations, etc.) on the manga canvas.
 * Handles creation, positioning, rendering, and lifecycle management of overlay elements.
 */
export class OverlayManager {
    constructor(viewportEl) {
        this.viewportEl = viewportEl;
        this.highlightPadding = 8; // pixels of padding around highlighted blocks
    }

    /**
     * Highlight a block at specific coordinates with a red rectangle overlay.
     * 
     * Finds the actual rendered OCR block element matching the coordinates and draws
     * a highlight overlay at its exact position, accounting for all transformations.
     * 
     * @param {number} x - X coordinate of the block (in original image pixels)
     * @param {number} y - Y coordinate of the block (in original image pixels)
     * @param {number} width - Width of the block
     * @param {number} height - Height of the block
     * @param {ZoomController} zoomController - Zoom controller for scale calculations
     */
    highlightBlock(x, y, width, height, zoomController) {
        // Remove any previous highlight overlays
        this._clearPreviousHighlight();

        if (!this.viewportEl) return;

        // Find the OCR block that matches these coordinates
        // The blocks are rendered with style.left and style.top matching x and y
        const targetBlock = this._findOCRBlock(x, y);

        // Determine the actual rendered position of the block
        let blockX, blockY, blockWidth, blockHeight;
        
        if (targetBlock) {
            // Get the actual rendered position of the block
            const screenRect = targetBlock.getBoundingClientRect();
            const viewportRect = this.viewportEl.getBoundingClientRect();
            
            blockX = screenRect.left - viewportRect.left;
            blockY = screenRect.top - viewportRect.top;
            blockWidth = screenRect.width;
            blockHeight = screenRect.height;
        } else {
            // Fallback: calculate manually using the page image as reference
            const { blockX: x2, blockY: y2, blockWidth: w2, blockHeight: h2 } = 
                this._calculateFallbackPosition(x, y, width, height, zoomController);
            
            blockX = x2;
            blockY = y2;
            blockWidth = w2;
            blockHeight = h2;
        }

        // Draw the highlight
        this._drawHighlight(blockX, blockY, blockWidth, blockHeight);
    }

    /**
     * Find OCR block element matching the given coordinates.
     * 
     * @param {number} x - X coordinate to match
     * @param {number} y - Y coordinate to match
     * @returns {HTMLElement|null} The matching block element or null
     * @private
     */
    _findOCRBlock(x, y) {
        const ocrBlocks = document.querySelectorAll('.ocr-block');
        
        for (const block of ocrBlocks) {
            const blockX = parseFloat(block.style.left) || 0;
            const blockY = parseFloat(block.style.top) || 0;
            
            // Match with some tolerance for floating point
            if (Math.abs(blockX - x) < 0.5 && Math.abs(blockY - y) < 0.5) {
                return block;
            }
        }
        
        return null;
    }

    /**
     * Calculate fallback position using page image as reference.
     * Used when OCR block element is not found.
     * 
     * @param {number} x - X coordinate in original image pixels
     * @param {number} y - Y coordinate in original image pixels
     * @param {number} width - Width of block
     * @param {number} height - Height of block
     * @param {ZoomController} zoomController - Zoom controller for scale
     * @returns {Object} Object with blockX, blockY, blockWidth, blockHeight
     * @private
     */
    _calculateFallbackPosition(x, y, width, height, zoomController) {
        const pageImages = document.querySelectorAll('.page-image');
        if (pageImages.length === 0) {
            return { blockX: 0, blockY: 0, blockWidth: 0, blockHeight: 0 };
        }
        
        const pageImage = pageImages[0];
        const pageRect = pageImage.getBoundingClientRect();
        const viewportRect = this.viewportEl.getBoundingClientRect();
        
        const zoomScale = zoomController.getScale();
        const imageX = pageRect.left - viewportRect.left;
        const imageY = pageRect.top - viewportRect.top;
        
        const screenX = imageX + (x * zoomScale);
        const screenY = imageY + (y * zoomScale);
        const screenWidth = width * zoomScale;
        const screenHeight = height * zoomScale;
        
        return {
            blockX: screenX,
            blockY: screenY,
            blockWidth: screenWidth,
            blockHeight: screenHeight
        };
    }

    /**
     * Draw the highlight rectangle on a canvas overlay with padding.
     * 
     * @param {number} x - X position in viewport
     * @param {number} y - Y position in viewport
     * @param {number} width - Width of rectangle
     * @param {number} height - Height of rectangle
     * @private
     */
    _drawHighlight(x, y, width, height) {
        // Create canvas overlay for drawing the highlight
        const canvas = document.createElement('canvas');
        canvas.id = 'block-highlight-overlay';
        canvas.style.position = 'absolute';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.pointerEvents = 'none';
        canvas.style.zIndex = '1000';

        // Set canvas dimensions to viewport size
        canvas.width = this.viewportEl.clientWidth;
        canvas.height = this.viewportEl.clientHeight;

        // Apply padding around the highlight
        const paddedX = x - this.highlightPadding;
        const paddedY = y - this.highlightPadding;
        const paddedWidth = width + (this.highlightPadding * 2);
        const paddedHeight = height + (this.highlightPadding * 2);

        // Draw the highlight rectangle
        const ctx = canvas.getContext('2d');
        if (ctx) {
            // Red rectangle with semi-transparent fill
            ctx.fillStyle = 'rgba(255, 0, 0, 0.15)';
            ctx.fillRect(paddedX, paddedY, paddedWidth, paddedHeight);

            // Red border
            ctx.strokeStyle = 'rgb(255, 0, 0)';
            ctx.lineWidth = 3;
            ctx.strokeRect(paddedX, paddedY, paddedWidth, paddedHeight);
        }

        // Append canvas to viewport
        this.viewportEl.appendChild(canvas);

        // Auto-remove highlight after 5 seconds
        this._scheduleHighlightRemoval();
    }

    /**
     * Schedule the highlight to fade out and be removed after 2 seconds.
     * 
     * @private
     */
    _scheduleHighlightRemoval() {
        setTimeout(() => {
            const highlight = document.getElementById('block-highlight-overlay');
            if (highlight) {
                highlight.style.opacity = '0';
                highlight.style.transition = 'opacity 0.3s ease-out';
                setTimeout(() => highlight.remove(), 300);
            }
        }, 2000);
    }

    /**
     * Clear any previous highlight overlays.
     * 
     * @private
     */
    _clearPreviousHighlight() {
        const existingHighlight = document.getElementById('block-highlight-overlay');
        if (existingHighlight) {
            existingHighlight.remove();
        }
    }
}
