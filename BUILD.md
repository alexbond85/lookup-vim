# Building VimLookup Standalone App

## Problem

The VimLookup app was originally designed to run with a FastAPI backend that served frontend assets at `/static/*` URLs. When building a standalone macOS `.app` bundle with Tauri, the following issues occurred:

1. **Frontend files weren't being embedded**: Tauri's build system expected a `dist` directory with built frontend assets (standard for modern web frameworks like Vite, Webpack, etc.), but VimLookup served raw HTML/JS files directly.

2. **Incorrect asset paths**: The HTML referenced JavaScript files as `/static/app.js` and `/static/context-extractor.js`, which only worked when the FastAPI backend was serving files. In the standalone `.app`, there's no backend serving `/static/*`, so these paths failed.

3. **Tauri's default behavior**: Without finding proper frontend assets, Tauri would fall back to embedding minimal placeholder files, resulting in an app that opened but had no CSS or JavaScript functionality.

## Solution

The solution involved three key changes:

### 1. Frontend Build Step

Created a minimal build process that copies frontend files to a `dist/` directory:

**`web/frontend/package.json`:**
```json
{
  "scripts": {
    "build": "mkdir -p dist && cp index.html app.js context-extractor.js dist/"
  }
}
```

This satisfies Tauri's expectation of a built frontend output directory.

### 2. Tauri Configuration

Updated `web/tauri/src-tauri/tauri.conf.json` to:
- Run the frontend build before bundling: `"beforeBuildCommand": "cd ../frontend && npm run build"`
- Point to the dist directory: `"frontendDist": "../../frontend/dist"`

### 3. Asset Path Changes

Changed asset references in `web/frontend/index.html` from absolute paths to relative paths:
- From: `/static/app.js` → To: `./app.js`
- From: `/static/context-extractor.js` → To: `./context-extractor.js`

Updated `web/backend/app.py` to support both `/static/*` (backward compatible) and relative paths at root.

## Building the App

**Note**: All Tauri build commands must be run from the `web/tauri/` directory, or use the commands below that work from the project root.

### Standard Build

**From project root:**
```bash
cd web/tauri && npm run tauri build -- --bundles app
```

**From web/tauri/ directory:**
```bash
npm run tauri build -- --bundles app
```

The built app will be located at:
```
web/tauri/src-tauri/target/release/bundle/macos/VimLookup.app
```

### Clean Build (No Cache)

To do a complete rebuild without any cached artifacts.

**From project root:**
```bash
cd web/tauri && rm -rf src-tauri/target ../frontend/dist && npm run tauri build -- --bundles app
```

**From web/tauri/ directory:**
```bash
# Remove all build artifacts
rm -rf src-tauri/target
rm -rf ../frontend/dist

# Build fresh
npm run tauri build -- --bundles app
```

This ensures:
- All Rust/Cargo artifacts are rebuilt
- Frontend assets are copied fresh to dist/
- Tauri embeds the latest frontend files

### Development Build

For faster iteration during development (uses debug profile).

**From project root:**
```bash
cd web/tauri && npm run tauri build -- --debug --bundles app
```

**From web/tauri/ directory:**
```bash
npm run tauri build -- --debug --bundles app
```

## Running the Built App

### Opening the App

```bash
open web/tauri/src-tauri/target/release/bundle/macos/VimLookup.app
```

Or simply double-click `VimLookup.app` in Finder.

### What Happens When You Start It

1. **Tauri Frontend**: The app window opens, loading the embedded HTML/CSS/JS
2. **Backend Sidecar**: The Python `vimlookup-server` backend starts automatically as a subprocess
3. **Communication**: Frontend communicates with backend via HTTP at `http://localhost:3000`

## Data Storage Locations

When the standalone app runs, it stores data in standard macOS application directories:

### Application Support Directory

Main application data (highlights history, settings, cache):

```
~/Library/Application Support/com.vimlookup.reader/
```

You can access this from terminal:
```bash
open ~/Library/Application\ Support/com.vimlookup.reader/
```

### Common Files You'll Find

- **Highlights/Selections**: `selections.jsonl` or similar cache files
- **Settings**: Configuration files (if any are persisted)
- **Database**: Any SQLite databases or data stores
- **Logs**: Application logs (if logging is configured)

### Finding the Directory Programmatically

The Tauri app uses the system's standard paths:

- **App Data**: `~/.local/share/com.vimlookup.reader/` (Linux) or `~/Library/Application Support/com.vimlookup.reader/` (macOS)
- **Config**: `~/.config/com.vimlookup.reader/` (Linux) or `~/Library/Application Support/com.vimlookup.reader/` (macOS)
- **Cache**: `~/.cache/com.vimlookup.reader/` (Linux) or `~/Library/Caches/com.vimlookup.reader/` (macOS)

### Checking the Actual Location

To see exactly where files are being created:

1. Start the app
2. Use the app to create some highlights/selections
3. Check the backend logs or search for recent files:

