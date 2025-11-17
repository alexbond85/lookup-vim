# ChatGPT Translation Service

This service provides French-to-Russian translations with detailed contextual explanations using OpenAI's ChatGPT.

## Setup

1. Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

2. Install the package (if not already installed):
```bash
uv pip install -e .
```

## Usage

### Basic Translation

Translate a French word or expression:

```bash
uv run robert-translate "bien que"
```

### Translation with Context

Provide context for better understanding:

```bash
uv run robert-translate "au fur et à mesure" --context "Il apprend au fur et à mesure."
```

Another example:

```bash
uv run robert-translate "pourtant" --context "Il était fatigué, pourtant il a continué."
```

## Output Format

The service returns JSON with the following fields:

```json
{
  "query": "pourtant",
  "translation": "однако, тем не менее, всё же",
  "explanations": "Detailed explanations including:\n- Literal meaning\n- Etymology\n- Intonation/connotation\n- Usage notes",
  "context": "Il était fatigué, pourtant il a continué."
}
```

## Options

- `--context, -c`: Provide the paragraph or sentence for context
- `--indent`: JSON indentation level (default: 2)
- `--model`: OpenAI model to use (default: gpt-4o)
- `--verbose, -v`: Enable verbose logging

## How It Works

1. **Input**: You provide a French word/expression and optionally a context paragraph
2. **Processing**: The service sends a carefully crafted prompt to ChatGPT that:
   - Explains the word was selected from the given context
   - Requests translation from French to Russian
   - Asks for detailed explanations including:
     - Literal meaning
     - Etymology
     - Intonation and connotation
     - Usage notes and nuances
     - How it functions in the given context
3. **Output**: Returns structured JSON with the query, translation, explanations, and context

## Architecture

The service follows the same clean architecture as the dictionary service:

- **Model**: `TranslationResult` in `models.py` - Domain model for translation data
- **Service**: `ChatGPTTranslationService` in `chatgpt_service.py` - Business logic for API calls
- **Printer**: `TranslationPrinter` in `printers/translation.py` - Output formatting
- **CLI**: `cli_translate.py` - Command-line interface

## Integration with Vim/Neovim

You can integrate this with your Vim setup similar to the dictionary service. Example:

```vim
" Visual mode mapping to translate selected text
vnoremap <leader>tr y:!uv run robert-translate "<C-R>""<CR>

" With context (assuming current paragraph as context)
vnoremap <leader>tc y:!uv run robert-translate "<C-R>"" --context "$(cat %)"<CR>
```

## Error Handling

The service handles errors gracefully:
- Missing API key: Returns clear error message
- API failures: Returns JSON error with details
- Network issues: Proper error reporting

All errors are output to stderr in JSON format for easy parsing.

