# Development Guide

## Setup

Install development dependencies:

```bash
uv pip install -e ".[dev]"
```

## Code Quality Tools

### Quick Commands

```bash
# Format code (auto-fix issues)
./autoformat.sh

# Check code quality (no changes)
./check.sh
```

### What Gets Checked?

- **Ruff linting**: Code style, complexity, best practices
- **Ruff formatting**: Consistent code formatting (replaces black + isort)
- **Mypy** (optional): Type checking

### Manual Commands

```bash
# Lint only
ruff check src/ tests/

# Format only
ruff format src/ tests/

# Auto-fix linting issues
ruff check --fix src/ tests/

# Type check
mypy src/
```

## Tools Used

- **Ruff**: Fast Python linter & formatter (replaces black, isort, flake8, pyupgrade)
- **Mypy**: Optional static type checker
