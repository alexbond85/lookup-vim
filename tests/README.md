# Tests

This directory contains the test suite for robert-dict.

## Running Tests

Install test dependencies:

```bash
uv pip install -e ".[dev]"
```

Run all tests:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=robert_dict --cov-report=html
```

Run specific test file:

```bash
pytest tests/test_models.py
```

Run specific test:

```bash
pytest tests/test_models.py::test_definition_creation
```

## Test Structure

- `conftest.py` - Shared fixtures and pytest configuration
- `test_models.py` - Tests for domain models (Definition, WordResult, etc.)
- `test_service.py` - Tests for DictionaryService with mocked dependencies
- `test_printers.py` - Tests for text and JSON formatters
- `test_cli.py` - Tests for command-line interface

## Writing Tests

### Fixtures

Common fixtures are defined in `conftest.py`:
- `sample_definition` - A sample Definition object
- `sample_word_result` - A sample WordResult with multiple definitions
- `sample_conjugation_result` - A sample ConjugationResult

### Mocking

For unit tests, we use mocks to isolate components:
- `MockScraper` - Mock scraper for testing service layer
- `MockPrinter` - Mock printer for testing service layer
- Use `unittest.mock.patch` for mocking external dependencies

### Integration Tests

Integration tests (marked with `@pytest.mark.integration`) test against the real Le Robert website and should be run sparingly to avoid overloading their servers.

Run only unit tests (skip integration):

```bash
pytest -m "not integration"
```

Run only integration tests:

```bash
pytest -m integration
```

## Coverage Goals

Aim for:
- 80%+ overall coverage
- 90%+ for core business logic (service, models)
- 70%+ for scrapers (due to external dependencies)

