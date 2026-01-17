// Session ID for conversation continuity
const SESSION_ID = crypto.randomUUID();

// State
let currentFile = null;
let highlights = [];
let editor = null;

// Initialize CodeMirror when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initEditor();
    setupEventListeners();
});

function initEditor() {
    const textarea = document.getElementById('editor');

    // Load saved theme
    const savedTheme = localStorage.getItem('editorTheme') || 'default';

    editor = CodeMirror.fromTextArea(textarea, {
        mode: 'markdown',
        lineNumbers: true,
        lineWrapping: true,
        keyMap: 'vim',
        theme: savedTheme
    });

    // Set theme select to saved value
    document.getElementById('theme-select').value = savedTheme;

    // Track vim mode changes
    editor.on('vim-mode-change', function(e) {
        const mode = e.mode || 'normal';
        document.getElementById('vim-mode').textContent = '-- ' + mode.toUpperCase() + ' --';
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

    console.log('Editor initialized with vim mode and theme:', savedTheme);
}

function setupEventListeners() {
    // Open file button
    document.getElementById('open-file').addEventListener('click', function() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.txt,.md';
        input.onchange = handleFileSelect;
        input.click();
    });

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

    // Theme selector
    document.getElementById('theme-select').addEventListener('change', function(e) {
        const theme = e.target.value;
        editor.setOption('theme', theme);
        localStorage.setItem('editorTheme', theme);
        console.log('Theme changed to:', theme);
    });

    // Settings button
    document.getElementById('settings').addEventListener('click', function() {
        fetch('/api/config')
            .then(r => r.json())
            .then(config => {
                alert('Current settings:\n\n' +
                      'Source: ' + config.source_lang + '\n' +
                      'Target: ' + config.target_lang + '\n\n' +
                      'To change, edit config.ini file');
            })
            .catch(err => {
                console.error('Settings error:', err);
                alert('Error loading settings');
            });
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
    const originalText = btn.textContent;
    btn.textContent = 'Translating...';
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
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// getParagraphContext removed - using extractParagraphFromEditor from context-extractor.js

async function translatePhrase() {
    console.log('Translating phrase...');

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
        displayMessagesWithContext(data.messages, data.has_phrase || false, data.has_paragraph || false);
    } catch (error) {
        console.error('Phrase translation error:', error);
        alert('Error: ' + error.message);
    }
}

async function translateParagraph() {
    console.log('Translating paragraph...');

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
        displayMessagesWithContext(data.messages, data.has_phrase || false, data.has_paragraph || false);
    } catch (error) {
        console.error('Paragraph translation error:', error);
        alert('Error: ' + error.message);
    }
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
                '<h3>' + escapeHtml(msg.data.query) + '</h3>' +
                '<div class="translation-text">' + escapeHtml(msg.data.translation) + '</div>' +
                '<div class="explanations">' + formatExplanations(msg.data.explanations) + '</div>';

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
                    btn1.textContent = '1. Translate full sentence';
                    btn1.onclick = translatePhrase;
                    actions.appendChild(btn1);
                }

                if (hasParagraph) {
                    console.log('Adding paragraph button');
                    const btn2 = document.createElement('button');
                    btn2.className = 'context-btn';
                    btn2.textContent = '2. Translate full paragraph';
                    btn2.onclick = translateParagraph;
                    actions.appendChild(btn2);
                }

                div.appendChild(actions);
                console.log('Buttons appended to div');
            }
        } else if (msg.type === 'question') {
            div.innerHTML = '<strong>You:</strong> ' + escapeHtml(msg.content);
        } else if (msg.type === 'answer') {
            div.innerHTML = '<strong>Assistant:</strong> ' + escapeHtml(msg.content);
        }

        container.appendChild(div);
    });

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

function displayMessages(messages) {
    displayMessagesWithContext(messages, false, false);
}

async function handleConversation() {
    const input = document.getElementById('chat-input');
    const question = input.value.trim();

    if (!question) return;

    console.log('Asking question:', question);

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

        displayMessages(data.messages);

        input.value = '';
    } catch (error) {
        console.error('Conversation error:', error);
        alert('Error: ' + error.message);
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
