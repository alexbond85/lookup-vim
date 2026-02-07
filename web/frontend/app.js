// API base URL - use localhost:2989 when running in Tauri (static files), empty for dev server
const API_BASE = window.__TAURI__ ? 'http://localhost:2989' : '';

// Session ID for conversation continuity - persist across page reloads
const SESSION_ID = localStorage.getItem('sessionId') || crypto.randomUUID();
localStorage.setItem('sessionId', SESSION_ID);

// State
let currentFile = null;
let highlights = [];
let editor = null;
let currentMessages = []; // Store current messages for conversation
let lastFromCache = false; // Track if last translation was from cache
let pendingSelection = null; // Store selection range for highlighting after translate

// Viewer instances (initialized in DOMContentLoaded)
let textViewer, pdfIframeViewer, pdfJsViewer, pdfViewer, activeViewer;

// Input field state management
// 'translate' - initial state or after editing selection, translates text
// 'followup' - after translation, for follow-up questions
// 'selection' - vim visual mode active, shows live selection
let inputMode = 'translate';
let isSelectionModified = false; // Track if user edited the selection text
let originalSelectionText = ''; // Original selection before user edits
let isTranslatingFromVisualMode = false; // Flag to prevent cursorActivity interference

// App settings (loaded from disk)
let appSettings = {};

// --- Viewer classes ---

class TextViewer {
    constructor() {
        const textarea = document.getElementById('editor');

        // Load saved theme from appSettings (disk-persisted)
        const savedTheme = appSettings.editorTheme || 'default';
        console.log('TextViewer - loading theme:', savedTheme);

        // Load saved split position from appSettings
        const savedSplit = appSettings.splitPosition || '65';
        const editorPane = document.getElementById('editor-pane');
        const chatPane = document.getElementById('chat-pane');
        editorPane.style.flex = `0 0 ${savedSplit}%`;
        chatPane.style.flex = '1';

        this.cm = CodeMirror.fromTextArea(textarea, {
            mode: 'markdown',
            lineNumbers: true,
            lineWrapping: true,
            keyMap: 'vim',
            theme: savedTheme
        });

        // Set global editor for backward compat
        editor = this.cm;

        // Update theme options to show active
        updateThemeOptions(savedTheme);

        // Track vim mode changes
        this.cm.on('vim-mode-change', function(e) {
            const mode = e.mode || 'normal';
            document.getElementById('vim-mode').textContent = mode.toUpperCase();
        });

        // Set up custom translate command in vim - just type :t in vim!
        CodeMirror.Vim.defineEx('translate', 't', function(cm) {
            console.log('Translate ex command triggered!');
            handleLookup();
        });

        // Also create :tr alias
        CodeMirror.Vim.defineEx('tr', 'tr', function(cm) {
            console.log('Translate :tr command triggered!');
            handleLookup();
        });

        // Map Enter key in visual mode to trigger translation
        CodeMirror.Vim.mapCommand('<CR>', 'action', 'translateSelection', {}, {
            context: 'visual'
        });

        // Define the translate action for visual mode
        CodeMirror.Vim.defineAction('translateSelection', function(cm) {
            // Get the selection text and range BEFORE exiting visual mode
            const selection = cm.getSelection();

            if (selection && selection.trim()) {
                // Set flag to prevent cursorActivity from interfering
                isTranslatingFromVisualMode = true;

                // Use listSelections() to get the selection range
                const selections = cm.listSelections();
                let from, to;
                if (selections.length > 0) {
                    const range = selections[0];
                    from = range.anchor;
                    to = range.head;

                    // Normalize order (make from < to)
                    if (from.line > to.line || (from.line === to.line && from.ch > to.ch)) {
                        [from, to] = [to, from];
                    }
                    // CodeMirror's vim mode already returns exclusive end position
                }

                const cursorPos = cm.getCursor('head');

                // Clear any pending selection and input state
                pendingSelection = null;
                inputMode = 'translate';

                // Clear the chat input (it shows the selection preview)
                const chatInput = document.getElementById('chat-input');
                chatInput.value = '';
                chatInput.classList.remove('has-selection');

                // Exit visual mode back to normal
                CodeMirror.Vim.exitVisualMode(cm);

                // Trigger translation with the selection and accurate range
                translateFromInputWithRefocus(selection, cursorPos, from, to);
            } else {
                // No selection, just exit visual mode
                CodeMirror.Vim.exitVisualMode(cm);
            }
        });

        console.log('Translate: select text (vim or mouse) then press Enter');

        // Handle clicks on highlights
        this.cm.getWrapperElement().addEventListener('click', function(e) {
            // Check if clicked element is a highlight
            if (e.target.classList.contains('highlight-mark')) {
                const text = e.target.textContent;
                if (text && text.trim()) {
                    console.log('Highlight clicked:', text);
                    translateHighlightedText(text.trim());
                }
            }
        });

        // Track mouse selection - when user releases mouse after selecting
        this.cm.getWrapperElement().addEventListener('mouseup', function() {
            // Small delay to let selection settle
            setTimeout(function() {
                const vimState = editor.state.vim;
                // Only handle if NOT in vim visual mode (mouse selection)
                if (!vimState || !vimState.visualMode) {
                    const selection = editor.getSelection();
                    if (selection && selection.trim()) {
                        updateSelectionPreview(selection);
                    }
                }
            }, 10);
        });

        // Handle Enter key for mouse selections (non-vim)
        this.cm.getWrapperElement().addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                const vimState = editor.state.vim;
                // Only intercept if NOT in vim visual mode and has selection
                if (!vimState || !vimState.visualMode) {
                    const selection = editor.getSelection();
                    if (selection && selection.trim()) {
                        e.preventDefault();
                        e.stopPropagation();

                        // Get cursor position for context
                        const cursorPos = editor.getCursor('start');

                        // Get selection range
                        const selections = editor.listSelections();
                        let from, to;
                        if (selections.length > 0) {
                            const range = selections[0];
                            from = range.anchor;
                            to = range.head;
                            if (from.line > to.line || (from.line === to.line && from.ch > to.ch)) {
                                [from, to] = [to, from];
                            }
                        }

                        // Clear selection in editor
                        editor.setCursor(cursorPos);

                        // Clear input state
                        const chatInput = document.getElementById('chat-input');
                        chatInput.value = '';
                        chatInput.classList.remove('has-selection');
                        pendingSelection = null;
                        inputMode = 'translate';

                        // Translate
                        translateFromInputWithRefocus(selection, cursorPos, from, to);
                    }
                }
            }
        });

        // Track vim selection in real-time for live preview
        this.cm.on('cursorActivity', function() {
            // Skip if we're in the middle of a visual mode translation
            if (isTranslatingFromVisualMode) {
                return;
            }

            const vimState = editor.state.vim;
            if (vimState && vimState.visualMode) {
                // Get selection in visual mode
                const start = editor.getCursor('anchor');
                const end = editor.getCursor('head');
                const selection = editor.getRange(start, end);
                if (selection && selection.trim()) {
                    updateSelectionPreview(selection);
                }
            } else {
                // Check for mouse selection
                const selection = editor.getSelection();
                if (selection && selection.trim()) {
                    // Keep showing preview for mouse selection
                } else {
                    clearSelectionPreview();
                }
            }

            // Save cursor position (debounced via the periodic save)
            saveCursorPosition();
        });

        // Save state before page unload
        window.addEventListener('beforeunload', function() {
            saveFileState();
        });

        console.log('Editor initialized with vim mode and theme:', savedTheme);
    }

    show() {
        const editorPane = document.getElementById('editor-pane');
        editorPane.classList.remove('pdf-mode', 'pdf-js');
        document.getElementById('vim-mode').style.display = '';

        // Clear PDF viewer
        if (pdfViewer && pdfViewer.hide) pdfViewer.hide();

        // Restore chat placeholder
        const chatInput = document.getElementById('chat-input');
        if (inputMode !== 'followup') {
            chatInput.placeholder = 'Enter text to translate...';
        }

        // Refresh CodeMirror to handle display change
        this.cm.refresh();
    }

    hide() {
        // no-op: CodeMirror stays in DOM, hidden via CSS pdf-mode class
    }

    load(filename, data) {
        this.show();
        this.cm.setValue(data);
        loadHighlightsForFile(filename, data);
    }

    getTypeKey() {
        return 'text';
    }

    getSaveState() {
        const content = this.cm.getValue();
        return {
            content: content.length < 5 * 1024 * 1024 ? content : null,
            cursor: this.cm.getCursor()
        };
    }

    restoreState(state) {
        if (state.content) {
            this.cm.setValue(state.content);
        }
        if (state.cursor) {
            try {
                this.cm.setCursor(state.cursor);
                this.cm.scrollIntoView(state.cursor, 100);
            } catch (e) {
                console.error('Error restoring cursor:', e);
            }
        }
    }

    getRecentFileEntry(filename) {
        return {
            name: filename,
            timestamp: Date.now(),
            content: this.cm.getValue()
        };
    }

    canRestoreFromRecent(entry) {
        return !!entry.content;
    }

    loadFromRecent(entry) {
        this.load(entry.name, entry.content);
    }
}

