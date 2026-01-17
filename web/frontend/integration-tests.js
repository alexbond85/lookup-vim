/**
 * Integration tests for nvim-lookup web app
 * Tests the full flow: selection -> context extraction -> API request -> UI display
 */

// ============================================
// Test Setup
// ============================================

function setupTests() {
    // Install fetch mock before running tests
    FetchMock.install();

    // Set up default mock responses
    FetchMock.setResponse('/api/lookup', {
        messages: [{
            type: 'translation',
            data: {
                query: 'test',
                translation: 'Test translation',
                explanations: 'This is a test explanation.'
            }
        }],
        has_phrase: true,
        has_paragraph: true
    });

    FetchMock.setResponse('/api/lookup/phrase', {
        messages: [{
            type: 'translation',
            data: {
                query: 'test phrase',
                translation: 'Phrase translation',
                explanations: 'Phrase explanation.'
            }
        }],
        has_phrase: false,
        has_paragraph: true
    });

    FetchMock.setResponse('/api/lookup/paragraph', {
        messages: [{
            type: 'translation',
            data: {
                query: 'test paragraph',
                translation: 'Paragraph translation',
                explanations: 'Paragraph explanation.'
            }
        }],
        has_phrase: false,
        has_paragraph: false
    });

    FetchMock.setResponse('/api/history', {
        entries: []
    });

    FetchMock.setResponse('/api/config', {
        source_lang: 'French',
        target_lang: 'English'
    });
}

function teardownTests() {
    FetchMock.uninstall();
}

// ============================================
// Register all tests
// ============================================

