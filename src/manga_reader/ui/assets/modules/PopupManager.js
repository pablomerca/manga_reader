/**
 * PopupManager Module
 * 
 * Manages dictionary popup lifecycle, content generation, and positioning.
 * Depends on TextFormatter for HTML escaping.
 */
export class PopupManager {
    constructor(containerEl, textFormatter) {
        this.containerEl = containerEl;
        this.textFormatter = textFormatter;
        this.popupEl = null;
    }

    /**
     * Show dictionary popup with definition data.
     * 
     * @param {Object} payload - Popup data (surface, reading, senses, mouseX, mouseY, notFound)
     */
    show(payload) {
        if (!payload || !this.containerEl) return;

        // Remove existing popup if any
        this.hide();

        const popup = this.createPopupElement(payload);
        this.positionPopup(popup, payload.mouseX || 0, payload.mouseY || 0);
        
        this.containerEl.appendChild(popup);
        this.popupEl = popup;
    }

    /**
     * Hide and remove the popup.
     */
    hide() {
        if (!this.popupEl) return;
        this.popupEl.remove();
        this.popupEl = null;
    }

    /**
     * Check if popup is currently visible.
     * 
     * @returns {boolean} True if popup is visible
     */
    isVisible() {
        return this.popupEl !== null;
    }

    /**
     * Check if an element is inside the popup.
     * 
     * @param {HTMLElement} element - Element to check
     * @returns {boolean} True if element is inside popup
     */
    contains(element) {
        return this.popupEl && this.popupEl.contains(element);
    }

    /**
     * Create popup element with dictionary content.
     * 
     * @param {Object} payload - Popup data
     * @returns {HTMLElement} Popup element
     * @private
     */
    createPopupElement(payload) {
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
                    const glosses = Array.isArray(sense.glosses) 
                        ? sense.glosses.map((g) => this.textFormatter.escapeHtml(g)).join("; ") 
                        : "";
                    const pos = Array.isArray(sense.pos) ? sense.pos.filter(Boolean).join(", ") : "";
                    const posPart = pos ? `<span class="dict-pos">${this.textFormatter.escapeHtml(pos)}</span>` : "";
                    return `<div class="dict-sense"><div class="dict-sense-title">${idx + 1}${posPart ? " · " + posPart : ""}</div><div class="dict-gloss">${glosses}</div></div>`;
                })
                .join("");
        } else {
            sensesHtml = `<div class="dict-empty">No definition found.</div>`;
        }

        popup.innerHTML = `${header}<div class="dict-body">${sensesHtml}</div>`;
        return popup;
    }

    /**
     * Position popup relative to anchor coordinates.
     * 
     * @param {HTMLElement} popup - Popup element to position
     * @param {number} anchorX - Anchor X coordinate
     * @param {number} anchorY - Anchor Y coordinate
     * @private
     */
    positionPopup(popup, anchorX, anchorY) {
        if (!this.containerEl) return;

        const popupWidth = 360;
        const popupHeight = 240;
        const viewportRect = this.containerEl.getBoundingClientRect();
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
    }

    /**
     * Clamp a value between min and max.
     * 
     * @param {number} value - Value to clamp
     * @param {number} min - Minimum value
     * @param {number} max - Maximum value
     * @returns {number} Clamped value
     * @private
     */
    clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }
}