class PdfIframeViewer {
    constructor() {
        this.iframe = document.getElementById('pdf-viewer');
    }

    show() {
        const editorPane = document.getElementById('editor-pane');
        editorPane.classList.add('pdf-mode');
        editorPane.classList.remove('pdf-js');
        document.getElementById('vim-mode').style.display = 'none';

        // Update chat placeholder for PDF mode
        const chatInput = document.getElementById('chat-input');
        if (inputMode !== 'followup') {
            chatInput.placeholder = 'Type or paste text to translate...';
        }
    }

    hide() {
        if (this.iframe.src && this.iframe.src.startsWith('blob:')) {
            URL.revokeObjectURL(this.iframe.src);
        }
        this.iframe.removeAttribute('src');
    }

    load(filename, data) {
        // data is an ArrayBuffer
        const blob = new Blob([data], { type: 'application/pdf' });
        const blobUrl = URL.createObjectURL(blob);

        if (this.iframe.src && this.iframe.src.startsWith('blob:')) {
            URL.revokeObjectURL(this.iframe.src);
        }
        this.iframe.src = blobUrl;
        this.show();
    }

    getTypeKey() {
        return 'pdf';
    }

    getSaveState() {
        return { content: null, cursor: null };
    }

    restoreState() {
        // no-op: PDF content not persisted
    }

    getRecentFileEntry(filename) {
        return {
            name: filename,
            timestamp: Date.now(),
            type: 'pdf'
        };
    }

    canRestoreFromRecent(entry) {
        return false;
    }

    loadFromRecent() {
        // no-op
    }
}

class PdfJsViewer {
    constructor() {
        this.container = document.getElementById('pdf-js-viewer');
        this.pagesEl = document.getElementById('pdf-pages');
        this.pdfDoc = null;
        this._currentFilename = null;
        this._currentData = null;
        this._renderInProgress = false;
        this._currentPage = 1;

        // Nav elements
        this._pageInput = document.getElementById('pdf-page-input');
        this._pageTotal = document.getElementById('pdf-page-total');
        this._prevBtn = document.getElementById('pdf-prev');
        this._nextBtn = document.getElementById('pdf-next');

        // Set PDF.js worker
        if (typeof pdfjsLib !== 'undefined') {
            pdfjsLib.GlobalWorkerOptions.workerSrc =
                'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        }

        this._setupSelectionListeners();
        this._setupResizeObserver();
        this._setupPageNav();
    }

    _setupSelectionListeners() {
        this.container.addEventListener('mouseup', () => {
            const sel = window.getSelection();
            const text = sel ? sel.toString().trim() : '';
            if (!text) return;

            const chatInput = document.getElementById('chat-input');
            chatInput.value = text;
            chatInput.classList.add('has-selection');
            chatInput.placeholder = 'Selected text...';

            inputMode = 'selection';
            isSelectionModified = false;
            originalSelectionText = text;

            pendingSelection = { from: null, to: null, text: text };

            updateSendButton();
            autoResizeTextarea(chatInput);
        });
    }

    _setupResizeObserver() {
        this._resizeObserver = new ResizeObserver(() => {
            if (this.pdfDoc && !this._renderInProgress) {
                this._renderAllPages();
            }
        });
        this._resizeObserver.observe(this.container);
    }

    _setupPageNav() {
        // Prev / Next buttons
        this._prevBtn.addEventListener('click', () => this._goToPage(this._currentPage - 1));
        this._nextBtn.addEventListener('click', () => this._goToPage(this._currentPage + 1));

        // Jump to page on Enter in input
        this._pageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const num = parseInt(this._pageInput.value, 10);
                if (num >= 1 && this.pdfDoc && num <= this.pdfDoc.numPages) {
                    this._goToPage(num);
                } else {
                    this._pageInput.value = this._currentPage;
                }
            }
        });

        // Also accept blur to jump
        this._pageInput.addEventListener('blur', () => {
            const num = parseInt(this._pageInput.value, 10);
            if (num >= 1 && this.pdfDoc && num <= this.pdfDoc.numPages) {
                this._goToPage(num);
            } else {
                this._pageInput.value = this._currentPage;
            }
        });

        // Track scroll to update current page indicator
        this.container.addEventListener('scroll', () => {
            if (!this.pdfDoc) return;
            const pages = this.pagesEl.children;
            if (pages.length === 0) return;

            const scrollTop = this.container.scrollTop;
            const containerTop = this.pagesEl.offsetTop;
            let page = 1;

            for (let i = 0; i < pages.length; i++) {
                const pageTop = pages[i].offsetTop - containerTop;
                const pageBottom = pageTop + pages[i].offsetHeight;
                // Current page is the one whose top half is visible
                if (scrollTop >= pageTop - pages[i].offsetHeight / 2) {
                    page = i + 1;
                }
            }

            if (page !== this._currentPage) {
                this._currentPage = page;
                this._pageInput.value = page;
            }
        });
    }

    _goToPage(num) {
        if (!this.pdfDoc || num < 1 || num > this.pdfDoc.numPages) return;
        const pages = this.pagesEl.children;
        if (pages[num - 1]) {
            pages[num - 1].scrollIntoView({ behavior: 'smooth', block: 'start' });
            this._currentPage = num;
            this._pageInput.value = num;
        }
    }

    _updatePageNav() {
        if (this.pdfDoc) {
            this._pageTotal.textContent = this.pdfDoc.numPages;
            this._pageInput.value = 1;
            this._currentPage = 1;
        }
    }

    async load(filename, data) {
        this._currentFilename = filename;
        this._currentData = data;

        // Clean up previous document
        if (this.pdfDoc) {
            this.pdfDoc.destroy();
            this.pdfDoc = null;
        }
        this.pagesEl.innerHTML = '';

        this.show();

        try {
            const loadingTask = pdfjsLib.getDocument({ data: new Uint8Array(data) });
            this.pdfDoc = await loadingTask.promise;
            this._updatePageNav();
            await this._renderAllPages();
        } catch (e) {
            console.error('PDF.js load error:', e);
            this.pagesEl.innerHTML = '<div style="padding:20px;color:var(--fg-muted)">Error loading PDF</div>';
        }
    }

    async _renderAllPages() {
        if (!this.pdfDoc || this._renderInProgress) return;
        this._renderInProgress = true;

        this.pagesEl.innerHTML = '';

        const containerWidth = this.container.clientWidth - 2; // account for border

        try {
            for (let i = 1; i <= this.pdfDoc.numPages; i++) {
                await this._renderPage(i, containerWidth);
            }
        } catch (e) {
            console.error('PDF.js render error:', e);
        } finally {
            this._renderInProgress = false;
        }
    }

    async _renderPage(pageNum, containerWidth) {
        const page = await this.pdfDoc.getPage(pageNum);
        const unscaledViewport = page.getViewport({ scale: 1 });
        const scale = containerWidth / unscaledViewport.width;
        const viewport = page.getViewport({ scale });

        // Page wrapper
        const pageDiv = document.createElement('div');
        pageDiv.className = 'pdf-page';
        pageDiv.style.width = viewport.width + 'px';
        pageDiv.style.height = viewport.height + 'px';

        // Canvas
        const canvas = document.createElement('canvas');
        canvas.width = viewport.width * (window.devicePixelRatio || 1);
        canvas.height = viewport.height * (window.devicePixelRatio || 1);
        canvas.style.width = viewport.width + 'px';
        canvas.style.height = viewport.height + 'px';
        const ctx = canvas.getContext('2d');
        ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
        pageDiv.appendChild(canvas);

        // Render canvas
        await page.render({ canvasContext: ctx, viewport }).promise;

        // Text layer
        const textContent = await page.getTextContent();
        const textLayerDiv = document.createElement('div');
        textLayerDiv.className = 'textLayer';
        textLayerDiv.style.width = viewport.width + 'px';
        textLayerDiv.style.height = viewport.height + 'px';
        pageDiv.appendChild(textLayerDiv);

        pdfjsLib.renderTextLayer({
            textContentSource: textContent,
            container: textLayerDiv,
            viewport: viewport,
            textDivs: []
        });

        this.pagesEl.appendChild(pageDiv);
    }

    show() {
        const editorPane = document.getElementById('editor-pane');
        editorPane.classList.add('pdf-mode', 'pdf-js');
        document.getElementById('vim-mode').style.display = 'none';

        // Update chat placeholder for PDF mode
        const chatInput = document.getElementById('chat-input');
        if (inputMode !== 'followup') {
            chatInput.placeholder = 'Select text in PDF or type to translate...';
        }
    }

    hide() {
        if (this.pdfDoc) {
            this.pdfDoc.destroy();
            this.pdfDoc = null;
        }
        this.pagesEl.innerHTML = '';
        this._currentFilename = null;
        this._currentData = null;
    }

    getTypeKey() {
        return 'pdf';
    }

    getSaveState() {
        return { content: null, cursor: null };
    }

    restoreState() {
        // no-op: PDF content not persisted
    }

    getRecentFileEntry(filename) {
        return {
            name: filename,
            timestamp: Date.now(),
            type: 'pdf'
        };
    }

    canRestoreFromRecent(entry) {
        return false;
    }

    loadFromRecent() {
        // no-op
    }
}

