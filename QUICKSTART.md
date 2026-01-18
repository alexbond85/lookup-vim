# VimLookup Quickstart

## Web Development (Browser)

```bash
./run-web.sh
# Open http://localhost:3000
```

## Tauri Development (Desktop Window)

```bash
./run-app.sh
```

## Production Build (Standalone App)

```bash
# Apple Silicon (M1/M2/M3/M4)
./build.sh --arch aarch64

# Intel (requires Rosetta on Apple Silicon)
./build.sh --arch x86_64

# Output:
#   .app → web/tauri/src-tauri/target/<arch>/release/bundle/macos/VimLookup.app
#   .dmg → web/tauri/src-tauri/target/<arch>/release/bundle/dmg/VimLookup_*.dmg
```

## First Run

1. `menu` → `Settings` → Enter OpenAI API key
2. Set source/target languages
3. Save

## Data Location

- **Dev**: `.cache/`
- **Prod**: `~/Library/Application Support/VimLookup/`
