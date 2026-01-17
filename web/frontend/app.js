// Session ID for conversation continuity
const SESSION_ID = crypto.randomUUID();

// State
let currentFile = null;
let highlights = [];
let editor = null;
let currentMessages = []; // Store current messages for conversation

// Initialize CodeMirror when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initEditor();
    setupEventListeners();
    setupResizeHandle();
    setupMenu();
    setupSettingsModal();
});

function initEditor() {
    const textarea = document.getElementById('editor');

    // Load saved theme
    const savedTheme = localStorage.getItem('editorTheme') || 'default';

    // Load saved split position
    const savedSplit = localStorage.getItem('splitPosition') || '65';
    const editorPane = document.getElementById('editor-pane');
    const chatPane = document.getElementById('chat-pane');
    editorPane.style.flex = `0 0 ${savedSplit}%`;
    chatPane.style.flex = '1';

    editor = CodeMirror.fromTextArea(textarea, {
        mode: 'markdown',
        lineNumbers: true,
        lineWrapping: true,
        keyMap: 'vim',
        theme: savedTheme
    });

    // Update theme options to show active
    updateThemeOptions(savedTheme);

    // Track vim mode changes
    editor.on('vim-mode-change', function(e) {
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

    console.log('Vim commands registered: type ":t" or ":tr" in vim normal mode!');

    // Handle clicks on highlights
    editor.getWrapperElement().addEventListener('click', function(e) {
        // Check if clicked element is a highlight
        if (e.target.classList.contains('highlight-mark')) {
            const text = e.target.textContent;
            if (text && text.trim()) {
                console.log('Highlight clicked:', text);
                translateHighlightedText(text.trim());
            }
        }
    });

    console.log('Editor initialized with vim mode and theme:', savedTheme);
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

        // Refresh CodeMirror to handle resize
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
            localStorage.setItem('splitPosition', percentage.toFixed(1));
        }
    });
}

function setupMenu() {
    const menuBtn = document.getElementById('menu-btn');
    const menuDropdown = document.getElementById('menu-dropdown');

    // Toggle menu
    menuBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        menuDropdown.classList.toggle('open');
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
        if (!menuDropdown.contains(e.target) && e.target !== menuBtn) {
            menuDropdown.classList.remove('open');
        }
    });

    // Open file menu item
    document.getElementById('menu-open-file').addEventListener('click', function() {
        menuDropdown.classList.remove('open');
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.txt,.md';
        input.onchange = handleFileSelect;
        input.click();
    });

    // Theme options
    document.querySelectorAll('.theme-option').forEach(function(option) {
        option.addEventListener('click', function(e) {
            e.stopPropagation();
            const theme = this.dataset.theme;
            editor.setOption('theme', theme);
            localStorage.setItem('editorTheme', theme);
            updateThemeOptions(theme);
            menuDropdown.classList.remove('open');
            console.log('Theme changed to:', theme);
        });
    });

    // Settings menu item
    document.getElementById('menu-settings').addEventListener('click', function() {
        menuDropdown.classList.remove('open');
        openSettingsModal();
    });
}

function setupSettingsModal() {
    const modal = document.getElementById('settings-modal');
    const sourceLang = document.getElementById('source-lang');
    const targetLang = document.getElementById('target-lang');
    const errorEl = document.getElementById('lang-error');
    const saveBtn = document.getElementById('settings-save');

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

    // Load current settings
    fetch('/api/config')
        .then(r => r.json())
        .then(config => {
            document.getElementById('source-lang').value = config.source_lang;
            document.getElementById('target-lang').value = config.target_lang;
            validateLanguages();
            modal.classList.add('open');
        })
        .catch(err => {
            console.error('Settings error:', err);
            alert('Error loading settings');
        });
}

function closeSettingsModal() {
    document.getElementById('settings-modal').classList.remove('open');
}

async function saveSettings() {
    if (!validateLanguages()) return;

    const sourceLang = document.getElementById('source-lang').value;
    const targetLang = document.getElementById('target-lang').value;
    const saveBtn = document.getElementById('settings-save');

    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';

    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                source_lang: sourceLang,
                target_lang: targetLang
            })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Failed to save settings');
        }

        closeSettingsModal();
        console.log('Settings saved:', sourceLang, '->', targetLang);
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
        if (option.dataset.theme === activeTheme) {
            option.classList.add('active');
        } else {
            option.classList.remove('active');
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
    // Translate button
    document.getElementById('translate-btn').addEventListener('click', function() {
        handleLookup();
    });

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
        if (file && (file.name.endsWith('.txt') || file.name.endsWith('.md'))) {
            const reader = new FileReader();
            reader.onload = function(e) {
                loadFile(file.name, e.target.result);
            };
            reader.readAsText(file);
        }
    });

    // Chat input - handle Enter key
    const chatInput = document.getElementById('chat-input');
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleConversation();
        }
    });
}