// --- Routing ---

function getViewerForFile(filename) {
    if (filename.toLowerCase().endsWith('.pdf')) return pdfViewer;
    return textViewer;
}

function openFile(filename, data) {
    const newViewer = getViewerForFile(filename);
    if (activeViewer && activeViewer !== newViewer) activeViewer.hide();
    activeViewer = newViewer;
    currentFile = filename;
    document.getElementById('filename').textContent = filename;
    activeViewer.load(filename, data);
    addToRecentFiles(filename);
    saveFileState();
}

// Initialize viewers when DOM is ready
document.addEventListener('DOMContentLoaded', async function() {
    // Load settings from disk first
    await loadAppSettings();

    textViewer = new TextViewer();
    pdfIframeViewer = new PdfIframeViewer();
    pdfJsViewer = new PdfJsViewer();
    pdfViewer = (appSettings.pdfRenderer === 'iframe') ? pdfIframeViewer : pdfJsViewer;
    activeViewer = textViewer;

    setupEventListeners();
    setupResizeHandle();
    setupMenu();
    setupSettingsModal();
    setupHelpModal();
    loadSessionMessages();
    updateRecentFilesMenu();
    restoreLastFile();

    // Initialize whisper if enabled
    if (appSettings.enableVoiceInput && typeof window.initWhisper === 'function') {
        window.initWhisper();
    }
});

async function loadAppSettings() {
    try {
        const response = await fetch(API_BASE + '/api/settings');
        if (response.ok) {
            appSettings = await response.json();
            console.log('Loaded app settings:', appSettings);
        }
    } catch (error) {
        console.error('Error loading app settings:', error);
    }
}

async function saveAppSettings() {
    try {
        await fetch(API_BASE + '/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(appSettings)
        });
        console.log('Saved app settings');
    } catch (error) {
        console.error('Error saving app settings:', error);
    }
}

async function loadSessionMessages() {
    try {
        const response = await fetch(API_BASE + '/api/session/messages', {
            headers: { 'X-Session-ID': SESSION_ID }
        });
        if (!response.ok) return;

        const data = await response.json();
        if (data.messages && data.messages.length > 0) {
            currentMessages = data.messages;
            displayMessagesWithContext(data.messages, false, false, false);

            // Switch to follow-up mode since we have messages
            const input = document.getElementById('chat-input');
            inputMode = 'followup';
            input.placeholder = 'Ask a follow-up question...';
            updateSendButton();

            console.log('Loaded', data.messages.length, 'messages from session');
        }
    } catch (error) {
        console.error('Error loading session messages:', error);
    }
}

function restoreLastFile() {
    const savedFile = appSettings.lastFile;
    const savedContent = appSettings.lastFileContent;
    const savedCursor = appSettings.lastCursorPosition;
    const savedType = appSettings.lastFileType || 'text';

    console.log('Restore check - savedFile:', savedFile, 'type:', savedType);
    console.log('Restore check - savedContent length:', savedContent ? savedContent.length : 0);
    console.log('Restore check - savedCursor:', savedCursor);

    if (savedFile && savedType === 'text' && savedContent) {
        console.log('Restoring last file:', savedFile);
        currentFile = savedFile;
        activeViewer = textViewer;
        document.getElementById('filename').textContent = savedFile;

        textViewer.restoreState({ content: savedContent, cursor: savedCursor });

        // Load highlights for this file
        loadHighlightsForFile(savedFile, savedContent);
    } else if (savedFile && savedType === 'pdf') {
        // PDF content not persisted, just show filename
        currentFile = savedFile;
        document.getElementById('filename').textContent = savedFile + ' (re-open from disk)';
    }
}

/**
 * Load and apply highlights from the cache for the given file.
 *
 * HIGHLIGHT SYSTEM NOTES:
 * - Highlights are visual markers on translated text, created with editor.markText()
 * - Position calculation uses indexOf + posFromIndex for reliability (not vim positions)
 * - CRITICAL: Before adding a highlight during live translation, we must clear any
 *   existing marks in the range. Vim creates invisible cursor bookmark markers that
 *   cause CodeMirror to split our highlight into multiple DOM spans if not cleared.
 *   This manifests as hover showing "text minus last char" and "last char" separately.
 * - On page reload, marks are fresh so this isn't needed.
 * - Deduplication happens on load to handle legacy duplicate cache entries.
 */
async function loadHighlightsForFile(filename, content) {
    try {
        const response = await fetch(API_BASE + '/api/history?file=' + encodeURIComponent(filename));
        const data = await response.json();

        // Build highlights from cache entries
        const rawHighlights = data.entries
            .map(entry => {
                const pos = content.indexOf(entry.selection);
                if (pos >= 0) {
                    return {
                        from: editor.posFromIndex(pos),
                        to: editor.posFromIndex(pos + entry.selection.length),
                        selection: entry.selection
                    };
                }
                return null;
            })
            .filter(Boolean);

        // Deduplicate highlights by position (keep first/longest at each start position)
        const seen = new Map(); // key: "line:ch" -> highlight
        for (const h of rawHighlights) {
            const key = `${h.from.line}:${h.from.ch}`;
            const existing = seen.get(key);
            if (!existing) {
                seen.set(key, h);
            } else {
                // Keep the longer selection if same start position
                if (h.selection.length > existing.selection.length) {
                    seen.set(key, h);
                }
            }
        }
        highlights = Array.from(seen.values());

        // Apply highlights from cache.
        // Note: Unlike live translation, we don't need to clear marks here because
        // this runs on fresh editor content before vim creates any cursor bookmarks.
        highlights.forEach(h => {
            editor.markText(h.from, h.to, { className: 'highlight-mark' });
        });

        if (rawHighlights.length !== highlights.length) {
            console.log(`Loaded ${highlights.length} highlights (${rawHighlights.length - highlights.length} duplicates removed)`);
        } else {
            console.log(`Loaded ${highlights.length} highlights`);
        }
    } catch (error) {
        console.error('Error loading highlights:', error);
    }
}