function registerTests() {
    // Clear any previously registered tests
    TestHarness.clear();

// ============================================
// Category 1: CodeMirror Selection Tests
// ============================================

TestHarness.test('CodeMirror: Editor initializes correctly', async function() {
    const editor = EditorHelper.getEditor();
    if (!editor) {
        throw new Error('Editor not initialized');
    }
});

TestHarness.test('CodeMirror: Can set and get content', async function() {
    const testContent = 'Hello world. This is a test.';
    EditorHelper.setContent(testContent);
    const content = EditorHelper.getContent();

    if (content !== testContent) {
        throw new Error(`Content mismatch: expected "${testContent}" but got "${content}"`);
    }
});

TestHarness.test('CodeMirror: Programmatic text selection works', async function() {
    EditorHelper.setContent('Bonjour monsieur. Comment allez-vous?');
    EditorHelper.selectText('monsieur');

    const selection = EditorHelper.getSelection();
    if (selection !== 'monsieur') {
        throw new Error(`Expected selection "monsieur" but got "${selection}"`);
    }
});

TestHarness.test('CodeMirror: Can select specific occurrence of text', async function() {
    EditorHelper.setContent('hello world hello universe hello galaxy');
    EditorHelper.selectText('hello', 1); // Second occurrence

    const cursor = EditorHelper.getCursor('start');
    // Second 'hello' starts at position 12
    if (cursor.ch !== 12) {
        throw new Error(`Expected cursor at ch=12 but got ch=${cursor.ch}`);
    }
});

TestHarness.test('CodeMirror: Selection across multiple words works', async function() {
    EditorHelper.setContent('The quick brown fox jumps over the lazy dog.');
    EditorHelper.selectText('quick brown fox');

    const selection = EditorHelper.getSelection();
    if (selection !== 'quick brown fox') {
        throw new Error(`Expected "quick brown fox" but got "${selection}"`);
    }
});

// ============================================
// Category 2: Context Extraction Tests
// ============================================

TestHarness.test('Context: getSentenceAtCursor extracts correct sentence', async function() {
    EditorHelper.setContent('First sentence. Second sentence here. Third sentence.');
    EditorHelper.selectText('Second');

    const cursor = EditorHelper.getCursor('start');
    const sentence = getSentenceAtCursor(window.editor, cursor);

    if (!sentence.includes('Second sentence here')) {
        throw new Error(`Expected sentence containing "Second sentence here" but got "${sentence}"`);
    }
});

TestHarness.test('Context: extractParagraphFromEditor works correctly', async function() {
    const content = 'Paragraph one line one.\nParagraph one line two.\n\nParagraph two.';
    EditorHelper.setContent(content);
    EditorHelper.selectText('line one');

    const cursor = EditorHelper.getCursor('start');
    const paragraph = extractParagraphFromEditor(window.editor, cursor.line);

    if (!paragraph.includes('Paragraph one line one') || !paragraph.includes('Paragraph one line two')) {
        throw new Error(`Expected both lines in paragraph but got "${paragraph}"`);
    }

    // Should NOT include paragraph two
    if (paragraph.includes('Paragraph two')) {
        throw new Error('Paragraph should not include text from next paragraph');
    }
});

TestHarness.test('Context: Single sentence is extracted correctly', async function() {
    EditorHelper.setContent('Only one sentence here.');
    EditorHelper.selectText('one');

    const cursor = EditorHelper.getCursor('start');
    const sentence = getSentenceAtCursor(window.editor, cursor);

    if (sentence !== 'Only one sentence here.') {
        throw new Error(`Expected "Only one sentence here." but got "${sentence}"`);
    }
});

TestHarness.test('Context: Sentence with exclamation mark', async function() {
    EditorHelper.setContent('Hello! How are you? I am fine.');
    EditorHelper.selectText('How');

    const cursor = EditorHelper.getCursor('start');
    const sentence = getSentenceAtCursor(window.editor, cursor);

    if (!sentence.includes('How are you?')) {
        throw new Error(`Expected sentence containing "How are you?" but got "${sentence}"`);
    }
});

TestHarness.test('Context: Sentence with question mark', async function() {
    EditorHelper.setContent('What is this? It is a book. Very nice!');
    EditorHelper.selectText('book');

    const cursor = EditorHelper.getCursor('start');
    const sentence = getSentenceAtCursor(window.editor, cursor);

    if (!sentence.includes('It is a book.')) {
        throw new Error(`Expected sentence containing "It is a book." but got "${sentence}"`);
    }
});

// ============================================
// Category 3: API Request Tests
// ============================================

TestHarness.test('API: handleLookup sends correct request structure', async function() {
    FetchMock.clearCalls();
    clearMessages();

    EditorHelper.setContent('Bonjour monsieur. Comment allez-vous?');
    EditorHelper.selectText('monsieur');

    await handleLookup();

    const calls = FetchMock.getCallsTo('/api/lookup');
    if (calls.length === 0) {
        throw new Error('Expected /api/lookup to be called');
    }

    const body = calls[0].body;
    if (!body.selection) {
        throw new Error('Request missing "selection" field');
    }
    if (body.phrase === undefined) {
        throw new Error('Request missing "phrase" field');
    }
    if (body.paragraph === undefined) {
        throw new Error('Request missing "paragraph" field');
    }
});

TestHarness.test('API: Selection is sent correctly', async function() {
    FetchMock.clearCalls();
    clearMessages();

    EditorHelper.setContent('Le chat noir dort.');
    EditorHelper.selectText('chat');

    await handleLookup();

    FetchMock.assertCalled('/api/lookup', { selection: 'chat' });
});

TestHarness.test('API: Phrase (sentence) is sent in request', async function() {
    FetchMock.clearCalls();
    clearMessages();

    EditorHelper.setContent('Bonjour monsieur. Comment allez-vous?');
    EditorHelper.selectText('monsieur');

    await handleLookup();

    const calls = FetchMock.getCallsTo('/api/lookup');
    const body = calls[0].body;

    // Phrase should contain the sentence with "monsieur"
    if (!body.phrase || !body.phrase.includes('monsieur')) {
        throw new Error(`Expected phrase to contain "monsieur" but got "${body.phrase}"`);
    }
});

TestHarness.test('API: Phrase differs from selection (enables has_phrase)', async function() {
    FetchMock.clearCalls();
    clearMessages();

    EditorHelper.setContent('Bonjour monsieur. Comment allez-vous?');
    EditorHelper.selectText('monsieur');

    await handleLookup();

    const calls = FetchMock.getCallsTo('/api/lookup');
    const body = calls[0].body;

    // This is the key check - phrase must differ from selection for has_phrase=true
    if (body.phrase.trim() === body.selection.trim()) {
        throw new Error(
            `CRITICAL: phrase equals selection! Backend will return has_phrase=false.\n` +
            `selection: "${body.selection}"\n` +
            `phrase: "${body.phrase}"`
        );
    }
});

TestHarness.test('API: Paragraph differs from selection and phrase (enables has_paragraph)', async function() {
    FetchMock.clearCalls();
    clearMessages();

    // Multi-line paragraph
    const content = 'First sentence here. Second sentence too.\n\nAnother paragraph.';
    EditorHelper.setContent(content);
    EditorHelper.selectText('First');

    await handleLookup();

    const calls = FetchMock.getCallsTo('/api/lookup');
    const body = calls[0].body;

    // Paragraph must differ from both selection and phrase
    if (body.paragraph.trim() === body.selection.trim()) {
        throw new Error(
            `paragraph equals selection! Backend will return has_paragraph=false.\n` +
            `selection: "${body.selection}"\n` +
            `paragraph: "${body.paragraph}"`
        );
    }

    // For single-line content, paragraph might equal phrase (that's OK)
    // But for multi-sentence content, they should differ
    if (body.paragraph.trim() === body.phrase.trim() && body.paragraph.includes('Second')) {
        throw new Error(
            `paragraph equals phrase for multi-sentence content!\n` +
            `phrase: "${body.phrase}"\n` +
            `paragraph: "${body.paragraph}"`
        );
    }
});

TestHarness.test('API: Paragraph is sent in request', async function() {
    FetchMock.clearCalls();
    clearMessages();

    const content = 'First line of paragraph.\nSecond line here.\n\nDifferent paragraph.';
    EditorHelper.setContent(content);
    EditorHelper.selectText('Second');

    await handleLookup();

    const calls = FetchMock.getCallsTo('/api/lookup');
    const body = calls[0].body;

    // Paragraph should contain both lines
    if (!body.paragraph || !body.paragraph.includes('First line')) {
        throw new Error(`Expected paragraph to contain "First line" but got "${body.paragraph}"`);
    }
});

// ============================================
// Category 4: Context Buttons Tests
// ============================================

TestHarness.test('Buttons: Context buttons appear when has_phrase=true and has_paragraph=true', async function() {
    FetchMock.clearCalls();
    clearMessages();

    // Set up response with both flags true
    FetchMock.setResponse('/api/lookup', {
        messages: [{
            type: 'translation',
            data: {
                query: 'test',
                translation: 'Translation',
                explanations: 'Explanation'
            }
        }],
        has_phrase: true,
        has_paragraph: true
    });

    EditorHelper.setContent('Bonjour monsieur. Comment allez-vous?');
    EditorHelper.selectText('monsieur');

    await handleLookup();

    // Wait a bit for DOM to update
    await sleep(100);

    DOMAssert.hasContextButtons(true, true);
});

TestHarness.test('Buttons: Only phrase button appears when has_phrase=true, has_paragraph=false', async function() {
    FetchMock.clearCalls();
    clearMessages();

    FetchMock.setResponse('/api/lookup', {
        messages: [{
            type: 'translation',
            data: {
                query: 'test',
                translation: 'Translation',
                explanations: 'Explanation'
            }
        }],
        has_phrase: true,
        has_paragraph: false
    });

    EditorHelper.setContent('Simple sentence.');
    EditorHelper.selectText('Simple');

    await handleLookup();
    await sleep(100);

    DOMAssert.hasContextButtons(true, false);
});

TestHarness.test('Buttons: No buttons appear when has_phrase=false and has_paragraph=false', async function() {
    FetchMock.clearCalls();
    clearMessages();

    FetchMock.setResponse('/api/lookup', {
        messages: [{
            type: 'translation',
            data: {
                query: 'test',
                translation: 'Translation',
                explanations: 'Explanation'
            }
        }],
        has_phrase: false,
        has_paragraph: false
    });

    EditorHelper.setContent('Word');
    EditorHelper.selectText('Word');

    await handleLookup();
    await sleep(100);

    DOMAssert.hasContextButtons(false, false);
});

// ============================================
// Category 5: Regression Tests
// ============================================

TestHarness.test('REGRESSION: Phrase should differ from single-word selection', async function() {
    EditorHelper.setContent('Bonjour monsieur. Comment allez-vous?');
    EditorHelper.selectText('monsieur');

    const selection = EditorHelper.getSelection();
    const cursor = EditorHelper.getCursor('start');
    const phrase = getSentenceAtCursor(window.editor, cursor);

    if (phrase === selection) {
        throw new Error('REGRESSION: Phrase equals selection - has_phrase will be false on backend!');
    }

    // Phrase should be the full sentence
    if (!phrase.includes('Bonjour')) {
        throw new Error(`Phrase should include "Bonjour" but got "${phrase}"`);
    }
});

TestHarness.test('REGRESSION: Paragraph should differ from phrase for multi-line content', async function() {
    const content = 'First sentence. Second sentence.\n\nThird in new paragraph.';
    EditorHelper.setContent(content);
    EditorHelper.selectText('First');

    const cursor = EditorHelper.getCursor('start');
    const phrase = getSentenceAtCursor(window.editor, cursor);
    const paragraph = extractParagraphFromEditor(window.editor, cursor.line);

    // For single-line paragraph, phrase might equal paragraph - that's OK
    // This test checks multi-line paragraphs
    if (phrase === paragraph && paragraph.includes('\n')) {
        throw new Error('For multi-line paragraphs, phrase and paragraph should differ');
    }
});

TestHarness.test('REGRESSION: Multi-word selection context extraction', async function() {
    EditorHelper.setContent('Je ne comprends pas. Pouvez-vous expliquer?');
    EditorHelper.selectText('ne comprends pas');

    const selection = EditorHelper.getSelection();
    const cursor = EditorHelper.getCursor('start');
    const phrase = getSentenceAtCursor(window.editor, cursor);

    if (selection !== 'ne comprends pas') {
        throw new Error(`Expected "ne comprends pas" but got "${selection}"`);
    }

    // Phrase should be the full sentence containing the selection
    if (!phrase.includes('Je') || !phrase.includes('comprends')) {
        throw new Error(`Phrase should be full sentence but got "${phrase}"`);
    }
});

// ============================================
// Category 6: Translation Display Tests
// ============================================

TestHarness.test('Display: Translation message shows query', async function() {
    FetchMock.clearCalls();
    clearMessages();

    FetchMock.setResponse('/api/lookup', {
        messages: [{
            type: 'translation',
            data: {
                query: 'bonjour',
                translation: 'hello',
                explanations: 'A greeting'
            }
        }],
        has_phrase: false,
        has_paragraph: false
    });

    EditorHelper.setContent('bonjour');
    EditorHelper.selectText('bonjour');

    await handleLookup();
    await sleep(100);

    DOMAssert.hasText('.message h3', 'bonjour');
});

TestHarness.test('Display: Translation message shows translation text', async function() {
    FetchMock.clearCalls();
    clearMessages();

    FetchMock.setResponse('/api/lookup', {
        messages: [{
            type: 'translation',
            data: {
                query: 'merci',
                translation: 'thank you',
                explanations: 'Expression of gratitude'
            }
        }],
        has_phrase: false,
        has_paragraph: false
    });

    EditorHelper.setContent('merci');
    EditorHelper.selectText('merci');

    await handleLookup();
    await sleep(100);

    DOMAssert.hasText('.translation-text', 'thank you');
});

TestHarness.test('Display: Translation message shows explanations', async function() {
    FetchMock.clearCalls();
    clearMessages();

    FetchMock.setResponse('/api/lookup', {
        messages: [{
            type: 'translation',
            data: {
                query: 'au revoir',
                translation: 'goodbye',
                explanations: 'Used when parting'
            }
        }],
        has_phrase: false,
        has_paragraph: false
    });

    EditorHelper.setContent('au revoir');
    EditorHelper.selectText('au revoir');

    await handleLookup();
    await sleep(100);

    DOMAssert.hasText('.explanations', 'parting');
});

// ============================================
// Category 7: Error Handling Tests
// ============================================

TestHarness.test('Error: Empty selection shows alert', async function() {
    EditorHelper.setContent('Some text here');
    EditorHelper.clearSelection();

    // Mock alert
    let alertCalled = false;
    const originalAlert = window.alert;
    window.alert = (msg) => {
        alertCalled = true;
        if (!msg.toLowerCase().includes('select')) {
            throw new Error('Alert should mention selecting text');
        }
    };

    try {
        await handleLookup();

        if (!alertCalled) {
            throw new Error('Expected alert to be called for empty selection');
        }
    } finally {
        window.alert = originalAlert;
    }
});

TestHarness.test('Error: Whitespace-only selection shows alert', async function() {
    EditorHelper.setContent('Some   text');
    // Select the whitespace between words
    const editor = EditorHelper.getEditor();
    editor.setSelection({ line: 0, ch: 4 }, { line: 0, ch: 7 });

    let alertCalled = false;
    const originalAlert = window.alert;
    window.alert = (msg) => {
        alertCalled = true;
    };

    try {
        await handleLookup();

        if (!alertCalled) {
            throw new Error('Expected alert for whitespace-only selection');
        }
    } finally {
        window.alert = originalAlert;
    }
});

TestHarness.test('Error: API error shows alert', async function() {
    FetchMock.clearCalls();
    clearMessages();

    // Set up error response
    FetchMock.setResponse('/api/lookup', { error: 'Server error' }, { ok: false, status: 500 });

    EditorHelper.setContent('test word');
    EditorHelper.selectText('test');

    let alertCalled = false;
    const originalAlert = window.alert;
    window.alert = (msg) => {
        alertCalled = true;
        if (!msg.toLowerCase().includes('error')) {
            throw new Error('Alert should mention error');
        }
    };

    try {
        await handleLookup();

        if (!alertCalled) {
            throw new Error('Expected alert for API error');
        }
    } finally {
        window.alert = originalAlert;
        // Restore normal response
        FetchMock.setResponse('/api/lookup', {
            messages: [],
            has_phrase: false,
            has_paragraph: false
        });
    }
});

// ============================================
// Category 8: Integration Flow Tests
// ============================================

TestHarness.test('Integration: Full lookup flow works end-to-end', async function() {
    FetchMock.clearCalls();
    clearMessages();

    // Set up response
    FetchMock.setResponse('/api/lookup', {
        messages: [{
            type: 'translation',
            data: {
                query: 'chien',
                translation: 'dog',
                explanations: 'A domesticated animal'
            }
        }],
        has_phrase: true,
        has_paragraph: true
    });

    // 1. Set content
    EditorHelper.setContent('Le petit chien court vite. Il est content.');

    // 2. Select word
    EditorHelper.selectText('chien');

    // 3. Trigger lookup
    await handleLookup();
    await sleep(100);

    // 4. Verify API was called with correct data
    FetchMock.assertCalled('/api/lookup', { selection: 'chien' });

    // 5. Verify translation is displayed
    DOMAssert.hasText('.message h3', 'chien');
    DOMAssert.hasText('.translation-text', 'dog');

    // 6. Verify context buttons appear
    DOMAssert.hasContextButtons(true, true);
});

TestHarness.test('Integration: Button state resets between lookups', async function() {
    FetchMock.clearCalls();
    clearMessages();

    // First lookup - with context buttons
    FetchMock.setResponse('/api/lookup', {
        messages: [{
            type: 'translation',
            data: { query: 'a', translation: 'b', explanations: 'c' }
        }],
        has_phrase: true,
        has_paragraph: true
    });

    EditorHelper.setContent('First sentence. Second here.');
    EditorHelper.selectText('First');
    await handleLookup();
    await sleep(100);

    DOMAssert.hasContextButtons(true, true);

    // Second lookup - without context buttons
    FetchMock.setResponse('/api/lookup', {
        messages: [{
            type: 'translation',
            data: { query: 'x', translation: 'y', explanations: 'z' }
        }],
        has_phrase: false,
        has_paragraph: false
    });

    EditorHelper.selectText('Second');
    await handleLookup();
    await sleep(100);

    // Old buttons should be gone
    DOMAssert.hasContextButtons(false, false);
});

TestHarness.test('Integration: Chat input is enabled after lookup', async function() {
    FetchMock.clearCalls();
    clearMessages();

    FetchMock.setResponse('/api/lookup', {
        messages: [{
            type: 'translation',
            data: { query: 'test', translation: 'test', explanations: 'test' }
        }],
        has_phrase: false,
        has_paragraph: false
    });

    EditorHelper.setContent('test word');
    EditorHelper.selectText('test');

    await handleLookup();
    await sleep(100);

    const chatInput = document.getElementById('chat-input');
    if (chatInput.disabled) {
        throw new Error('Chat input should be enabled after lookup');
    }
});

} // End of registerTests()

// ============================================
// Run Tests
// ============================================

async function runAllTests() {
    const resultsContainer = document.getElementById('test-results');
    const summaryContainer = document.getElementById('test-summary');

    if (resultsContainer) {
        resultsContainer.innerHTML = '<div class="running">Running tests...</div>';
    }
    if (summaryContainer) {
        summaryContainer.innerHTML = '';
    }

    // Wait for editor to be ready
    await waitFor(() => window.editor !== null && window.editor !== undefined, 5000);

    // Register tests (must be done before each run to support re-runs)
    registerTests();

    // Setup mocks
    setupTests();

    // Run tests
    try {
        const results = await TestHarness.runAll();
        console.log('Test results:', results);
        return results;
    } finally {
        // Teardown
        teardownTests();
    }
}

// Export for use in HTML
if (typeof window !== 'undefined') {
    window.runAllTests = runAllTests;
    window.registerTests = registerTests;
    window.setupTests = setupTests;
    window.teardownTests = teardownTests;
}
