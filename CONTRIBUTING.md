# Contributing to robert-dict

Thank you for your interest in contributing to robert-dict! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Setting Up Development Environment

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd robert-online
   ```

2. **Install dependencies**:
   ```bash
   uv pip install -e ".[dev]"
   ```

3. **Run tests to verify setup**:
   ```bash
   pytest
   ```

## Development Workflow

### Code Style and Standards

- **Follow PEP 8**: Python code should follow PEP 8 style guidelines
- **Type hints**: All functions should have type hints for parameters and return values
- **Docstrings**: All public functions and classes must have docstrings
- **KISS principle**: Keep code simple and readable; avoid unnecessary complexity

### Architecture

Please read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the project structure and design patterns before making significant changes.

Key principles:
- **Protocol-based design**: Use `typing.Protocol` for interface definitions
- **Dependency injection**: Components receive their dependencies via constructor
- **Separation of concerns**: Keep scraping, formatting, and CLI logic separate

### Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Write clean, well-documented code
   - Add type hints to all functions
   - Follow existing patterns in the codebase

3. **Write tests**:
   - Add unit tests for new functionality
   - Ensure test coverage remains high (aim for 80%+)
   - Run tests: `pytest`
   - Check coverage: `pytest --cov=robert_dict --cov-report=html`

4. **Test manually**:
   ```bash
   robert-dict bien
   robert-dict maison --format json
   robert-dict écrivaient
   ```

5. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add description of your feature"
   ```

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring without changing functionality
- `style:` - Code style changes (formatting, etc.)
- `chore:` - Maintenance tasks

Examples:
```
feat: add synonym lookup functionality
fix: handle network timeout gracefully
docs: update README with new examples
test: add tests for conjugation handling
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_models.py

# Run specific test
pytest tests/test_models.py::test_definition_creation

# Run with coverage
pytest --cov=robert_dict --cov-report=html
```

### Test Coverage

- Aim for 80%+ overall coverage
- Core business logic (service, models) should have 90%+ coverage
- Write both unit tests (with mocks) and integration tests

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Use descriptive test names: `test_<what>_<condition>_<expected_result>`
- Use fixtures from `conftest.py` for common test data
- Mock external dependencies (network calls, file system)

Example:
```python
def test_service_lookup_returns_formatted_result(sample_word_result):
    """Test that service.lookup returns properly formatted result"""
    scraper = MockScraper(result=sample_word_result)
    printer = MockPrinter(output="formatted")
    service = DictionaryService(scraper, printer)
    
    result = service.lookup("test")
    
    assert result == "formatted"
```

## Adding New Features

### Adding a New Scraper

1. Create a new file in `src/robert_dict/scrapers/`
2. Implement the `Scraper` protocol (see `scrapers/base.py`)
3. Add tests in `tests/test_scrapers.py`
4. Update CLI to support the new scraper

### Adding a New Output Format

1. Create a new file in `src/robert_dict/printers/`
2. Implement the `Printer` protocol (see `printers/base.py`)
3. Add tests in `tests/test_printers.py`
4. Update CLI argument parser to include the new format

### Adding a New Feature to Scraper

1. Update the relevant model in `models.py` if needed
2. Implement the scraping logic in `scrapers/lerobert.py`
3. Update printers to handle the new data
4. Add tests for the new functionality
5. Update README with examples

## Code Review Checklist

Before submitting a PR, ensure:

- [ ] Code follows PEP 8 style guidelines
- [ ] All functions have type hints
- [ ] All public APIs have docstrings
- [ ] Tests are added for new functionality
- [ ] All tests pass: `pytest`
- [ ] Test coverage hasn't decreased
- [ ] Code is well-commented where necessary
- [ ] README is updated if adding user-facing features
- [ ] No hardcoded values (use constants)
- [ ] Error handling is appropriate
- [ ] Logging is added for important operations

## Questions or Issues?

- Open an issue on GitHub for bugs or feature requests
- Check existing issues before opening a new one
- Provide detailed information: steps to reproduce, expected vs actual behavior, etc.

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).