function saveFileState() {
    if (currentFile && activeViewer) {
        const state = activeViewer.getSaveState();
        appSettings.lastFile = currentFile;
        appSettings.lastFileType = activeViewer.getTypeKey();
        appSettings.lastFileContent = state.content;
        appSettings.lastCursorPosition = state.cursor;
        saveAppSettings();
        console.log('Saving file state -', activeViewer.getTypeKey(), '- file:', currentFile);
    } else {
        console.log('saveFileState skipped - currentFile:', currentFile, 'activeViewer:', !!activeViewer);
    }
}

// Debounced cursor position save
let cursorSaveTimeout = null;
function saveCursorPosition() {
    if (cursorSaveTimeout) clearTimeout(cursorSaveTimeout);
    cursorSaveTimeout = setTimeout(function() {
        if (currentFile && editor) {
            appSettings.lastCursorPosition = editor.getCursor();
            saveAppSettings();
        }
    }, 1000); // Save after 1s of no cursor movement
}

// Selection preview functions for live selection UX
function updateSelectionPreview(text) {
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');

    if (text && text.trim()) {
        input.value = text;
        input.classList.add('has-selection');
        input.placeholder = 'Selected text...';

        // Set mode to selection, reset modified flag
        inputMode = 'selection';
        isSelectionModified = false;
        originalSelectionText = text;

        // Update button
        updateSendButton();

        // Store selection range for highlighting after translate
        pendingSelection = {
            from: editor.getCursor('anchor'),
            to: editor.getCursor('head'),
            text: text
        };

        // Auto-resize textarea
        autoResizeTextarea(input);
    }
}

function clearSelectionPreview() {
    const input = document.getElementById('chat-input');

    if (inputMode === 'selection') {
        input.value = '';
        input.classList.remove('has-selection');
        pendingSelection = null;
        isSelectionModified = false;
        originalSelectionText = '';

        // Switch to followup mode if we have translations, otherwise translate mode
        if (currentMessages.length > 0) {
            inputMode = 'followup';
            input.placeholder = 'Ask a follow-up question...';
        } else {
            inputMode = 'translate';
            input.placeholder = 'Enter text to translate...';
        }

        updateSendButton();
        autoResizeTextarea(input);
    }
}

// Update send button based on current mode
function updateSendButton() {
    const sendBtn = document.getElementById('send-btn');
    const input = document.getElementById('chat-input');
    const hasText = input.value.trim().length > 0;

    // Always show "Send", just toggle disabled state
    sendBtn.disabled = !hasText;
}

// Auto-resize textarea to fit content
function autoResizeTextarea(textarea) {
    // Reset height to auto to get correct scrollHeight
    textarea.style.height = 'auto';
    // Set height to scrollHeight, capped by max-height in CSS (32px min, 120px max)
    const newHeight = Math.max(32, Math.min(textarea.scrollHeight, 120));
    textarea.style.height = newHeight + 'px';
}

async function translateFromInput() {
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const text = input.value.trim();

    if (!text) return;

    // Show loading state
    const originalBtnText = sendBtn.textContent;
    sendBtn.textContent = 'Translating...';
    sendBtn.disabled = true;

    // Determine if we should include context
    // Only include context if in selection mode AND text wasn't modified
    let sentence = '';
    let paragraph = '';

    const useContext = (inputMode === 'selection' && !isSelectionModified);

    if (useContext && pendingSelection && pendingSelection.from) {
        try {
            const cursor = pendingSelection.from;
            sentence = getSentenceAtCursor(editor, cursor);
            paragraph = extractParagraphFromEditor(editor, cursor.line);
        } catch (e) {
            console.log('Could not get context:', e);
        }
    }

    // Prepare request data
    const requestData = {
        selection: text,
        phrase: useContext ? (sentence || "") : "",
        paragraph: useContext ? (paragraph || "") : "",
        file: currentFile || ""
    };


    // Call API
    try {
        const response = await fetch(API_BASE + '/api/lookup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': SESSION_ID
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const errorMsg = await parseErrorResponse(response);
            displayError(errorMsg);
            return;
        }

        const data = await response.json();


        // Add highlight if we have stored selection range and text wasn't modified
        // Skip if translating from visual mode (that path handles its own highlighting)
        if (pendingSelection && pendingSelection.from && !isSelectionModified && !isTranslatingFromVisualMode) {
            // Use indexOf approach for consistent behavior with reload
            const content = editor.getValue();
            const textIndex = content.indexOf(pendingSelection.text);
            if (textIndex >= 0) {
                const from = editor.posFromIndex(textIndex);
                const to = editor.posFromIndex(textIndex + pendingSelection.text.length);

                // IMPORTANT: Clear existing marks to prevent highlight splitting.
                // See translateFromInputWithRefocus for detailed explanation.
                // Vim's cursor bookmarks cause CodeMirror to split markText into multiple spans.
                editor.findMarks(from, to).forEach(m => m.clear());

                editor.markText(from, to, { className: 'highlight-mark' });
                highlights.push({ from, to, selection: pendingSelection.text });
            }
        }

        // Clear pending selection
        pendingSelection = null;

        // Store messages and cache state
        currentMessages = data.messages;
        lastFromCache = data.from_cache || false;

        // Display with context buttons and cache indicator
        displayMessagesWithContext(data.messages, data.has_phrase, data.has_paragraph, data.from_cache);

        // Switch to follow-up mode
        input.value = '';
        input.classList.remove('has-selection');
        inputMode = 'followup';
        isSelectionModified = false;
        originalSelectionText = '';
        input.placeholder = 'Ask a follow-up question...';

        // Reset textarea height and update button
        autoResizeTextarea(input);
        updateSendButton();

        // Return focus to vim editor
        if (editor) {
            editor.focus();
            console.log('Focus returned to editor');
        }

        console.log('Translation received, switched to followup mode');
    } catch (error) {
        console.error('Lookup error:', error);
        displayError('Translation error: ' + error.message);
    } finally {
        // Reset button state
        sendBtn.textContent = originalBtnText;
        updateSendButton();
    }
}

