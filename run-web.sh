#!/bin/bash
# Run the web version (browser only, no Tauri)

set -e

echo "🚀 Starting nvim-lookup web version..."
echo ""
echo "📡 Starting FastAPI backend..."

source .venv/bin/activate
python -m uvicorn web.backend.app:app --host 127.0.0.1 --port 2989

echo ""
echo "✅ Server running at: http://127.0.0.1:2989"
echo ""
echo "Press Ctrl+C to stop"
