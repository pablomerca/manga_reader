/**
 * ChannelBridge Module
 * 
 * Wraps QWebChannel initialization and provides clean API for Python communication.
 * Handles connection lifecycle and provides methods to send messages to Python.
 */
export class ChannelBridge {
    constructor() {
        this.connector = null;
        this.isConnected = false;
        this.onConnectedCallback = null;
    }

    /**
     * Initialize QWebChannel connection.
     * 
     * @param {Function} onConnected - Callback when connection is established
     */
    initialize(onConnected) {
        this.onConnectedCallback = onConnected;

        if (typeof qt !== "undefined" && qt.webChannelTransport) {
            new QWebChannel(qt.webChannelTransport, (channel) => {
                console.log("QWebChannel connected.");
                this.connector = channel.objects.connector;
                
                if (!this.connector) {
                    console.error("Connector object not found in WebChannel objects:", channel.objects);
                    return;
                }
                
                console.log("Bridge object found:", this.connector);
                
                // Validate that all required methods are present and are functions
                const requiredMethods = [
                    'requestWordLookup',
                    'requestNavigation',
                    'blockClicked',
                    'trackWord',
                    'viewWordContext'
                ];
                
                for (const method of requiredMethods) {
                    if (typeof this.connector[method] !== 'function') {
                        throw new Error(`Bridge connector missing required method: ${method}`);
                    }
                }
                
                console.log("All required bridge methods validated.");
                this.isConnected = true;
                
                if (this.onConnectedCallback) {
                    this.onConnectedCallback(this.connector);
                }
            });
        } else {
            console.error("Qt WebChannel not found! Ensure this is running inside QWebEngineView.");
        }
    }

    /**
     * Request word lookup from Python.
     * 
     * @param {string} lemma - Word lemma form
     * @param {string} surface - Surface form of word
     * @param {number} x - Click X coordinate
     * @param {number} y - Click Y coordinate
     */
    requestWordLookup(lemma, surface, x, y, pageIndex, blockId) {
        this.connector.requestWordLookup(lemma, surface, x, y, pageIndex, blockId, () => {});
    }

    /**
     * Request page navigation from Python.
     * 
     * @param {string} direction - Navigation direction ("next" or "prev")
     */
    requestNavigation(direction) {
        this.connector.requestNavigation(direction, () => {});
    }

    /**
     * Notify Python that a block was clicked.
     * 
     * @param {string} blockId - Block identifier
     */
    blockClicked(blockId, pageIndex) {
        this.connector.blockClicked(blockId, pageIndex, () => {});
    }

    /**
     * Track word in vocabulary database.
     * 
     * @param {string} lemma - Dictionary base form
     * @param {string} reading - Kana reading
     * @param {string} partOfSpeech - Part of speech tag
     */
    trackWord(lemma, reading, partOfSpeech) {
        this.connector.trackWord(lemma, reading, partOfSpeech, () => {});
    }

    /**
     * View context (appearances) of a tracked word.
     * 
     * @param {string} lemma - Dictionary base form
     */
    viewWordContext(lemma) {
        this.connector.viewWordContext(lemma, () => {});
    }

    /**
     * Get the raw connector object for custom operations.
     * 
     * @returns {Object|null} The QWebChannel connector object
     */
    getConnector() {
        return this.connector;
    }

    /**
     * Check if the channel is connected.
     * 
     * @returns {boolean} True if connected
     */
    connected() {
        return this.isConnected;
    }
}