// New function: translate with automatic refocus and cursor restoration
async function translateFromInputWithRefocus(text, cursorPos, selectionStart, selectionEnd) {
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');

    if (!text) return;

    console.log('Translating from visual mode:', text);

    // Show loading state
    const originalBtnText = sendBtn.textContent;
    sendBtn.textContent = 'Translating...';
    sendBtn.disabled = true;

    // Get context from cursor position
    let sentence = '';
    let paragraph = '';

    if (cursorPos) {
        try {
            sentence = getSentenceAtCursor(editor, cursorPos);
            paragraph = extractParagraphFromEditor(editor, cursorPos.line);
        } catch (e) {
            console.log('Could not get context:', e);
        }
    }

    // Prepare request data
    const requestData = {
        selection: text,
        phrase: sentence || "",
        paragraph: paragraph || "",
        file: currentFile || ""
    };


    // Call API
    try {
        const response = await fetch(API_BASE + '/api/lookup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': SESSION_ID
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const errorMsg = await parseErrorResponse(response);
            displayError(errorMsg);
            if (editor) editor.focus();
            return;
        }

        const data = await response.json();


        // Add highlight using text position (same approach as reload - more reliable)
        const content = editor.getValue();
        const textIndex = content.indexOf(text);

        if (textIndex >= 0) {
            const from = editor.posFromIndex(textIndex);
            const to = editor.posFromIndex(textIndex + text.length);

            // IMPORTANT: Clear all existing marks within our highlight range before adding.
            // Vim creates invisible cursor bookmark markers during visual mode selection.
            // If these markers exist inside our range when we call markText(), CodeMirror
            // will SPLIT our highlight around them, creating multiple <span> elements
            // instead of one continuous highlight. This causes the visual bug where
            // hovering shows "text minus last char" and "last char" as separate regions.
            // Clearing all marks first ensures our highlight renders as a single span.
            editor.findMarks(from, to).forEach(m => m.clear());

            editor.markText(from, to, { className: 'highlight-mark' });
            highlights.push({ from, to, selection: text });
        } else if (selectionStart && selectionEnd) {
            // Fallback to captured range if text not found (shouldn't happen)
            editor.markText(selectionStart, selectionEnd, { className: 'highlight-mark' });
            highlights.push({ from: selectionStart, to: selectionEnd, selection: text });
        }

        // Store messages and cache state
        currentMessages = data.messages;
        lastFromCache = data.from_cache || false;

        // Display with context buttons and cache indicator
        displayMessagesWithContext(data.messages, data.has_phrase, data.has_paragraph, data.from_cache);

        // Switch to follow-up mode
        input.value = '';
        input.classList.remove('has-selection');
        inputMode = 'followup';
        isSelectionModified = false;
        originalSelectionText = '';
        input.placeholder = 'Ask a follow-up question...';

        // Reset textarea height and update button
        autoResizeTextarea(input);
        updateSendButton();

        // Restore cursor position and focus editor
        if (editor && cursorPos) {
            editor.setCursor(cursorPos);
            editor.focus();
            console.log('Cursor restored and focus returned to editor');
        }

        console.log('Translation received, switched to followup mode');
    } catch (error) {
        console.error('Lookup error:', error);
        displayError('Translation error: ' + error.message);
        // Return focus even on error
        if (editor) {
            editor.focus();
        }
    } finally {
        // Reset button state and flag
        sendBtn.textContent = originalBtnText;
        updateSendButton();
        isTranslatingFromVisualMode = false;
    }
}

function setupResizeHandle() {
    const handle = document.getElementById('resize-handle');
    const container = document.getElementById('main-container');
    const editorPane = document.getElementById('editor-pane');
    const chatPane = document.getElementById('chat-pane');

    let isDragging = false;
    let startX = 0;
    let startWidth = 0;

    handle.addEventListener('mousedown', function(e) {
        isDragging = true;
        startX = e.clientX;
        startWidth = editorPane.offsetWidth;

        document.body.classList.add('resizing');
        handle.classList.add('dragging');

        e.preventDefault();
    });

    document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;

        const containerWidth = container.offsetWidth;
        const dx = e.clientX - startX;
        const newWidth = startWidth + dx;

        // Calculate percentage (min 20%, max 80%)
        let percentage = (newWidth / containerWidth) * 100;
        percentage = Math.max(20, Math.min(80, percentage));

        editorPane.style.flex = `0 0 ${percentage}%`;

        // Refresh viewers to handle resize
        if (editor) {
            editor.refresh();
        }
    });

    document.addEventListener('mouseup', function() {
        if (isDragging) {
            isDragging = false;
            document.body.classList.remove('resizing');
            handle.classList.remove('dragging');

            // Save position
            const containerWidth = container.offsetWidth;
            const percentage = (editorPane.offsetWidth / containerWidth) * 100;
            appSettings.splitPosition = percentage.toFixed(1);
            saveAppSettings();
        }
    });
}

function setupMenu() {
    const menuBtn = document.getElementById('menu-btn');
    const menuDropdown = document.getElementById('menu-dropdown');

    // Toggle menu
    menuBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        const isOpen = menuDropdown.classList.toggle('open');
        menuBtn.classList.toggle('open', isOpen);
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
        if (!menuDropdown.contains(e.target) && e.target !== menuBtn) {
            menuDropdown.classList.remove('open');
            menuBtn.classList.remove('open');
        }
    });

    // Helper to close menu
    function closeMenu() {
        menuDropdown.classList.remove('open');
        menuBtn.classList.remove('open');
    }

    // Open file menu item
    document.getElementById('menu-open-file').addEventListener('click', function() {
        closeMenu();
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.txt,.md,.pdf,text/plain,text/markdown,application/pdf';
        input.style.display = 'none';
        document.body.appendChild(input);
        input.onchange = function(e) {
            handleFileSelect(e);
            input.remove();
        };
        input.click();
    });

    // Theme options
    document.querySelectorAll('.theme-option').forEach(function(option) {
        option.addEventListener('click', function(e) {
            e.stopPropagation();
            const theme = this.dataset.theme;
            editor.setOption('theme', theme);
            appSettings.editorTheme = theme;
            saveAppSettings();
            updateThemeOptions(theme);
            closeMenu();
            console.log('Theme changed to:', theme);
        });
    });

    // Edit cache menu item
    document.getElementById('menu-edit-cache').addEventListener('click', function() {
        closeMenu();
        openCacheFile();
    });

    // Settings menu item
    document.getElementById('menu-settings').addEventListener('click', function() {
        closeMenu();
        openSettingsModal();
    });
}

async function openCacheFile() {
    try {
        const response = await fetch(API_BASE + '/api/cache/open', { method: 'POST' });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to open cache file');
        }
        console.log('Cache file opened:', data.path);
    } catch (error) {
        console.error('Error opening cache:', error);
        alert('Error opening cache file: ' + error.message);
    }
}

function setupSettingsModal() {
    const modal = document.getElementById('settings-modal');
    const sourceLang = document.getElementById('source-lang');
    const targetLang = document.getElementById('target-lang');
    const errorEl = document.getElementById('lang-error');
    const saveBtn = document.getElementById('settings-save');
    const apiKeyInput = document.getElementById('openai-api-key');
    const toggleBtn = document.getElementById('toggle-api-key');

    // Close handlers
    document.getElementById('settings-close').addEventListener('click', closeSettingsModal);
    document.getElementById('settings-cancel').addEventListener('click', closeSettingsModal);

    // Close on backdrop click
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeSettingsModal();
        }
    });

    // Close on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('open')) {
            closeSettingsModal();
        }
    });

    // API key visibility toggle
    toggleBtn.addEventListener('click', function() {
        if (apiKeyInput.type === 'password') {
            apiKeyInput.type = 'text';
            toggleBtn.classList.add('showing');
        } else {
            apiKeyInput.type = 'password';
            toggleBtn.classList.remove('showing');
        }
    });

    // Validate on change
    sourceLang.addEventListener('change', validateLanguages);
    targetLang.addEventListener('change', validateLanguages);

    // Save handler
    saveBtn.addEventListener('click', saveSettings);
}

function validateLanguages() {
    const sourceLang = document.getElementById('source-lang').value;
    const targetLang = document.getElementById('target-lang').value;
    const errorEl = document.getElementById('lang-error');
    const saveBtn = document.getElementById('settings-save');

    if (sourceLang === targetLang) {
        errorEl.textContent = 'Source and target languages must be different';
        saveBtn.disabled = true;
        return false;
    } else {
        errorEl.textContent = '';
        saveBtn.disabled = false;
        return true;
    }
}

function openSettingsModal() {
    const modal = document.getElementById('settings-modal');
    const apiKeyInput = document.getElementById('openai-api-key');
    const voiceInputCheckbox = document.getElementById('enable-voice-input');
    const pdfRendererSelect = document.getElementById('pdf-renderer');

    // Load API key from appSettings
    apiKeyInput.value = appSettings.openaiApiKey || '';
    apiKeyInput.type = 'password'; // Reset to hidden
    document.getElementById('toggle-api-key').classList.remove('showing');

    // Load voice input setting
    voiceInputCheckbox.checked = appSettings.enableVoiceInput || false;

    // Load PDF renderer setting
    pdfRendererSelect.value = appSettings.pdfRenderer || 'pdfjs';

    // Open modal immediately, then populate language settings
    modal.classList.add('open');

    fetch(API_BASE + '/api/config')
        .then(r => r.json())
        .then(config => {
            document.getElementById('source-lang').value = config.source_lang;
            document.getElementById('target-lang').value = config.target_lang;
            validateLanguages();
        })
        .catch(err => {
            console.error('Settings error:', err);
        });
}

