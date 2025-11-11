# Architecture

This document describes the architecture and design principles of robert-dict.

## Overview

robert-dict is a CLI tool that fetches French word definitions from Le Robert online dictionary. The architecture follows clean code principles with clear separation of concerns and protocol-based design for extensibility.

## Design Principles

### 1. KISS (Keep It Simple, Stupid)
- Single-purpose functions with clear responsibilities
- Minimal abstractions - only abstract when there's a clear benefit
- Readable code over clever code

### 2. Protocol-Based Design
- Use `typing.Protocol` to define interfaces
- Enables duck typing with type safety
- Easy to add new implementations without modifying existing code

### 3. Dependency Injection
- Components receive dependencies via constructor
- Makes testing easier with mock objects
- Loose coupling between components

### 4. Separation of Concerns
- **Scrapers**: Fetch data from external sources
- **Models**: Domain objects (data structures)
- **Printers**: Format data for output
- **Service**: Orchestrate scraping and printing
- **CLI**: User interface and argument parsing

## Directory Structure

```
robert-online/
├── src/robert_dict/           # Main package
│   ├── __init__.py
│   ├── cli.py                 # CLI entry point
│   ├── service.py             # Service layer (orchestration)
│   ├── models.py              # Domain models (dataclasses)
│   ├── constants.py           # Application constants
│   ├── scrapers/              # Data fetching implementations
│   │   ├── __init__.py
│   │   ├── base.py            # Scraper protocol definition
│   │   └── lerobert.py        # Le Robert scraper implementation
│   └── printers/              # Output formatters
│       ├── __init__.py
│       ├── base.py            # Printer protocol definition
│       ├── text.py            # Text formatter (console output)
│       └── json.py            # JSON formatter
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── conftest.py            # Shared fixtures
│   ├── test_models.py
│   ├── test_service.py
│   ├── test_printers.py
│   └── test_cli.py
├── vim/                       # Vim plugin (separate component)
│   └── robert-dict.vim
├── pyproject.toml             # Project configuration
└── README.md                  # User documentation
```

## Core Components

### 1. Models (`models.py`)

Domain objects using Python dataclasses:

- **`Definition`**: A single word definition with category and examples
- **`WordResult`**: Complete word lookup result with definitions, examples, and combinations
- **`ConjugationResult`**: Result when a conjugated verb form is looked up

These are pure data structures with no business logic.

### 2. Protocols (`scrapers/base.py`, `printers/base.py`)

Define interfaces that implementations must satisfy:

- **`Scraper` Protocol**: Defines `fetch(word: str)` method
- **`Printer` Protocol**: Defines `print(result)` method

Using protocols instead of abstract base classes provides:
- Duck typing with type checking
- No need to inherit from base classes
- More Pythonic and flexible

### 3. Scrapers (`scrapers/`)

Responsible for fetching data from external sources:

**LeRobertScraper** (`lerobert.py`):
- Fetches HTML from Le Robert dictionary
- Parses HTML using BeautifulSoup
- Handles different page types (definitions vs conjugations)
- Follows redirects when necessary
- Returns structured data (WordResult or ConjugationResult)

Key methods:
- `fetch(word)`: Main entry point
- `_fetch_html(url)`: HTTP request handling
- `_extract_definitions(soup)`: Parse definition blocks
- `_extract_examples(soup)`: Parse usage examples
- `_extract_combinations(soup)`: Parse word combinations

### 4. Printers (`printers/`)

Format structured data for output:

**TextPrinter** (`text.py`):
- Formats results for beautiful console output
- Uses Unicode box-drawing characters
- Color-coded sections (when supported)
- Human-readable layout

**JsonPrinter** (`json.py`):
- Formats results as JSON
- Preserves French characters (ensure_ascii=False)
- Configurable indentation
- Machine-readable output for integrations

### 5. Service Layer (`service.py`)

Orchestrates scraping and printing:

**DictionaryService**:
- Takes a Scraper and Printer via dependency injection
- Coordinates the lookup workflow
- Delegates to scraper for data fetching
- Delegates to printer for formatting
- Returns formatted string

This layer keeps CLI logic separate from business logic.

### 6. CLI (`cli.py`)