```bash
# Find recently modified files related to vimlookup
find ~/Library/Application\ Support -name "*vimlookup*" -mtime -1

# Or check the cache directory
find ~/Library/Caches -name "*vimlookup*" -mtime -1

# Look for JSONL files (selections data)
find ~/ -name "selections.jsonl" -mtime -1 2>/dev/null
```

## Troubleshooting

### App Opens But Features Don't Work

If the app opens but CSS/JavaScript features aren't working:

1. **Check console logs**: Enable developer tools in the Tauri window (if configured)
2. **Verify bundle contents**: 
   ```bash
   # Check if frontend files are embedded
   ls -lh web/tauri/src-tauri/target/release/build/tauri-*/out/tauri-codegen-assets/
   ```
3. **Rebuild without cache**: Follow the "Clean Build" steps above

### Backend Server Not Starting

If the app opens but the backend isn't responding:

1. **Check the sidecar binary exists**:
   ```bash
   ls -la web/tauri/src-tauri/binaries/vimlookup-server
   ```
2. **Verify it's in the bundle**:
   ```bash
   ls -la web/tauri/src-tauri/target/release/bundle/macos/VimLookup.app/Contents/MacOS/
   ```
3. **Check backend permissions**: The binary needs execute permissions

### Port Already in Use

If port 3000 is already in use:

```bash
# Find and kill the process using port 3000
lsof -ti:3000 | xargs kill -9
```

## Development vs Production

### Development Mode (`run-app.sh`)

- FastAPI backend serves frontend files at `/static/*`
- Frontend loaded from `web/frontend/` directory directly
- Hot reload supported (if using dev tools)
- Backend runs in Python virtual environment

### Production Mode (Standalone `.app`)

- Frontend files embedded in the app bundle
- Backend runs as a compiled sidecar binary
- Self-contained, no external dependencies needed
- Data stored in user's Application Support directory

## Distribution

To distribute the app:

1. Build with `npm run tauri build -- --bundles dmg` to create a DMG installer
2. The DMG will be at: `web/tauri/src-tauri/target/release/bundle/dmg/VimLookup_*.dmg`
3. Users can drag-and-drop to Applications folder

For code signing and notarization (required for distribution outside the App Store), see [Tauri's macOS distribution guide](https://v2.tauri.app/distribute/macos-application-bundle/).

## Uninstalling / Cleaning Up

### Remove the Installed App

If you've copied VimLookup.app to `/Applications`:

```bash
rm -rf /Applications/VimLookup.app
```

### Remove Build Artifacts

To clean up all built apps from your project directory:

```bash
cd web/tauri

# Remove all build artifacts (includes all .app bundles)
rm -rf src-tauri/target

# Or just remove the app bundles
rm -rf src-tauri/target/*/bundle/macos/VimLookup.app
rm -rf src-tauri/target/*/*/bundle/macos/VimLookup.app
```

### Remove User Data

To completely remove all VimLookup data (highlights, settings, cache):

```bash
# Application data and settings
rm -rf ~/Library/Application\ Support/com.vimlookup.reader

# Cache files
rm -rf ~/Library/Caches/com.vimlookup.reader

# Logs (if any)
rm -rf ~/Library/Logs/com.vimlookup.reader

# Preferences
rm -f ~/Library/Preferences/com.vimlookup.reader.plist
```

### Clean Spotlight Index

If you see multiple VimLookup apps in Spotlight/Launchpad after removing them, rebuild the Spotlight index:

```bash
# Rebuild Spotlight index for your project directory
mdutil -E /Users/alexbond/projects/alexbond/nvim-lookup

# Or rebuild for your entire home directory (takes longer)
mdutil -E ~
```

Alternatively, just wait a few minutes for macOS to automatically update its index.

### Complete Uninstall (One Command)

To remove everything related to VimLookup:

```bash
# Remove app from Applications
rm -rf /Applications/VimLookup.app

# Remove build artifacts from project
rm -rf /Users/alexbond/projects/alexbond/nvim-lookup/web/tauri/src-tauri/target

# Remove user data
rm -rf ~/Library/Application\ Support/com.vimlookup.reader
rm -rf ~/Library/Caches/com.vimlookup.reader
rm -rf ~/Library/Logs/com.vimlookup.reader
rm -f ~/Library/Preferences/com.vimlookup.reader.plist

# Rebuild Spotlight index
mdutil -E /Users/alexbond/projects/alexbond/nvim-lookup
```

### Why Multiple Apps Appear

During development, you may see multiple VimLookup apps because:

1. **Debug builds**: `target/debug/bundle/macos/VimLookup.app`
2. **Release builds**: `target/release/bundle/macos/VimLookup.app`
3. **Architecture-specific builds**: `target/aarch64-apple-darwin/release/bundle/macos/VimLookup.app`

macOS Spotlight indexes all of these, making them appear in Launchpad and app searches. These are just different builds in your project directory, not separate installations.
