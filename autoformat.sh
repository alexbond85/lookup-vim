#!/bin/bash
set -e

if ! command -v ruff &> /dev/null; then
    echo "❌ ruff not found. Install with: uv pip install ruff"
    exit 1
fi

echo '🎨 Auto-formatting code with ruff...'
# ruff format src/ tests/
ruff format src/ 

echo '🔧 Fixing auto-fixable lint issues...'
# ruff check --fix src/ tests/
ruff check --fix src/ 
# ruff format src/ tests/
ruff format src/ 

echo ''
echo '✨ All formatting complete! ✨'

