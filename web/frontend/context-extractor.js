/**
 * Context extraction functions for nvim-lookup web app
 * Mimics the logic from books/selection-grep.vim lines 131-208
 */

/**
 * Extract sentence containing cursor position from paragraph text
 * Mimics s:GetCurrentSentence() from selection-grep.vim lines 131-185
 *
 * @param {string} paragraphText - The full paragraph text (lines joined with spaces)
 * @param {number} cursorOffset - Cursor position within the paragraph text
 * @returns {string} The sentence containing the cursor
 */
function extractSentence(paragraphText, cursorOffset) {
    if (!paragraphText || paragraphText.length === 0) {
        return '';
    }

    // Clamp cursor offset to valid range
    cursorOffset = Math.max(0, Math.min(cursorOffset, paragraphText.length - 1));

    let sentenceStart = 0;
    let sentenceEnd = paragraphText.length;

    // Search backwards for . ! ? followed by whitespace (or end of string)
    for (let i = cursorOffset - 1; i >= 0; i--) {
        if (/[.!?]/.test(paragraphText[i])) {
            // Check if followed by whitespace or end of string
            if (i + 1 >= paragraphText.length || /\s/.test(paragraphText[i + 1])) {
                sentenceStart = i + 1;
                break;
            }
        }
    }

    // Search forwards for . ! ? followed by whitespace (or end of string)
    for (let i = cursorOffset; i < paragraphText.length; i++) {
        if (/[.!?]/.test(paragraphText[i])) {
            // Check if followed by whitespace or end of string
            if (i + 1 >= paragraphText.length || /\s/.test(paragraphText[i + 1])) {
                sentenceEnd = i + 1;
                break;
            }
        }
    }

    // Skip leading whitespace
    while (sentenceStart < paragraphText.length && /\s/.test(paragraphText[sentenceStart])) {
        sentenceStart++;
    }

    // Extract and normalize whitespace
    let sentence = paragraphText.substring(sentenceStart, sentenceEnd);
    return sentence.replace(/\s+/g, ' ').trim();
}

/**
 * Extract paragraph from a simple text string (single "line")
 * Used when text is already a single paragraph
 *
 * @param {string} text - The text
 * @returns {string} Normalized paragraph text
 */
function extractParagraph(text) {
    if (!text) return '';
    return text.replace(/\s+/g, ' ').trim();
}

/**
 * Extract paragraph containing the given line from an editor-like object
 * Mimics s:GetCurrentParagraph() from selection-grep.vim lines 188-208
 *
 * @param {Object} editor - Editor object with getLine(n) and lineCount() methods
 * @param {number} lineIndex - Current line index (0-based)
 * @returns {string} The paragraph text with lines joined by spaces
 */
function extractParagraphFromEditor(editor, lineIndex) {
    // Find start of paragraph (search backwards until blank line)
    let startLine = lineIndex;
    while (startLine > 0) {
        const prevLine = editor.getLine(startLine - 1);
        if (!prevLine || prevLine.trim() === '') {
            break;
        }
        startLine--;
    }

    // Find end of paragraph (search forwards until blank line)
    let endLine = lineIndex;
    const lastLine = editor.lineCount() - 1;
    while (endLine < lastLine) {
        const nextLine = editor.getLine(endLine + 1);
        if (!nextLine || nextLine.trim() === '') {
            break;
        }
        endLine++;
    }

    // Join lines with spaces
    const lines = [];
    for (let i = startLine; i <= endLine; i++) {
        const line = editor.getLine(i);
        if (line) {
            lines.push(line);
        }
    }

    const paragraph = lines.join(' ');
    return paragraph.replace(/\s+/g, ' ').trim();
}

/**
 * Calculate cursor offset within paragraph text
 *
 * @param {Object} editor - Editor object with getLine(n) method
 * @param {number} cursorLine - Current cursor line (0-based)
 * @param {number} cursorCh - Current cursor character position
 * @param {number} paragraphStartLine - Line where paragraph starts
 * @returns {number} Offset of cursor within the joined paragraph text
 */
function calculateCursorOffsetInParagraph(editor, cursorLine, cursorCh, paragraphStartLine) {
    let offset = 0;

    // Add length of each line before cursor line (plus 1 for the space that joins them)
    for (let i = paragraphStartLine; i < cursorLine; i++) {
        const line = editor.getLine(i);
        offset += (line ? line.length : 0) + 1; // +1 for space between lines
    }

    // Add cursor position within current line
    offset += cursorCh;

    return offset;
}

/**
 * Get paragraph start line
 *
 * @param {Object} editor - Editor object
 * @param {number} lineIndex - Current line
 * @returns {number} Start line of paragraph
 */
function getParagraphStartLine(editor, lineIndex) {
    let startLine = lineIndex;
    while (startLine > 0) {
        const prevLine = editor.getLine(startLine - 1);
        if (!prevLine || prevLine.trim() === '') {
            break;
        }
        startLine--;
    }
    return startLine;
}

/**
 * Get sentence at cursor position in CodeMirror editor
 *
 * @param {Object} editor - CodeMirror editor instance
 * @param {Object} cursor - Cursor position {line, ch}
 * @returns {string} The sentence containing the cursor
 */
function getSentenceAtCursor(editor, cursor) {
    // Get the full paragraph containing the cursor
    const paragraph = extractParagraphFromEditor(editor, cursor.line);

    // Calculate cursor offset within the paragraph
    const paragraphStart = getParagraphStartLine(editor, cursor.line);
    const cursorOffset = calculateCursorOffsetInParagraph(editor, cursor.line, cursor.ch, paragraphStart);

    // Extract the sentence
    return extractSentence(paragraph, cursorOffset);
}

// Export for use in app.js (works in browser without module system)
if (typeof window !== 'undefined') {
    window.extractSentence = extractSentence;
    window.extractParagraph = extractParagraph;
    window.extractParagraphFromEditor = extractParagraphFromEditor;
    window.getSentenceAtCursor = getSentenceAtCursor;
    window.calculateCursorOffsetInParagraph = calculateCursorOffsetInParagraph;
    window.getParagraphStartLine = getParagraphStartLine;
}
