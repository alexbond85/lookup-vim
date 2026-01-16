# nvim-lookup Standalone App - Quick Start

## 🚀 Try It Now

The fastest way to see your new app in action:

### 1. Start the Web Version

```bash
./run-web.sh
```

Then open: **http://127.0.0.1:3000**

### 2. Test the Features

1. **Drag and drop** a French text file into the editor pane
2. **Use vim keys** to navigate (h/j/k/l)
3. **Press `v`** to enter visual mode
4. **Select a word or phrase** by moving the cursor
5. **Press `,,`** to translate
6. **See the translation** appear in the chat panel on the right
7. **Ask follow-up questions** in the input field at the bottom

### 3. Run as Native Mac App (Optional)

For the full native experience:

```bash
./run-app.sh
```

This opens a native Mac window instead of using your browser.

## 📖 Example Workflow

```
1. Open a French book chapter (drag .txt file)
2. Read using vim navigation
3. See word → Press ,,
4. Translation appears in chat
5. Ask "Can you give me an example sentence?"
6. Assistant responds with examples
7. Continue reading - highlights show previous lookups
```

## ⚙️ Configuration

Your existing `config.ini` works as-is:

```ini
[translation]
source_lang = French
target_lang = English
```

## 🎯 What You Get

- ✅ All your existing CLI functionality
- ✅ Beautiful Claude-like interface
- ✅ Vim keybindings (full support)
- ✅ Chat-style conversations
- ✅ Persistent highlight history
- ✅ Drag-and-drop files
- ✅ Native Mac app (via Tauri)

## 📚 Need More Info?

See **WEB_APP.md** for:
- Complete feature documentation
- Architecture details
- Building standalone .dmg
- Troubleshooting
- Customization options

---

**Enjoy your new standalone reading app!** 🎉
