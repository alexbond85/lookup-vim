#!/usr/bin/env bash
# Dictionary viewer with file watching - delegates to Python script for logic
# Usage: Run this in your second terminal window
#   - Type a word and press Enter to look it up
#   - Or use ,, in vim to trigger lookup

# Disable job control messages
set +m

WORD_FILE="${TMPDIR:-/tmp}/robert-dict-word.json"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/dict_watcher.py"

# Cleanup function
cleanup() {
    # Kill background watcher if it exists
    if [ -n "$WATCHER_PID" ] && kill -0 "$WATCHER_PID" 2>/dev/null; then
        kill "$WATCHER_PID" 2>/dev/null
        wait "$WATCHER_PID" 2>/dev/null
    fi
}

# Trap signals to cleanup properly (but don't trap EXIT to avoid double-cleanup)
trap cleanup INT TERM

# Colors for bash prompts
GREEN='\033[1;32m'
CYAN='\033[1;36m'
DIM='\033[2m'
RESET='\033[0m'

# Check for fswatch
if ! command -v fswatch &> /dev/null; then
    echo -e "${YELLOW}Warning: fswatch not found. File watching disabled.${RESET}"
    echo "Install with: brew install fswatch"
    echo ""
    FSWATCH_AVAILABLE=false
else
    FSWATCH_AVAILABLE=true
fi

# Function to call Python script and display result
display_definition() {
    local input="$1"
    
    # Write input to file if provided (for manual input)
    [ -n "$input" ] && echo "{\"selection\": \"$input\"}" > "$WORD_FILE"
    
    # Call Python script - it handles all the logic and formatting
    python3 "$PYTHON_SCRIPT"
    
    # Show prompt after Python finishes
    echo ""
    echo -e "${GREEN}────────────────────────────────────────────────────────────────────────────────${RESET}"
    echo -e "${CYAN}Tapez un mot et appuyez sur Entrée${RESET} ${DIM}ou utilisez ,, dans vim${RESET}"
    echo -ne "${GREEN}❯${RESET} "
}

# Kill any existing instances of this script and fswatch
pkill -f "dict-watcher.sh" 2>/dev/null
pkill -f "fswatch.*robert-dict-word" 2>/dev/null
sleep 0.5

# Create/clear the word file on startup
echo "" > "$WORD_FILE"

# Initial screen
clear
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}║${RESET}  ${CYAN}${BOLD}📖  Dictionnaire Le Robert & ChatGPT${RESET}                                   ${GREEN}║${RESET}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "${YELLOW}Mode interactif activé${RESET}"
echo ""
echo -e "  ${CYAN}•${RESET} Tapez un mot et appuyez sur ${BOLD}Entrée${RESET} pour voir sa définition"
echo -e "  ${CYAN}•${RESET} Ou utilisez ${BOLD},,${RESET} dans vim pour rechercher le mot sous le curseur"
echo ""
echo -e "${GREEN}────────────────────────────────────────────────────────────────────────────────${RESET}"
echo -ne "${GREEN}❯${RESET} "

# Start file watcher in background if available
if [ "$FSWATCH_AVAILABLE" = true ]; then
    {
        fswatch -o "$WORD_FILE" 2>/dev/null | while read; do
            # File changed - call Python script to handle it
            # The Python script reads from WORD_FILE and outputs to stdout
            display_definition ""
        done
    } &
    WATCHER_PID=$!
fi

# Interactive mode: read from stdin
while IFS= read -r input || [ -n "$input" ]; do
    # Handle EOF (Ctrl+D)
    if [ -z "$input" ] && [ ${#input} -eq 0 ]; then
        break
    fi
    
    # Check for exit commands (case-insensitive)
    input_lower=$(echo "$input" | tr '[:upper:]' '[:lower:]')
    if [ "$input_lower" = "quit" ] || [ "$input_lower" = "exit" ] || [ "$input_lower" = "q" ]; then
        echo ""
        echo -e "${CYAN}Au revoir! 👋${RESET}"
        break
    elif [ -n "$input" ]; then
        # Manual input - convert to JSON and trigger lookup
        display_definition "$input"
    else
        echo -ne "${GREEN}❯${RESET} "
    fi
done

# Cleanup - script will exit naturally when it reaches the end
cleanup