async function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        loadFile(file.name, e.target.result);
    };
    reader.readAsText(file);
}

async function loadFile(filename, content) {
    currentFile = filename;
    document.getElementById('filename').textContent = filename;

    // Set editor content
    editor.setValue(content);

    // Load highlights from history
    try {
        const response = await fetch('/api/history?file=' + encodeURIComponent(filename));
        const data = await response.json();

        highlights = data.entries
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

        // Apply highlights
        highlights.forEach(h => {
            editor.markText(h.from, h.to, { className: 'highlight-mark' });
        });

        console.log('Loaded ' + highlights.length + ' highlights');
    } catch (error) {
        console.error('Load history error:', error);
    }
}

async function translateHighlightedText(text) {
    // Translate text from a clicked highlight (will be served from cache)
    console.log('Translating highlighted text:', text);

    // Show loading state
    const btn = document.getElementById('translate-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = 'Translating...';
    btn.disabled = true;

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
        const response = await fetch('/api/lookup', {
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

        // Store messages for conversation
        currentMessages = data.messages;

        // Display (no context buttons since no phrase/paragraph)
        displayMessagesWithContext(data.messages, false, false);

        // Enable chat input
        document.getElementById('chat-input').disabled = false;

        console.log('Translation received (from highlight)');
    } catch (error) {
        console.error('Lookup error:', error);
        alert('Translation error: ' + error.message + '\n\nCheck console for details');
    } finally {
        // Reset button
        btn.innerHTML = originalText;
        btn.disabled = false;
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

    // Show loading state
    const btn = document.getElementById('translate-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = 'Translating...';
    btn.disabled = true;

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

    console.log('Sending to API:', requestData);

    // Call API
    try {
        const response = await fetch('/api/lookup', {
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

        console.log('API response:', data);
        console.log('has_phrase:', data.has_phrase, 'has_paragraph:', data.has_paragraph);

        // Add highlight
        const from = editor.getCursor('start');
        const to = editor.getCursor('end');
        editor.markText(from, to, { className: 'highlight-mark' });

        highlights.push({ from, to, selection });

        // Store messages for conversation
        currentMessages = data.messages;

        // Display with context buttons
        displayMessagesWithContext(data.messages, data.has_phrase, data.has_paragraph);

        // Enable chat input
        document.getElementById('chat-input').disabled = false;

        console.log('Translation received');
    } catch (error) {
        console.error('Lookup error:', error);
        alert('Translation error: ' + error.message + '\n\nCheck console for details');
    } finally {
        // Reset button
        btn.innerHTML = originalText;
        btn.disabled = false;
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
        const response = await fetch('/api/lookup/phrase', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': SESSION_ID
            }
        });

        if (!response.ok) {
            throw new Error('Server error: ' + response.status);
        }

        const data = await response.json();
        currentMessages = data.messages;
        displayMessagesWithContext(data.messages, data.has_phrase || false, data.has_paragraph || false);
    } catch (error) {
        console.error('Phrase translation error:', error);
        alert('Error: ' + error.message);
        enableContextButtons();
    }
}

async function translateParagraph() {
    console.log('Translating paragraph...');

    disableContextButtons();

    try {
        const response = await fetch('/api/lookup/paragraph', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': SESSION_ID
            }
        });

        if (!response.ok) {
            throw new Error('Server error: ' + response.status);
        }

        const data = await response.json();
        currentMessages = data.messages;
        displayMessagesWithContext(data.messages, data.has_phrase || false, data.has_paragraph || false);
    } catch (error) {
        console.error('Paragraph translation error:', error);
        alert('Error: ' + error.message);
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

function displayMessagesWithContext(messages, hasPhrase, hasParagraph) {
    const container = document.getElementById('chat-messages');
    container.innerHTML = '';

    console.log('displayMessagesWithContext called:', {
        messageCount: messages.length,
        hasPhrase: hasPhrase,
        hasParagraph: hasParagraph
    });

    messages.forEach((msg, idx) => {
        const div = document.createElement('div');
        div.className = 'message ' + msg.type;

        if (msg.type === 'translation') {
            div.innerHTML =
                '<div class="query-header">' +
                    '<span class="query-text">' + escapeHtml(msg.data.query) + '</span>' +
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
        const response = await fetch('/api/conversation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': SESSION_ID
            },
            body: JSON.stringify({ question: question })
        });

        if (!response.ok) {
            throw new Error('Server error: ' + response.status);
        }

        const data = await response.json();
        console.log('Received response:', data);

        // Remove loading and show answer
        removeLoadingMessage();

        // Find the answer in the response
        const answerMsg = data.messages.find(m => m.type === 'answer' && m.content);
        if (answerMsg) {
            appendAnswerMessage(answerMsg.content);
        }

        // Update stored messages
        currentMessages = data.messages;

    } catch (error) {
        console.error('Conversation error:', error);
        removeLoadingMessage();
        appendAnswerMessage('Error: ' + error.message);
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
}
