#!/usr/bin/env bash
# Dictionary viewer with beautiful formatting and interactive mode
# Usage: Run this in your second terminal window
#   - Type a word and press Enter to look it up
#   - Or use ,, in vim to trigger lookup

# Disable job control messages
set +m

WORD_FILE="${TMPDIR:-/tmp}/robert-dict-word.json"

# Colors
BOLD='\033[1m'
DIM='\033[2m'
BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
MAGENTA='\033[1;35m'
RESET='\033[0m'

# Configuration
STREAM_MODE=true        # Set to false to disable streaming effect
STREAM_DELAY=0.002      # Delay between characters (seconds) - faster now

# Streaming print function - handles color codes properly
stream_print() {
    local text="$1"
    if [ "$STREAM_MODE" = true ]; then
        local i=0
        local len=${#text}
        while [ $i -lt $len ]; do
            # Check for escape sequence start
            if [ "${text:$i:1}" = $'\033' ] || [ "${text:$i:2}" = '\0' ]; then
                # Find the end of escape sequence (letter after '[')
                local esc_end=$i
                while [ $esc_end -lt $len ]; do
                    local char="${text:$esc_end:1}"
                    esc_end=$((esc_end + 1))
                    if [[ "$char" =~ [a-zA-Z] ]]; then
                        break
                    fi
                done
                # Print entire escape sequence instantly
                echo -ne "${text:$i:$((esc_end - i))}"
                i=$esc_end
            else
                # Regular character - stream it
                echo -n "${text:$i:1}"
                sleep "$STREAM_DELAY"
                i=$((i + 1))
            fi
        done
        echo ""
    else
        echo -e "$text"
    fi
}

# Check for fswatch
if ! command -v fswatch &> /dev/null; then
    echo -e "${YELLOW}Warning: fswatch not found. File watching disabled.${RESET}"
    echo "Install with: brew install fswatch"
    echo ""
    FSWATCH_AVAILABLE=false
else
    FSWATCH_AVAILABLE=true
fi

# Function to display a word definition
display_definition() {
    local input="$1"
    local word=""
    local phrase=""
    local paragraph=""
    
    # Try to parse as JSON
    if command -v jq &> /dev/null && echo "$input" | jq empty 2>/dev/null; then
        word=$(echo "$input" | jq -r '.selection // empty')
        phrase=$(echo "$input" | jq -r '.phrase // empty')
        paragraph=$(echo "$input" | jq -r '.paragraph // empty')
    else
        # Fallback: treat as plain text
        word="$input"
    fi
    
    # Clear screen and show header
    clear
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${GREEN}║${RESET}  ${CYAN}${BOLD}📖  Dictionnaire Le Robert${RESET}                                                ${GREEN}║${RESET}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════════════╝${RESET}"
    echo ""
    
    # Show context if available
    if [ -n "$phrase" ]; then
        echo -e "${DIM}Phrase: ${RESET}${phrase:0:120}..."
        echo ""
    fi
    
    # Fetch and display definition with nice formatting and streaming
    robert-dict "$word" 2>/dev/null | while IFS= read -r line; do
        # Category headers (in brackets)
        if [[ "$line" =~ ^\[.*\]$ ]]; then
            stream_print "${MAGENTA}${BOLD}$line${RESET}"
        # Definition numbers
        elif [[ "$line" =~ ^[[:space:]]*[0-9]+\. ]]; then
            stream_print "${CYAN}$line${RESET}"
        # Examples (arrows)
        elif [[ "$line" =~ ^[[:space:]]*→ ]]; then
            stream_print "${DIM}$line${RESET}"
        # Section headers (all caps)
        elif [[ "$line" =~ ^[A-ZÀÂÄÆÇÉÈÊËÏÎÔŒÙÛÜŸ\'\ ]+$ ]] && [ ${#line} -lt 80 ]; then
            stream_print "${YELLOW}${BOLD}$line${RESET}"
        # Separator lines (instant - no streaming for these)
        elif [[ "$line" =~ ^─+$ ]] || [[ "$line" =~ ^═+$ ]]; then
            echo -e "${GREEN}$line${RESET}"
        # Regular text
        else
            stream_print "$line"
        fi
    done
    
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}⚠ Aucune définition trouvée pour: ${BOLD}$word${RESET}"
    fi
    
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
echo -e "${GREEN}║${RESET}  ${CYAN}${BOLD}📖  Dictionnaire Le Robert${RESET}                                                ${GREEN}║${RESET}"
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
            INPUT=$(cat "$WORD_FILE" 2>/dev/null)
            if [ -n "$INPUT" ]; then
                display_definition "$INPUT"
            fi
        done
    } &
    WATCHER_PID=$!
fi

# Interactive mode: read from stdin
while IFS= read -r input; do
    # Check for exit commands
    if [ "$input" = "quit" ] || [ "$input" = "exit" ] || [ "$input" = "q" ]; then
        echo ""
        echo -e "${CYAN}Au revoir! 👋${RESET}"
        # Cleanup
        if [ -n "$WATCHER_PID" ]; then
            kill $WATCHER_PID 2>/dev/null
        fi
        exit 0
    elif [ -n "$input" ]; then
        display_definition "$input"
    else
        echo -ne "${GREEN}❯${RESET} "
    fi
done

# Cleanup on exit
if [ -n "$WATCHER_PID" ]; then
    kill $WATCHER_PID 2>/dev/null
fi
