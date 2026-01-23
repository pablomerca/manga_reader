/**
 * EventRouter Module
 * 
 * Handles all event binding and delegation for the manga viewer.
 * Routes events to appropriate callback handlers provided by the coordinator.
 */
export class EventRouter {
    constructor(viewportEl, callbacks) {
        this.viewportEl = viewportEl;
        this.callbacks = callbacks;
    }

    /**
     * Bind all event listeners.
     * Call this once during setup.
     */
    bindAll() {
        // Window resize for layout recomputation
        window.addEventListener("resize", () => {
            if (this.callbacks.onResize) {
                this.callbacks.onResize();
            }
        });

        // Global click for closing popup
        window.addEventListener("click", (e) => {
            if (this.callbacks.onGlobalClick) {
                this.callbacks.onGlobalClick(e);
            }
        });

        if (this.viewportEl) {
            // Zoom with mouse wheel
            this.viewportEl.addEventListener("wheel", (e) => {
                if (this.callbacks.onWheelZoom) {
                    this.callbacks.onWheelZoom(e);
                }
            }, { passive: false });

            // Pan gestures
            this.viewportEl.addEventListener("mousedown", (e) => {
                if (this.callbacks.onPanStart) {
                    this.callbacks.onPanStart(e);
                }
            });

            this.viewportEl.addEventListener("mousemove", (e) => {
                if (this.callbacks.onPanMove) {
                    this.callbacks.onPanMove(e);
                }
            });

            this.viewportEl.addEventListener("mouseup", () => {
                if (this.callbacks.onPanEnd) {
                    this.callbacks.onPanEnd();
                }
            });

            this.viewportEl.addEventListener("mouseleave", () => {
                if (this.callbacks.onPanEnd) {
                    this.callbacks.onPanEnd();
                }
            });

            // Word clicks for dictionary lookup (capture phase to stop block click bubbling)
            this.viewportEl.addEventListener("click", (e) => {
                // Intercept word clicks before they reach block handlers
                if (e.target && e.target.classList && e.target.classList.contains("word")) {
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    if (this.callbacks.onWordClick) {
                        this.callbacks.onWordClick(e);
                    }
                    return;
                }
                // Non-word clicks can bubble normally
            }, { capture: true });
        }

        // Keyboard navigation
        const navHandler = (event) => {
            if (this.callbacks.onKeydown) {
                this.callbacks.onKeydown(event);
            }
        };

        window.addEventListener("keydown", navHandler, { passive: false });
        document.addEventListener("keydown", navHandler, { passive: false, capture: true });
        if (document.body) {
            document.body.addEventListener("keydown", navHandler, { passive: false, capture: true });
        }
    }

    /**
     * Update callbacks dynamically if needed.
     * 
     * @param {Object} newCallbacks - New callback functions
     */
    updateCallbacks(newCallbacks) {
        this.callbacks = { ...this.callbacks, ...newCallbacks };
    }
}
