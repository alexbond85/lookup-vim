/**
 * Unit tests for context-extractor.js
 * Open this file in a browser to run tests (after including context-extractor.js)
 */

// Test framework
const tests = [];
let passed = 0;
let failed = 0;

function test(name, fn) {
    tests.push({ name, fn });
}

function assertEqual(actual, expected, message) {
    if (actual !== expected) {
        throw new Error(`${message}\n  Expected: "${expected}"\n  Actual:   "${actual}"`);
    }
}

function runTests() {
    const results = document.getElementById('results') || document.body;
    results.innerHTML = '<h1>Context Extractor Tests</h1>';

    tests.forEach(t => {
        try {
            t.fn();
            passed++;
            results.innerHTML += `<div style="color: green;">✓ ${t.name}</div>`;
        } catch (e) {
            failed++;
            results.innerHTML += `<div style="color: red;">✗ ${t.name}<pre>${e.message}</pre></div>`;
        }
    });

    results.innerHTML += `<h2>${passed} passed, ${failed} failed</h2>`;
    console.log(`Tests: ${passed} passed, ${failed} failed`);
}

// =============================================================================
// Test 1: Single-word selection in middle of sentence
// =============================================================================
test('Test 1: Single-word selection in middle of sentence', function() {
    const text = "Bonjour monsieur. Comment allez-vous?";

    // Cursor on "monsieur" - position 8 (0-indexed)
    const cursorOffset = 8;

    const sentence = extractSentence(text, cursorOffset);
    const paragraph = extractParagraph(text);

    assertEqual(sentence, "Bonjour monsieur.", "Sentence extraction");
    assertEqual(paragraph, "Bonjour monsieur. Comment allez-vous?", "Paragraph extraction");
});

// =============================================================================
// Test 2: Selection at start of sentence
// =============================================================================
test('Test 2: Selection at start of sentence', function() {
    const text = "Bonjour monsieur. Comment allez-vous?";

    // Cursor on "Comment" - position 18
    const cursorOffset = 18;

    const sentence = extractSentence(text, cursorOffset);

    assertEqual(sentence, "Comment allez-vous?", "Sentence extraction for second sentence");
});

// =============================================================================
// Test 3: Multi-line paragraph
// =============================================================================
test('Test 3: Multi-line paragraph', function() {
    const lines = [
        "Ceci est la première ligne.",
        "Ceci est la deuxième ligne.",
        "Ceci est la troisième ligne.",
        "",
        "Un nouveau paragraphe ici."
    ];

    // Mock editor for extractParagraphFromLines
    const mockEditor = {
        lines: lines,
        getLine: function(n) { return this.lines[n] || ''; },
        lineCount: function() { return this.lines.length; }
    };

    // Selection on line 1 (0-indexed), "deuxième"
    const lineIndex = 1;
    const paragraph = extractParagraphFromEditor(mockEditor, lineIndex);

    assertEqual(
        paragraph,
        "Ceci est la première ligne. Ceci est la deuxième ligne. Ceci est la troisième ligne.",
        "Multi-line paragraph extraction"
    );

    // Calculate cursor offset for "deuxième" in the joined paragraph
    // "Ceci est la première ligne. " = 28 chars, then "Ceci est la " = 12 chars = offset 40
    const cursorOffset = 40;
    const sentence = extractSentence(paragraph, cursorOffset);

    assertEqual(sentence, "Ceci est la deuxième ligne.", "Sentence from line 2");
});

// =============================================================================
// Test 4: Multiple sentences in one line
// =============================================================================
test('Test 4: Multiple sentences in one line', function() {
    const text = "Premier. Deuxième. Troisième.";

    // Cursor on "Deuxième" - position 9 (after "Premier. ")
    const cursorOffset = 9;

    const sentence = extractSentence(text, cursorOffset);
    const paragraph = extractParagraph(text);

    assertEqual(sentence, "Deuxième.", "Middle sentence extraction");
    assertEqual(paragraph, "Premier. Deuxième. Troisième.", "Full line as paragraph");
});

// =============================================================================
// Test 5: Selection spanning multiple words
// =============================================================================
test('Test 5: Selection spanning multiple words', function() {
    const text = "Il était une fois un grand château.";

    // Cursor on "une" - position 10
    const cursorOffset = 10;

    const sentence = extractSentence(text, cursorOffset);
    const paragraph = extractParagraph(text);

    assertEqual(sentence, "Il était une fois un grand château.", "Full sentence");
    assertEqual(paragraph, "Il était une fois un grand château.", "Single sentence paragraph");
});

// =============================================================================
// Additional edge case tests
// =============================================================================
test('Test 6: Sentence at very beginning', function() {
    const text = "First sentence. Second sentence.";
    const cursorOffset = 0;

    const sentence = extractSentence(text, cursorOffset);
    assertEqual(sentence, "First sentence.", "Sentence at position 0");
});

test('Test 7: Sentence at very end', function() {
    const text = "First. Second. Third.";
    const cursorOffset = 15; // On "Third"

    const sentence = extractSentence(text, cursorOffset);
    assertEqual(sentence, "Third.", "Last sentence");
});

test('Test 8: No punctuation (single sentence)', function() {
    const text = "This is a sentence without ending punctuation";
    const cursorOffset = 10;

    const sentence = extractSentence(text, cursorOffset);
    assertEqual(sentence, "This is a sentence without ending punctuation", "No punctuation case");
});

test('Test 9: Exclamation and question marks', function() {
    const text = "Hello! How are you? I am fine.";

    // Cursor on "How"
    let sentence = extractSentence(text, 7);
    assertEqual(sentence, "How are you?", "Question mark boundary");

    // Cursor on "Hello"
    sentence = extractSentence(text, 0);
    assertEqual(sentence, "Hello!", "Exclamation mark boundary");
});

test('Test 10: Empty paragraph boundaries', function() {
    const lines = [
        "",
        "Middle paragraph line 1.",
        "Middle paragraph line 2.",
        "",
        "Next paragraph."
    ];

    const mockEditor = {
        lines: lines,
        getLine: function(n) { return this.lines[n] || ''; },
        lineCount: function() { return this.lines.length; }
    };

    const paragraph = extractParagraphFromEditor(mockEditor, 1);
    assertEqual(
        paragraph,
        "Middle paragraph line 1. Middle paragraph line 2.",
        "Paragraph bounded by empty lines"
    );
});

// Run tests when page loads
if (typeof window !== 'undefined') {
    window.addEventListener('DOMContentLoaded', runTests);
}