function closeSettingsModal() {
    document.getElementById('settings-modal').classList.remove('open');
}

function setupHelpModal() {
    const modal = document.getElementById('help-modal');
    const helpBtn = document.getElementById('help-btn');
    const closeBtn = document.getElementById('help-close');

    // Open help modal
    helpBtn.addEventListener('click', function() {
        modal.classList.add('open');
    });

    // Close button
    closeBtn.addEventListener('click', function() {
        modal.classList.remove('open');
    });

    // Close on backdrop click
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.classList.remove('open');
        }
    });

    // Close on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('open')) {
            modal.classList.remove('open');
        }
    });
}

async function saveSettings() {
    if (!validateLanguages()) return;

    const sourceLang = document.getElementById('source-lang').value;
    const targetLang = document.getElementById('target-lang').value;
    const apiKey = document.getElementById('openai-api-key').value.trim();
    const enableVoiceInput = document.getElementById('enable-voice-input').checked;
    const pdfRenderer = document.getElementById('pdf-renderer').value;
    const saveBtn = document.getElementById('settings-save');

    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';

    try {
        // Save settings to appSettings (stored on disk)
        appSettings.openaiApiKey = apiKey;
        appSettings.enableVoiceInput = enableVoiceInput;
        appSettings.pdfRenderer = pdfRenderer;
        await saveAppSettings();

        // Update active PDF viewer reference
        pdfViewer = (pdfRenderer === 'iframe') ? pdfIframeViewer : pdfJsViewer;

        // Save language config to backend
        const response = await fetch(API_BASE + '/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                source_lang: sourceLang,
                target_lang: targetLang,
                openai_api_key: apiKey
            })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Failed to save settings');
        }

        // Toggle whisper feature based on current setting
        if (enableVoiceInput && typeof window.initWhisper === 'function') {
            window.initWhisper();
        } else if (!enableVoiceInput && typeof window.destroyWhisper === 'function') {
            window.destroyWhisper();
        }

        closeSettingsModal();
        console.log('Settings saved:', sourceLang, '->', targetLang, 'API key:', apiKey ? 'set' : 'not set', 'Voice:', enableVoiceInput);
    } catch (error) {
        console.error('Save settings error:', error);
        document.getElementById('lang-error').textContent = error.message;
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save';
    }
}

// Dark themes list
const DARK_THEMES = ['monokai', 'dracula', 'solarized dark', 'material'];

function updateThemeOptions(activeTheme) {
    document.querySelectorAll('.theme-option').forEach(function(option) {
        const isActive = option.dataset.theme === activeTheme;
        option.classList.toggle('active', isActive);

        // Update icon: filled circle for active, empty for inactive
        const icon = option.querySelector('.menu-icon');
        if (icon) {
            icon.textContent = isActive ? '●' : '○';
        }
    });

    // Apply dark theme class to body for chat pane styling
    if (DARK_THEMES.includes(activeTheme)) {
        document.body.classList.add('dark-theme');
    } else {
        document.body.classList.remove('dark-theme');
    }
}

function setupEventListeners() {
    // Drag and drop
    const editorPane = document.getElementById('editor-pane');

    editorPane.addEventListener('dragover', function(e) {
        e.preventDefault();
        editorPane.classList.add('drag-over');
    });

    editorPane.addEventListener('dragleave', function() {
        editorPane.classList.remove('drag-over');
    });

    editorPane.addEventListener('drop', function(e) {
        e.preventDefault();
        editorPane.classList.remove('drag-over');

        const file = e.dataTransfer.files[0];
        if (!file) return;

        const name = file.name.toLowerCase();
        if (name.endsWith('.pdf')) {
            const reader = new FileReader();
            reader.onload = function(e) {
                openFile(file.name, e.target.result);
            };
            reader.readAsArrayBuffer(file);
        } else if (name.endsWith('.txt') || name.endsWith('.md')) {
            const reader = new FileReader();
            reader.onload = function(e) {
                openFile(file.name, e.target.result);
            };
            reader.readAsText(file);
        }
    });

    // Chat input setup
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');

    // Handle keyboard input - Enter to submit, Shift+Enter for newline
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    });

    // Track text changes for auto-resize and mode detection
    chatInput.addEventListener('input', function() {
        // Auto-resize textarea
        autoResizeTextarea(chatInput);

        // Slash command autocomplete
        const val = chatInput.value;
        if (val.startsWith('/') && !val.includes(' ')) {
            showCommandAutocomplete(val);
        } else {
            hideCommandAutocomplete();
        }

        // Detect if user modified selection text
        if (inputMode === 'selection' && originalSelectionText) {
            if (chatInput.value !== originalSelectionText) {
                isSelectionModified = true;
                // When user edits selection, switch to translate mode
                inputMode = 'translate';
                chatInput.classList.remove('has-selection');
                chatInput.placeholder = 'Enter text to translate...';
                // Clear pending selection since user is typing new text
                pendingSelection = null;
            }
        }

        // Update button state based on content
        updateSendButton();
    });

    // Hide autocomplete on blur
    chatInput.addEventListener('blur', function() {
        setTimeout(hideCommandAutocomplete, 150);
    });

    // Send button click handler
    sendBtn.addEventListener('click', handleSubmit);

    // Reset context button
    document.getElementById('reset-btn').addEventListener('click', resetContext);

    // Initial button state
    updateSendButton();
}

// Reset conversation context (LLM history only, UI messages stay)
async function resetContext() {
    try {
        await fetch(API_BASE + '/api/session/reset', {
            method: 'POST',
            headers: { 'X-Session-ID': SESSION_ID }
        });

        // Append a visual note in the chat
        const container = document.getElementById('chat-messages');
        const note = document.createElement('div');
        note.className = 'context-reset-note';
        note.textContent = '--- context reset ---';
        container.appendChild(note);
        container.scrollTop = container.scrollHeight;

        console.log('Context reset');
    } catch (error) {
        console.error('Error resetting context:', error);
    }
}

// Slash command autocomplete
const SLASH_COMMANDS = [
    { command: '/reset', description: 'Reset conversation context' }
];

function showCommandAutocomplete(filter) {
    let dropdown = document.getElementById('command-autocomplete');
    if (!dropdown) {
        dropdown = document.createElement('div');
        dropdown.id = 'command-autocomplete';
        document.getElementById('chat-input-container').appendChild(dropdown);
    }

    const matches = SLASH_COMMANDS.filter(c => c.command.startsWith(filter));
    if (matches.length === 0) {
        dropdown.style.display = 'none';
        return;
    }

    dropdown.innerHTML = '';
    matches.forEach(cmd => {
        const item = document.createElement('div');
        item.className = 'autocomplete-item';
        item.innerHTML = '<span class="autocomplete-cmd">' + cmd.command + '</span>' +
                         '<span class="autocomplete-desc">' + cmd.description + '</span>';
        item.addEventListener('mousedown', function(e) {
            e.preventDefault(); // prevent blur
            const chatInput = document.getElementById('chat-input');
            chatInput.value = cmd.command;
            hideCommandAutocomplete();
            handleSubmit();
        });
        dropdown.appendChild(item);
    });

    dropdown.style.display = 'block';
}

function hideCommandAutocomplete() {
    const dropdown = document.getElementById('command-autocomplete');
    if (dropdown) dropdown.style.display = 'none';
}

// Unified submit handler
function handleSubmit() {
    const chatInput = document.getElementById('chat-input');
    const text = chatInput.value.trim();

    if (!text) return;

    // Intercept /reset command
    if (text === '/reset') {
        chatInput.value = '';
        autoResizeTextarea(chatInput);
        updateSendButton();
        resetContext();
        return;
    }

    if (inputMode === 'followup') {
        // Send as follow-up question
        handleConversation();
    } else {
        // Translate mode (selection or free text)
        translateFromInput();
    }
}

