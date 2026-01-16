/**
 * Test Harness for nvim-lookup web app integration tests
 * Provides: TestHarness, FetchMock, EditorHelper, DOMAssert
 */

// ============================================
// TestHarness: Async test runner
// ============================================
const TestHarness = {
    tests: [],
    results: [],

    /**
     * Register a test
     * @param {string} name - Test name
     * @param {Function} fn - Async test function
     */
    test(name, fn) {
        this.tests.push({ name, fn });
    },

    /**
     * Run all registered tests
     * @returns {Promise<{passed: number, failed: number, results: Array}>}
     */
    async runAll() {
        this.results = [];
        let passed = 0;
        let failed = 0;

        for (const test of this.tests) {
            const result = { name: test.name, passed: false, error: null };

            try {
                await test.fn();
                result.passed = true;
                passed++;
            } catch (error) {
                result.passed = false;
                result.error = error.message || String(error);
                failed++;
            }

            this.results.push(result);
            this._updateUI(result);
        }

        this._showSummary(passed, failed);
        return { passed, failed, results: this.results };
    },

    /**
     * Clear all registered tests
     */
    clear() {
        this.tests = [];
        this.results = [];
    },

    /**
     * Update UI with test result
     */
    _updateUI(result) {
        const container = document.getElementById('test-results');
        if (!container) return;

        const div = document.createElement('div');
        div.className = 'test-result ' + (result.passed ? 'passed' : 'failed');

        const icon = result.passed ? '\u2713' : '\u2717';
        div.innerHTML = `
            <span class="test-icon">${icon}</span>
            <span class="test-name">${escapeHtml(result.name)}</span>
            ${result.error ? `<pre class="test-error">${escapeHtml(result.error)}</pre>` : ''}
        `;

        container.appendChild(div);
    },

    /**
     * Show test summary
     */
    _showSummary(passed, failed) {
        const container = document.getElementById('test-summary');
        if (!container) return;

        const total = passed + failed;
        container.innerHTML = `
            <strong>Results:</strong> ${passed}/${total} tests passed
            ${failed > 0 ? ` (${failed} failed)` : ''}
        `;
        container.className = 'test-summary ' + (failed === 0 ? 'all-passed' : 'has-failures');
    }
};

// ============================================
// FetchMock: Intercept API calls
// ============================================
const FetchMock = {
    _originalFetch: null,
    _responses: {},
    _calls: [],
    _installed: false,

    /**
     * Install the fetch mock
     */
    install() {
        if (this._installed) return;

        this._originalFetch = window.fetch;
        this._calls = [];

        window.fetch = async (url, options = {}) => {
            const urlPath = typeof url === 'string' ? url : url.toString();

            // Record the call
            let body = null;
            if (options.body) {
                try {
                    body = JSON.parse(options.body);
                } catch {
                    body = options.body;
                }
            }

            this._calls.push({
                url: urlPath,
                method: options.method || 'GET',
                headers: options.headers || {},
                body: body
            });

            // Find matching response
            const response = this._responses[urlPath];
            if (response) {
                return {
                    ok: response.ok !== false,
                    status: response.status || 200,
                    json: async () => response.data,
                    text: async () => JSON.stringify(response.data)
                };
            }

            // Default 404 response
            return {
                ok: false,
                status: 404,
                json: async () => ({ error: 'Not found' }),
                text: async () => 'Not found'
            };
        };

        this._installed = true;
    },

    /**
     * Uninstall the fetch mock and restore original fetch
     */
    uninstall() {
        if (!this._installed) return;

        window.fetch = this._originalFetch;
        this._originalFetch = null;
        this._installed = false;
    },

    /**
     * Set a mock response for a URL
     * @param {string} url - URL path to mock
     * @param {Object} data - Response data
     * @param {Object} options - Optional: { ok, status }
     */
    setResponse(url, data, options = {}) {
        this._responses[url] = {
            data: data,
            ok: options.ok !== false,
            status: options.status || 200
        };
    },

    /**
     * Clear all mock responses
     */
    clearResponses() {
        this._responses = {};
    },

    /**
     * Clear recorded calls
     */
    clearCalls() {
        this._calls = [];
    },

    /**
     * Get all recorded calls
     */
    getCalls() {
        return [...this._calls];
    },

    /**
     * Get calls to a specific URL
     */
    getCallsTo(url) {
        return this._calls.filter(c => c.url === url);
    },

    /**
     * Assert that a URL was called with expected body
     * @param {string} url - URL to check
     * @param {Object} expectedBody - Expected request body (partial match)
     */
    assertCalled(url, expectedBody = null) {
        const calls = this.getCallsTo(url);

        if (calls.length === 0) {
            throw new Error(`Expected fetch to "${url}" but it was not called`);
        }

        if (expectedBody) {
            const lastCall = calls[calls.length - 1];
            for (const [key, value] of Object.entries(expectedBody)) {
                if (lastCall.body[key] !== value) {
                    throw new Error(
                        `Expected "${url}" to be called with ${key}="${value}" ` +
                        `but got ${key}="${lastCall.body[key]}"`
                    );
                }
            }
        }
    },

    /**
     * Assert that a URL was NOT called
     */
    assertNotCalled(url) {
        const calls = this.getCallsTo(url);
        if (calls.length > 0) {
            throw new Error(`Expected fetch to "${url}" to not be called but it was called ${calls.length} times`);
        }
    },

    /**
     * Reset everything (responses and calls)
     */
    reset() {
        this.clearResponses();
        this.clearCalls();
    }
};

