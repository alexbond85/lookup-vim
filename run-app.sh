#!/bin/bash
# Run the nvim-lookup standalone app

set -e

echo "🚀 Starting nvim-lookup standalone app..."
echo ""

# Start FastAPI backend in background
echo "📡 Starting FastAPI backend..."
source .venv/bin/activate
python -m uvicorn web.backend.app:app --host 127.0.0.1 --port 3000 &
BACKEND_PID=$!

echo "   Backend PID: $BACKEND_PID"
echo "   Backend URL: http://127.0.0.1:3000"
echo ""

# Wait for backend to start
echo "⏳ Waiting for backend to be ready..."
sleep 3

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    kill $BACKEND_PID 2>/dev/null || true
    echo "✅ Done!"
}
trap cleanup EXIT INT TERM

# Start Tauri dev
echo "🖥️  Opening application window..."
echo ""
cd web/tauri
npm run tauri dev