Command-line interface:
- Argument parsing (argparse)
- Creates scraper, printer, and service instances
- Error handling with appropriate exit codes
- Structured logging
- Outputs to stdout (success) or stderr (errors)

**Exit Codes**:
- `0`: Success
- `1`: Word not found
- `2`: General error (network, parsing, etc.)

### 7. Constants (`constants.py`)

Centralized constants:
- `ExitCode`: Enum for CLI exit codes
- `BASE_URL`: Le Robert dictionary URL
- `DEFAULT_TIMEOUT`: HTTP request timeout
- `DEFAULT_JSON_INDENT`: Default JSON indentation

## Data Flow

```
┌──────────┐
│   CLI    │  Parse arguments, setup logging
└────┬─────┘
     │
     ▼
┌──────────────────┐
│ DictionaryService│  Orchestration layer
└─────┬────────┬───┘
      │        │
      │        └─────────────┐
      │                      │
      ▼                      ▼
┌─────────────┐       ┌──────────┐
│   Scraper   │       │ Printer  │
│ (LeRobert)  │       │ (Text/   │
│             │       │  JSON)   │
└─────┬───────┘       └────┬─────┘
      │                    │
      │ Fetch HTML         │ Format
      │ Parse              │ Output
      ▼                    │
┌─────────────┐            │
│ WordResult  │────────────┘
│ or Conj.    │
│ Result      │
└─────────────┘
```

### Example Flow:

1. User runs: `robert-dict bien --format json`
2. CLI parses arguments
3. CLI creates:
   - `LeRobertScraper()` 
   - `JsonPrinter(indent=2)`
   - `DictionaryService(scraper, printer)`
4. CLI calls `service.lookup("bien")`
5. Service calls `scraper.fetch("bien")`
6. Scraper fetches and parses HTML, returns `WordResult`
7. Service calls `printer.print(word_result)`
8. Printer formats as JSON string
9. CLI prints result to stdout

## Error Handling

### Error Strategy

1. **ValueError**: Used for expected errors (word not found)
2. **requests.RequestException**: Network errors
3. **Exception**: Catch-all for unexpected errors

### Error Propagation

- Scrapers raise errors
- Service propagates errors (no catching)
- CLI catches and formats errors appropriately
- Exit codes indicate error type

### Logging

- **DEBUG**: Detailed information (--verbose flag)
- **WARNING**: Word not found, non-critical issues
- **ERROR**: Network errors, parsing failures

## Extensibility

### Adding a New Dictionary Source

1. Create `scrapers/new_source.py`
2. Implement `Scraper` protocol:
   ```python
   class NewSourceScraper:
       def fetch(self, word: str) -> Union[WordResult, ConjugationResult]:
           # Implementation
           pass
   ```
3. Update CLI to allow source selection

### Adding a New Output Format

1. Create `printers/new_format.py`
2. Implement `Printer` protocol:
   ```python
   class NewFormatPrinter:
       def print(self, result: Union[WordResult, ConjugationResult]) -> str:
           # Implementation
           pass
   ```
3. Update CLI argument parser

### Adding New Data Fields

1. Update models in `models.py`
2. Update scraper to extract new data
3. Update printers to display new data
4. Tests will catch any missing implementations

## Testing Strategy

### Unit Tests
- Test each component in isolation
- Use mocks for dependencies
- Fast, deterministic tests

### Integration Tests
- Test against real Le Robert website (sparingly)
- Mark with `@pytest.mark.integration`
- Run separately from unit tests

### Test Organization
- One test file per module
- Shared fixtures in `conftest.py`
- Mock classes for testing (MockScraper, MockPrinter)

## Future Enhancements

Potential features that fit the architecture:

1. **Synonyms**: Add to WordResult model, extract in scraper
2. **Antonyms**: Similar to synonyms
3. **Pronunciation**: Add audio URL to WordResult
4. **Caching**: Add caching layer to Service
5. **Multiple dictionaries**: Add source parameter to CLI
6. **Word history**: Track lookup history

All can be added without major architectural changes.

## Vim Plugin

The Vim plugin (`vim/robert-dict.vim`) is a separate component that:
- Calls the CLI tool (`robert-dict`)
- Displays results in a Vim popup
- Provides key bindings for quick lookups

It's loosely coupled to the CLI and communicates via stdin/stdout.