// ============================================
// EditorHelper: Programmatic CodeMirror control
// ============================================
const EditorHelper = {
    /**
     * Get the CodeMirror editor instance
     */
    getEditor() {
        return window.editor;
    },

    /**
     * Set editor content
     * @param {string} content - Text content to set
     */
    setContent(content) {
        const editor = this.getEditor();
        if (!editor) throw new Error('Editor not initialized');
        editor.setValue(content);
    },

    /**
     * Get editor content
     */
    getContent() {
        const editor = this.getEditor();
        if (!editor) throw new Error('Editor not initialized');
        return editor.getValue();
    },

    /**
     * Select text by finding it in the editor
     * Simulates vim visual mode selection
     * @param {string} text - Text to select
     * @param {number} occurrence - Which occurrence (0-based, default 0)
     */
    selectText(text, occurrence = 0) {
        const editor = this.getEditor();
        if (!editor) throw new Error('Editor not initialized');

        const content = editor.getValue();
        let index = -1;
        let count = 0;

        // Find the nth occurrence
        let searchPos = 0;
        while (count <= occurrence) {
            index = content.indexOf(text, searchPos);
            if (index === -1) break;
            if (count === occurrence) break;
            searchPos = index + 1;
            count++;
        }

        if (index === -1) {
            throw new Error(`Text "${text}" not found in editor (occurrence ${occurrence})`);
        }

        const from = editor.posFromIndex(index);
        const to = editor.posFromIndex(index + text.length);

        // Set the selection (simulates vim visual mode result)
        editor.setSelection(from, to);
    },

    /**
     * Select a range by line and character positions
     * @param {number} fromLine - Start line (0-based)
     * @param {number} fromCh - Start character
     * @param {number} toLine - End line (0-based)
     * @param {number} toCh - End character
     */
    selectRange(fromLine, fromCh, toLine, toCh) {
        const editor = this.getEditor();
        if (!editor) throw new Error('Editor not initialized');

        editor.setSelection(
            { line: fromLine, ch: fromCh },
            { line: toLine, ch: toCh }
        );
    },

    /**
     * Get current selection text
     */
    getSelection() {
        const editor = this.getEditor();
        if (!editor) throw new Error('Editor not initialized');
        return editor.getSelection();
    },

    /**
     * Get cursor position
     * @param {string} which - 'start', 'end', 'head', or 'anchor'
     */
    getCursor(which = 'start') {
        const editor = this.getEditor();
        if (!editor) throw new Error('Editor not initialized');
        return editor.getCursor(which);
    },

    /**
     * Clear selection
     */
    clearSelection() {
        const editor = this.getEditor();
        if (!editor) throw new Error('Editor not initialized');

        const cursor = editor.getCursor('start');
        editor.setCursor(cursor);
    },

    /**
     * Set cursor position
     * @param {number} line - Line number (0-based)
     * @param {number} ch - Character position
     */
    setCursor(line, ch) {
        const editor = this.getEditor();
        if (!editor) throw new Error('Editor not initialized');
        editor.setCursor({ line, ch });
    }
};

