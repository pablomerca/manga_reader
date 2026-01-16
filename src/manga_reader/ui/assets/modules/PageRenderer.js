/**
 * PageRenderer Module
 * 
 * Creates DOM elements for pages, OCR blocks, and text lines.
 * Depends on TextFormatter for word wrapping.
 */
export class PageRenderer {
    constructor(textFormatter, bridge) {
        if (!bridge) {
            throw new Error("PageRenderer requires a QWebChannel bridge");
        }
        this.textFormatter = textFormatter;
        this.bridge = bridge;
    }

    /**
     * Create a page container element with image and OCR blocks.
     * 
     * @param {Object} pageData - Page data with width, height, imageUrl, blocks
     * @returns {HTMLElement} Page container element
     */
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

    /**
     * Create an OCR block element with text lines.
     * 
     * @param {Object} block - Block data with position, dimensions, lines, words
     * @returns {HTMLElement} Block element
     */
    createBlockElement(block) {
        const el = document.createElement("div");
        el.className = "ocr-block";
        el.dataset.blockId = String(block.id);
        el.style.left = block.x + "px";
        el.style.top = block.y + "px";
        el.style.width = block.width + "px";
        el.style.height = block.height + "px";

        // Attach click handler; bridge validated at construction
        el.onclick = () => {
            this.bridge.blockClicked(block.id, () => {});
        };

        if (block.lines) {
            // Process each line with adjusted word offsets
            let currentOffset = 0;
            
            block.lines.forEach((lineText) => {
                const lineEl = document.createElement("div");
                lineEl.className = "ocr-line";
                
                // Filter words that belong to this line
                const lineStart = currentOffset;
                const lineEnd = currentOffset + lineText.length;

                const lineWords = (block.words || [])
                    .filter(this.isWordInLineRange(lineEnd, lineStart))
                    .map(this.transformWordOffsets(lineStart, lineText));
                
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

    transformWordOffsets(lineStart, lineText) {
        return word => ({
            // Adjust offsets to be relative to this line
            surface: word.surface,
            lemma: word.lemma,
            pos: word.pos,
            isTracked: word.isTracked,
            start: Math.max(0, word.start - lineStart),
            end: Math.min(lineText.length, word.end - lineStart)
        });
    }

    isWordInLineRange(lineEnd, lineStart) {
        return word => {
            return word.start < lineEnd && word.end > lineStart;
        };
    }

    /**
     * Mark a lemma as tracked and update visual styling.
     * Updates all word spans with the given lemma to show tracked-word styling.
     * 
     * @param {string} lemma - The lemma to mark as tracked
     */
    markLemmaAsTracked(lemma) {
        // Ensure tracked lemmas array exists
        if (!window.trackedLemmas) {
            window.trackedLemmas = [];
        }
        
        // Add lemma to tracked set
        window.trackedLemmas.push(lemma);
        
        // Update all word spans with this lemma to show tracked style
        document.querySelectorAll(`[data-lemma="${lemma}"]`).forEach(el => {
            el.classList.add('tracked-word');
        });
    }
}
