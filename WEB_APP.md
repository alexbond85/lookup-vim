# nvim-lookup Web App

A standalone Mac app version of nvim-lookup with a beautiful, Claude-like interface.

## Quick Start

### Option 1: Run in Browser (Web Version)

```bash
./run-web.sh
```

Then open: http://127.0.0.1:3000

### Option 2: Run as Native Mac App (Tauri)

```bash
./run-app.sh
```

This will:
1. Start the FastAPI backend
2. Open the app in a native Mac window

## Features

- **Vim Navigation**: Full vim keybindings (h/j/k/l, w/b, etc.)
- **Visual Selection**: Press `v` to enter visual mode, select text
- **Translation**: Press `,,` to translate selected text
- **Chat Interface**: Ask follow-up questions about translations
- **Drag & Drop**: Drop `.txt` or `.md` files directly into the editor
- **Highlight History**: Previous translations are highlighted when you reopen a file

## How to Use

1. **Open a file**: Click "Open File" or drag-and-drop a text file into the editor
2. **Navigate**: Use vim keys (h/j/k/l for movement, w/b for word navigation)
3. **Select text**:
   - Press `v` to enter VISUAL mode
   - Move cursor to select text
4. **Translate**: Press `,,` while text is selected
5. **Follow-up**: Type questions in the chat input to ask about the translation

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `h/j/k/l` | Move cursor (vim) |
| `w`/`b` | Word forward/backward |
| `v` | Enter visual mode |
| `,,` | Translate selection |
| `Esc` | Return to normal mode |

## Architecture

```
Frontend (CodeMirror + Vim)
    ↓
FastAPI Backend (Python)
    ↓
Existing Services (LookupService, TranslationService, etc.)
    ↓
OpenAI API
```

All your existing business logic is reused - zero changes needed!

## Configuration

Edit `config.ini` to change source/target languages:

```ini
[translation]
source_lang = French
target_lang = English
```

## Building the Mac App

To build a standalone `.dmg` installer:

```bash
cd web/tauri
npm run tauri build
```

The built app will be in: `web/tauri/src-tauri/target/release/bundle/dmg/`

## Development

- **Backend code**: `web/backend/` (FastAPI routes, session management)
- **Frontend code**: `web/frontend/` (HTML, JavaScript, CodeMirror)
- **Tauri config**: `web/tauri/src-tauri/tauri.conf.json`

The implementation follows the KISS principle - minimal code, maximum functionality.

## Troubleshooting

**Port 3000 already in use:**
```bash
# Kill the existing process
lsof -ti:3000 | xargs kill -9

# Then restart
./run-web.sh
```

**Backend not starting:**
```bash
# Make sure dependencies are installed
uv sync

# Activate venv and run manually
source .venv/bin/activate
uvicorn web.backend.app:app --host 127.0.0.1 --port 3000
```

**Tauri build fails:**
```bash
# Install/update Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Source cargo env
source "$HOME/.cargo/env"

# Try again
cd web/tauri
npm run tauri dev
```

## Next Steps

- [ ] Add app icon (replace default icons in `web/tauri/src-tauri/icons/`)
- [ ] Implement settings UI (currently uses config.ini)
- [ ] Add export/save functionality for chat history
- [ ] Support more file formats
- [ ] Add dark mode toggle

Enjoy your new standalone reading app! 🎉