async function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;

    if (file.name.toLowerCase().endsWith('.pdf')) {
        const reader = new FileReader();
        reader.onload = function(e) {
            openFile(file.name, e.target.result);
        };
        reader.readAsArrayBuffer(file);
    } else {
        const reader = new FileReader();
        reader.onload = function(e) {
            openFile(file.name, e.target.result);
        };
        reader.readAsText(file);
    }
}

function addToRecentFiles(filename) {
    // Initialize recent files array if needed
    if (!appSettings.recentFiles) {
        appSettings.recentFiles = [];
    }

    // Remove if already exists (to move to top)
    appSettings.recentFiles = appSettings.recentFiles.filter(f => f.name !== filename);

    // Add to beginning - delegate entry creation to activeViewer
    appSettings.recentFiles.unshift(activeViewer.getRecentFileEntry(filename));

    // Keep only last 10 files
    appSettings.recentFiles = appSettings.recentFiles.slice(0, 10);

    // Save and update menu
    saveAppSettings();
    updateRecentFilesMenu();
}

function updateRecentFilesMenu() {
    const submenu = document.getElementById('recent-files-submenu');
    if (!submenu) return;

    // Clear existing items
    submenu.innerHTML = '';

    const recentFiles = appSettings.recentFiles || [];

    if (recentFiles.length === 0) {
        const emptyItem = document.createElement('div');
        emptyItem.className = 'menu-item disabled';
        emptyItem.innerHTML = '<span class="menu-icon">-</span><span class="menu-label">No recent files</span>';
        submenu.appendChild(emptyItem);
        return;
    }

    recentFiles.forEach((file) => {
        const viewer = getViewerForFile(file.name);
        const canRestore = viewer.canRestoreFromRecent(file);
        const item = document.createElement('div');
        item.className = 'menu-item' + (canRestore ? '' : ' disabled');
        item.title = canRestore ? file.name : file.name + ' (re-open from disk)';
        item.innerHTML = `<span class="menu-icon">·</span><span class="menu-label">${escapeHtml(file.name)}</span>`;
        if (canRestore) {
            item.addEventListener('click', function(e) {
                e.stopPropagation();
                if (activeViewer && activeViewer !== viewer) activeViewer.hide();
                activeViewer = viewer;
                currentFile = file.name;
                document.getElementById('filename').textContent = file.name;
                viewer.loadFromRecent(file);
                addToRecentFiles(file.name);
                saveFileState();
                document.getElementById('menu-dropdown').classList.remove('open');
                document.getElementById('menu-btn').classList.remove('open');
            });
        }
        submenu.appendChild(item);
    });
}

async function translateHighlightedText(text) {
    // Translate text from a clicked highlight (will be served from cache)
    console.log('Translating highlighted text:', text);

    // Prepare request data - no context needed, cache will handle it
    const requestData = {
        selection: text,
        phrase: "",
        paragraph: "",
        file: currentFile || ""
    };

    console.log('Sending to API (from highlight):', requestData);

    // Call API
    try {
        const response = await fetch(API_BASE + '/api/lookup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': SESSION_ID
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            throw new Error('Server error: ' + response.status);
        }

        const data = await response.json();

        console.log('API response (from highlight):', data);
        console.log('from_cache:', data.from_cache);

        // Store messages and cache state for conversation
        currentMessages = data.messages;
        lastFromCache = data.from_cache || false;

        // Display (no context buttons since no phrase/paragraph, but show cache indicator)
        displayMessagesWithContext(data.messages, false, false, data.from_cache);

        // Switch to follow-up mode
        const input = document.getElementById('chat-input');
        input.value = '';
        inputMode = 'followup';
        input.placeholder = 'Ask a follow-up question...';
        updateSendButton();

        console.log('Translation received (from highlight), switched to followup mode');
    } catch (error) {
        console.error('Lookup error:', error);
        alert('Translation error: ' + error.message + '\n\nCheck console for details');
    }
}

async function handleLookup() {
    // Get selection - handle vim visual mode properly
    let selection = editor.getSelection();

    // If no selection (vim mode issue), try getting from vim state
    if (!selection || !selection.trim()) {
        const vimState = editor.state.vim;
        if (vimState && vimState.visualMode) {
            // Force vim to update the selection
            const start = editor.getCursor('anchor');
            const end = editor.getCursor('head');
            selection = editor.getRange(start, end);
        }
    }

    if (!selection || !selection.trim()) {
        alert('Please select some text first!\n\nUse vim: press "v" then move cursor to select');
        return;
    }

    console.log('Selected text:', selection);
    console.log('Looking up:', selection);

    // Get context - use the selection cursor position, not current cursor
    const selStart = editor.getCursor('start');
    const selEnd = editor.getCursor('end');

    // Extract sentence and paragraph using vim-compatible logic
    const sentence = getSentenceAtCursor(editor, selStart);
    const paragraph = extractParagraphFromEditor(editor, selStart.line);

    console.log('DEBUG Context:');
    console.log('  cursor line:', selStart.line);
    console.log('  sentence:', sentence);
    console.log('  paragraph:', paragraph);

    // Prepare request data
    const requestData = {
        selection: selection,
        phrase: sentence || "",
        paragraph: paragraph || "",
        file: currentFile || ""
    };

    
    // Call API
    try {
        const response = await fetch(API_BASE + '/api/lookup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': SESSION_ID
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            throw new Error('Server error: ' + response.status);
        }

        const data = await response.json();

                console.log('has_phrase:', data.has_phrase, 'has_paragraph:', data.has_paragraph, 'from_cache:', data.from_cache);

        // Add highlight using indexOf approach for consistency
        const content = editor.getValue();
        const textIndex = content.indexOf(selection);
        if (textIndex >= 0) {
            const from = editor.posFromIndex(textIndex);
            const to = editor.posFromIndex(textIndex + selection.length);

            // IMPORTANT: Clear existing marks to prevent highlight splitting.
            // See translateFromInputWithRefocus for detailed explanation.
            // Vim's cursor bookmarks cause CodeMirror to split markText into multiple spans.
            editor.findMarks(from, to).forEach(m => m.clear());

            editor.markText(from, to, { className: 'highlight-mark' });
            highlights.push({ from, to, selection });
        }

        // Store messages and cache state for conversation
        currentMessages = data.messages;
        lastFromCache = data.from_cache || false;

        // Display with context buttons and cache indicator
        displayMessagesWithContext(data.messages, data.has_phrase, data.has_paragraph, data.from_cache);

        // Switch to follow-up mode
        const input = document.getElementById('chat-input');
        input.value = '';
        input.classList.remove('has-selection');
        inputMode = 'followup';
        isSelectionModified = false;
        originalSelectionText = '';
        input.placeholder = 'Ask a follow-up question...';
        autoResizeTextarea(input);
        updateSendButton();

        console.log('Translation received, switched to followup mode');
    } catch (error) {
        console.error('Lookup error:', error);
        alert('Translation error: ' + error.message + '\n\nCheck console for details');
    }
}

// getParagraphContext removed - using extractParagraphFromEditor from context-extractor.js

function disableContextButtons() {
    document.querySelectorAll('.context-btn').forEach(function(btn) {
        btn.disabled = true;
        btn.classList.add('loading');
    });
}

function enableContextButtons() {
    document.querySelectorAll('.context-btn').forEach(function(btn) {
        btn.disabled = false;
        btn.classList.remove('loading');
    });
}

async function translatePhrase() {
    console.log('Translating phrase...');

    disableContextButtons();

    try {
        const response = await fetch(API_BASE + '/api/lookup/phrase', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': SESSION_ID
            }
        });

        if (!response.ok) {
            const errorMsg = await parseErrorResponse(response);
            displayError(errorMsg);
            enableContextButtons();
            return;
        }

        const data = await response.json();
        currentMessages = data.messages;
        lastFromCache = data.from_cache || false;
        displayMessagesWithContext(data.messages, data.has_phrase || false, data.has_paragraph || false, data.from_cache);
    } catch (error) {
        console.error('Phrase translation error:', error);
        displayError('Error: ' + error.message);
        enableContextButtons();
    }
}

