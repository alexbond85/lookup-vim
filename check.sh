#!/bin/bash
set -e

echo '🔧 Running code quality checks and fixes...'
echo ''

# Ruff linting with auto-fix
echo '📋 Linting and fixing with ruff...'
uv run ruff check --fix src/ tests/

# Ruff formatting (auto-formats files)
echo '🎨 Formatting with ruff...'
uv run ruff format src/ tests/

# mypy type checking (cannot auto-fix)
echo '🔎 Type checking with mypy...'
uv run mypy src/

echo ''
echo '✅ All checks passed!'

