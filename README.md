# nvim-lookup

A Neovim foreign language reader: nvim plugin for highlighting and selecting text + Python client that handles translation and history.

Includes a word scraper from the Robert online dictionary for learning French.

## How It Works



https://github.com/user-attachments/assets/15123fe3-e686-47e6-a558-30d8bbf004e4



https://github.com/user-attachments/assets/b3642ac6-cf01-4868-9880-f0a555fedb8f



https://github.com/user-attachments/assets/09685383-cd06-4cd6-b8c8-0f38f8e852b1



Navigate the text using vim commands, select a word or expression in visual mode, then press `,,` to trigger translation in the chat client on the right.

Within the chat client:
- Press `1` to translate the sentence containing the selection
- Press `2` to translate the entire paragraph
- Press `?` to ask follow-up questions

## New to Neovim?

Run `vimtutor` in your terminal for a 30-minute interactive tutorial. For this app, you only need basic navigation (`h`/`j`/`k`/`l`), visual selection (`v`), and one shortcut (`,,`).

## Installation

### 1. Install Neovim

```bash
# macOS
brew install neovim

# Ubuntu/Debian
sudo apt install neovim

# Arch
sudo pacman -S neovim
```

### 2. Neovim Configuration

Neovim stores its configuration in `~/.config/nvim`. [NvChad](https://nvchad.com/) is a good starting point.

**Install NvChad:**

```bash
git clone https://github.com/NvChad/starter ~/.config/nvim && nvim
```

On first launch, it installs plugins automatically.

**Pre-configured setup (optional):**

A ready-to-use NvChad config with the plugin already set up:

```bash
rm -rf ~/.config/nvim
git clone -b feat/current-settings https://github.com/alexbond85/nvchad-starter ~/.config/nvim
```

The plugin config lives in `~/.config/nvim/lua/plugins/text-selections.lua`. **Edit the `dir` path to point to where you cloned nvim-lookup:**

```lua
return {
    dir = "~/your/path/to/nvim-lookup/nvim-plugins/text-selections",
}
```

### 3. Clone and Setup

```bash
git clone https://github.com/alexbond85/nvim-lookup.git
cd nvim-lookup
```

Install [uv](https://github.com/astral-sh/uv) if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create the environment and install dependencies:

```bash
uv sync --all-extras
source .venv/bin/activate
```

### 4. Configure

```bash
cp config.ini.example config.ini
```

Set your source and target languages in `config.ini`:

```ini
[translation]
source_lang = French
target_lang = English
```

## OpenAI API Key

1. Create an account at [platform.openai.com](https://platform.openai.com)
2. Add prepaid credit (~$10)
3. Generate an API key
4. Create `.env` in the project root:

```
OPENAI_API_KEY=sk-...
```

## Using Another LLM

The LLM is abstracted via the `StructuredOutputLLM` protocol in [`src/lookup/translation/llm/base.py`](src/lookup/translation/llm/base.py). Implement `structured_response()` and `response()` to use a different provider.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for code quality tools.