async function translateParagraph() {
    console.log('Translating paragraph...');

    disableContextButtons();

    try {
        const response = await fetch(API_BASE + '/api/lookup/paragraph', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': SESSION_ID
            }
        });

        if (!response.ok) {
            const errorMsg = await parseErrorResponse(response);
            displayError(errorMsg);
            enableContextButtons();
            return;
        }

        const data = await response.json();
        currentMessages = data.messages;
        lastFromCache = data.from_cache || false;
        displayMessagesWithContext(data.messages, data.has_phrase || false, data.has_paragraph || false, data.from_cache);
    } catch (error) {
        console.error('Paragraph translation error:', error);
        displayError('Error: ' + error.message);
        enableContextButtons();
    }
}

function renderMarkdown(text) {
    // Use marked library if available, otherwise fallback to basic formatting
    if (typeof marked !== 'undefined') {
        // Configure marked for safe rendering
        marked.setOptions({
            breaks: true,
            gfm: true
        });
        return marked.parse(text);
    }
    // Fallback: just escape and convert newlines
    return escapeHtml(text).replace(/\n/g, '<br>');
}

function displayMessagesWithContext(messages, hasPhrase, hasParagraph, fromCache) {
    const container = document.getElementById('chat-messages');
    container.innerHTML = '';

    // Use global lastFromCache if fromCache not provided (for conversation updates)
    const showCache = fromCache !== undefined ? fromCache : lastFromCache;

    console.log('displayMessagesWithContext called:', {
        messageCount: messages.length,
        hasPhrase: hasPhrase,
        hasParagraph: hasParagraph,
        fromCache: showCache
    });

    messages.forEach((msg, idx) => {
        const div = document.createElement('div');
        div.className = 'message ' + msg.type;

        if (msg.type === 'translation') {
            // Show cache badge only on the last translation if from cache
            const isLastMsg = idx === messages.length - 1;
            const cacheBadge = (isLastMsg && showCache)
                ? '<span class="cache-badge">&#9889; Cached</span>'
                : '';

            div.innerHTML =
                '<div class="query-header">' +
                    '<span class="query-text">' + escapeHtml(msg.data.query) + '</span>' +
                    cacheBadge +
                '</div>' +
                '<div class="translation-text">' + escapeHtml(msg.data.translation) + '</div>' +
                '<div class="explanations">' + renderMarkdown(msg.data.explanations) + '</div>';

            console.log('Message index:', idx, 'Last index:', messages.length - 1);
            console.log('Should show buttons:', idx === messages.length - 1 && (hasPhrase || hasParagraph));

            // Add context buttons to LAST translation only
            if (idx === messages.length - 1 && (hasPhrase || hasParagraph)) {
                console.log('Creating context buttons!');
                const actions = document.createElement('div');
                actions.className = 'context-actions';

                if (hasPhrase) {
                    console.log('Adding phrase button');
                    const btn1 = document.createElement('button');
                    btn1.className = 'context-btn';
                    btn1.textContent = 'Translate full sentence';
                    btn1.onclick = translatePhrase;
                    actions.appendChild(btn1);
                }

                if (hasParagraph) {
                    console.log('Adding paragraph button');
                    const btn2 = document.createElement('button');
                    btn2.className = 'context-btn';
                    btn2.textContent = 'Translate full paragraph';
                    btn2.onclick = translateParagraph;
                    actions.appendChild(btn2);
                }

                div.appendChild(actions);
                console.log('Buttons appended to div');
            }
        } else if (msg.type === 'question') {
            div.innerHTML =
                '<div class="message-header">You</div>' +
                '<div class="message-content">' + escapeHtml(msg.content) + '</div>';
        } else if (msg.type === 'answer') {
            div.innerHTML =
                '<div class="message-header">Assistant</div>' +
                '<div class="message-content">' + renderMarkdown(msg.content) + '</div>';
        }

        container.appendChild(div);
    });

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

function displayMessages(messages) {
    displayMessagesWithContext(messages, false, false);
}

function displayError(errorMessage) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'message error-message';
    div.innerHTML =
        '<div class="message-header" style="color: #dc2626;">Error</div>' +
        '<div class="message-content" style="color: #dc2626; background: #fef2f2; border: 1px solid #fecaca; padding: 12px; border-radius: 6px;">' +
        escapeHtml(errorMessage) +
        '</div>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

async function parseErrorResponse(response) {
    try {
        const data = await response.json();
        return data.detail || data.message || `Server error (${response.status})`;
    } catch {
        return `Server error (${response.status})`;
    }
}

function appendQuestionMessage(question) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'message question';
    div.innerHTML =
        '<div class="message-header">You</div>' +
        '<div class="message-content">' + escapeHtml(question) + '</div>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function appendLoadingMessage() {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'message loading';
    div.id = 'loading-message';
    div.innerHTML =
        '<div class="message-header">Assistant</div>' +
        '<div class="loading-dots"><span></span><span></span><span></span></div>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div;
}

function removeLoadingMessage() {
    const loading = document.getElementById('loading-message');
    if (loading) {
        loading.remove();
    }
}

function appendAnswerMessage(answer) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'message answer';
    div.innerHTML =
        '<div class="message-header">Assistant</div>' +
        '<div class="message-content">' + renderMarkdown(answer) + '</div>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

async function handleConversation() {
    const input = document.getElementById('chat-input');
    const question = input.value.trim();

    if (!question) return;

    console.log('Asking question:', question);

    // Clear input immediately
    input.value = '';

    // Show question immediately
    appendQuestionMessage(question);

    // Show loading indicator
    appendLoadingMessage();

    // Disable input while waiting
    input.disabled = true;

    try {
        const response = await fetch(API_BASE + '/api/conversation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': SESSION_ID
            },
            body: JSON.stringify({ question: question })
        });

        // Remove loading first
        removeLoadingMessage();

        if (!response.ok) {
            const errorMsg = await parseErrorResponse(response);
            displayError(errorMsg);
            return;
        }

        const data = await response.json();
        console.log('Received response:', data);

        // Find the LAST answer in the response (the new one we just received)
        // Using findLast() because data.messages contains ALL conversation history,
        // and we only want to append the newest answer (not re-display old ones)
        const answerMsg = data.messages.findLast(m => m.type === 'answer' && m.content);
        if (answerMsg) {
            appendAnswerMessage(answerMsg.content);
        }

        // Update stored messages
        currentMessages = data.messages;

    } catch (error) {
        console.error('Conversation error:', error);
        removeLoadingMessage();
        displayError('Error: ' + error.message);
    } finally {
        // Re-enable input
        input.disabled = false;
        input.focus();
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatExplanations(text) {
    // Convert newlines to <br> tags and preserve formatting
    return escapeHtml(text).replace(/\n/g, '<br>');
}

// Export functions and state for testing
if (typeof window !== 'undefined') {
    // Make editor accessible globally for tests
    Object.defineProperty(window, 'editor', {
        get: function() { return editor; },
        set: function(val) { editor = val; }
    });

    window.handleLookup = handleLookup;
    window.displayMessagesWithContext = displayMessagesWithContext;
    window.displayMessages = displayMessages;
    window.translatePhrase = translatePhrase;
    window.translateParagraph = translateParagraph;
    window.updateSelectionPreview = updateSelectionPreview;
    window.clearSelectionPreview = clearSelectionPreview;
    window.translateFromInput = translateFromInput;
    window.translateFromInputWithRefocus = translateFromInputWithRefocus;
    window.updateSendButton = updateSendButton;
    window.autoResizeTextarea = autoResizeTextarea;
    window.handleSubmit = handleSubmit;
}
