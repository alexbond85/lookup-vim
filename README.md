# robert-dict

A simple CLI tool to fetch French word definitions from [Le Robert dictionary](https://dictionnaire.lerobert.com).

## Features

- Fetch word definitions from Le Robert online dictionary
- Get usage examples and word combinations
- JSON output for easy parsing and integration
- Simple, KISS-principle design
- Extensible architecture for future features (synonyms, conjugations)

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management. If you don't have `uv` installed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then install the project:

```bash
# Clone or navigate to the project directory
cd robert-online

# Install dependencies and the package
uv pip install -e .
```

## Usage

### Basic Usage

Look up a French word:

```bash
robert-dict bien
```

### Command-Line Options

```bash
robert-dict --help
```

- `word`: The French word to look up (required)
- `--indent N`: JSON indentation level (default: 2)

### Examples

**Look up "bien":**

```bash
robert-dict bien
```

**Look up a multi-word phrase:**

```bash
robert-dict "bien que"
```

**Compact JSON output:**

```bash
robert-dict maison --indent 0
```

**Save output to a file:**

```bash
robert-dict bonjour > bonjour_definition.json
```

## Output Format

### For Definitions

The tool outputs a JSON object with the following structure:

```json
{
  "original_word": "bien",
  "word": "bien",
  "url": "https://dictionnaire.lerobert.com/definition/bien",
  "definitions": [
    {
      "category": "adverbe et adjectif invariable",
      "definition": "D'une manière satisfaisante.",
      "examples": [
        "Elle danse bien.",
        "Il a très bien réussi.",
        "Comment vas-tu ? Bien."
      ]
    },
    {
      "category": "nom masculin",
      "definition": "Ce qui est utile, bon, agréable.",
      "examples": [
        "Ce remède lui a fait (le plus) grand bien.",
        "Le bien commun."
      ]
    }
  ],
  "usage_examples": [
    "Et bien évidemment, ces mesures sont actuellement difficiles à prendre.",
    "Cette forme d'écriture polyphonique suggère une familiarité..."
  ],
  "word_combinations": [
    "abandonner + bien",
    "acheter + bien",
    "avoir + bien",
    "bien agricole",
    "bien commun"
  ]
}
```

### For Conjugated Forms

When you look up a conjugated verb form (e.g., "écrivaient"), the tool automatically follows the conjugation page to fetch the definition of the base verb. The `original_word` field will show what you searched for, while `word` will show the base form:

```json
{
  "original_word": "écrivaient",
  "word": "écrire",
  "url": "https://dictionnaire.lerobert.com/definition/ecrire",
  "definitions": [
    {
      "category": "verbe transitif",
      "definition": "Tracer (des signes d'écriture, un ensemble organisé de ces signes).",
      "examples": [
        "Écrire quelques mots.",
        "Apprendre à écrire.",
        "Il ne sait ni lire ni écrire."
      ]
    }
  ],
  "usage_examples": [...],
  "word_combinations": [...]
}
```

**Note:** For regular words, `original_word` and `word` will be the same.

## Error Handling

- **Word not found (404)**: Returns error JSON with exit code 1
- **Network errors**: Returns error JSON with exit code 2

Error messages are printed to stderr in JSON format.

## Development

Want to contribute? Check out our [Contributing Guide](CONTRIBUTING.md) and [Architecture Documentation](ARCHITECTURE.md).

### Quick Start for Developers

```bash
# Install with development dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=robert_dict --cov-report=html

# Enable verbose logging
robert-dict bien --verbose
```

### Project Structure

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed documentation.

Key directories:
- `src/robert_dict/` - Main package code
- `tests/` - Test suite
- `vim/` - Vim plugin (optional)

### Design Principles

- **KISS (Keep It Simple, Stupid)**: Single-purpose functions, minimal abstractions
- **Protocol-based design**: Use `typing.Protocol` for interfaces
- **Dependency Injection**: Components receive dependencies via constructor
- **Separation of Concerns**: Clear boundaries between scraping, formatting, and CLI

## Requirements

- Python 3.11+
- requests
- beautifulsoup4
- lxml

## License

MIT

