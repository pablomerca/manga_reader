/**
 * TextFormatter Module
 * 
 * Pure utility functions for text processing, HTML escaping, and word wrapping.
 * No dependencies on DOM, Qt, or other viewer components.
 */
export class TextFormatter {
    /**
     * Wraps word tokens in HTML spans for highlighting and interaction.
     * Works with text and a list of word objects containing start/end offsets.
     * 
     * @param {string} text - The full text to process
     * @param {Array} words - Array of {surface, lemma, start, end} objects
     * @returns {string} HTML string with word spans
     */
    wrapWordsInText(text, words) {
        if (!words || words.length === 0) {
            return this.escapeHtml(text);
        }

        // Sort words by start offset
        const sortedWords = [...words].sort((a, b) => a.start - b.start);

        let result = "";
        let lastIndex = 0;

        for (const word of sortedWords) {
            // Add text before the word
            if (word.start > lastIndex) {
                result += this.escapeHtml(text.substring(lastIndex, word.start));
            }

            // Add the word with span
            const wordText = text.substring(word.start, word.end);
            const escapedLemma = this.escapeAttr(word.lemma);
            const pos = word.pos || "unknown";
            const posClass = `word--${pos.toLowerCase()}`;
            const escapedPos = this.escapeAttr(pos);
            result += `<span class="word ${posClass}" data-lemma="${escapedLemma}" data-pos="${escapedPos}">${this.escapeHtml(wordText)}</span>`;

            lastIndex = word.end;
        }

        // Add remaining text
        if (lastIndex < text.length) {
            result += this.escapeHtml(text.substring(lastIndex));
        }

        return result;
    }

    /**
     * Escapes HTML special characters to prevent XSS.
     * 
     * @param {string} text - Text to escape
     * @returns {string} Escaped text safe for HTML content
     */
    escapeHtml(text) {
        const map = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;",
        };
        return text.replace(/[&<>"']/g, (m) => map[m]);
    }

    /**
     * Escapes HTML attribute values.
     * 
     * @param {string} text - Text to escape
     * @returns {string} Escaped text safe for HTML attributes
     */
    escapeAttr(text) {
        return text.replace(/"/g, "&quot;");
    }
}