// ============================================
// DOMAssert: Verify UI state
// ============================================
const DOMAssert = {
    /**
     * Assert that context buttons exist (or don't exist)
     * @param {boolean} expectPhrase - Expect phrase button to exist
     * @param {boolean} expectParagraph - Expect paragraph button to exist
     */
    hasContextButtons(expectPhrase, expectParagraph) {
        const buttons = document.querySelectorAll('.context-btn');
        const buttonTexts = Array.from(buttons).map(b => b.textContent);

        const hasPhraseBtn = buttonTexts.some(t => t.includes('sentence') || t.includes('phrase'));
        const hasParagraphBtn = buttonTexts.some(t => t.includes('paragraph'));

        if (expectPhrase && !hasPhraseBtn) {
            throw new Error('Expected phrase/sentence button but it was not found. Buttons: ' + buttonTexts.join(', '));
        }
        if (!expectPhrase && hasPhraseBtn) {
            throw new Error('Did not expect phrase/sentence button but it was found');
        }
        if (expectParagraph && !hasParagraphBtn) {
            throw new Error('Expected paragraph button but it was not found. Buttons: ' + buttonTexts.join(', '));
        }
        if (!expectParagraph && hasParagraphBtn) {
            throw new Error('Did not expect paragraph button but it was found');
        }
    },

    /**
     * Assert that an element contains specific text
     * @param {string} selector - CSS selector
     * @param {string} text - Expected text (substring match)
     */
    hasText(selector, text) {
        const elements = document.querySelectorAll(selector);
        const found = Array.from(elements).some(el => el.textContent.includes(text));

        if (!found) {
            const actualTexts = Array.from(elements).map(el => el.textContent.substring(0, 100));
            throw new Error(
                `Expected "${selector}" to contain "${text}" but found: ` +
                (actualTexts.length ? actualTexts.join(' | ') : '(no elements matched)')
            );
        }
    },

    /**
     * Assert that an element exists
     * @param {string} selector - CSS selector
     */
    exists(selector) {
        const element = document.querySelector(selector);
        if (!element) {
            throw new Error(`Expected element "${selector}" to exist but it was not found`);
        }
    },

    /**
     * Assert that an element does NOT exist
     * @param {string} selector - CSS selector
     */
    notExists(selector) {
        const element = document.querySelector(selector);
        if (element) {
            throw new Error(`Expected element "${selector}" to not exist but it was found`);
        }
    },

    /**
     * Assert element count
     * @param {string} selector - CSS selector
     * @param {number} count - Expected count
     */
    hasCount(selector, count) {
        const elements = document.querySelectorAll(selector);
        if (elements.length !== count) {
            throw new Error(`Expected ${count} "${selector}" elements but found ${elements.length}`);
        }
    },

    /**
     * Assert that an element is visible
     * @param {string} selector - CSS selector
     */
    isVisible(selector) {
        const element = document.querySelector(selector);
        if (!element) {
            throw new Error(`Element "${selector}" not found`);
        }

        const style = window.getComputedStyle(element);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
            throw new Error(`Expected element "${selector}" to be visible but it is hidden`);
        }
    },

    /**
     * Assert that an element has a specific class
     * @param {string} selector - CSS selector
     * @param {string} className - Expected class name
     */
    hasClass(selector, className) {
        const element = document.querySelector(selector);
        if (!element) {
            throw new Error(`Element "${selector}" not found`);
        }
        if (!element.classList.contains(className)) {
            throw new Error(`Expected "${selector}" to have class "${className}" but it has: ${element.className}`);
        }
    },

    /**
     * Get text content of an element
     * @param {string} selector - CSS selector
     */
    getText(selector) {
        const element = document.querySelector(selector);
        if (!element) {
            throw new Error(`Element "${selector}" not found`);
        }
        return element.textContent;
    }
};

// ============================================
// Utility Functions
// ============================================

/**
 * Wait for a condition to be true
 * @param {Function} condition - Function that returns boolean
 * @param {number} timeout - Max wait time in ms
 * @param {number} interval - Check interval in ms
 */
async function waitFor(condition, timeout = 5000, interval = 50) {
    const start = Date.now();

    while (Date.now() - start < timeout) {
        if (condition()) {
            return true;
        }
        await sleep(interval);
    }

    throw new Error('Timeout waiting for condition');
}

/**
 * Sleep for specified milliseconds
 * @param {number} ms - Milliseconds to sleep
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Escape HTML special characters
 * @param {string} text - Text to escape
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Clear the chat messages container
 */
function clearMessages() {
    const container = document.getElementById('chat-messages');
    if (container) {
        container.innerHTML = '';
    }
}

// Export for use in tests
if (typeof window !== 'undefined') {
    window.TestHarness = TestHarness;
    window.FetchMock = FetchMock;
    window.EditorHelper = EditorHelper;
    window.DOMAssert = DOMAssert;
    window.waitFor = waitFor;
    window.sleep = sleep;
    window.clearMessages = clearMessages;
}
