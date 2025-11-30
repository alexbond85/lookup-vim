#!/bin/bash
# Simple test script to verify FIFO integration

echo "Testing FIFO Integration"
echo "========================"

FIFO_PATH="/tmp/robert-dict.fifo"

# Test 1: Check if FIFO exists (will be created by Python service)
if [ -e "$FIFO_PATH" ]; then
    echo "✓ FIFO exists at $FIFO_PATH"
else
    echo "✗ FIFO not found at $FIFO_PATH (start the Python service first)"
    exit 1
fi

# Test 2: Send a test message to FIFO
echo "Sending test message to FIFO..."
TEST_DATA='{"selection":"être","phrase":"Je veux être heureux","paragraph":"Je veux être heureux dans ma vie.","file":"test.txt"}'

# Non-blocking write
echo "$TEST_DATA" > "$FIFO_PATH" 2>/dev/null &

if [ $? -eq 0 ]; then
    echo "✓ Successfully sent test data to FIFO"
    echo "  Check the Python REPL for translation output"
else
    echo "✗ Failed to send data to FIFO"
    exit 1
fi

echo ""
echo "Integration test complete!"
echo ""
echo "To test the full workflow:"
echo "1. Start Python service: python -m lookup_vim.interactive.main_service"
echo "2. Open Neovim with a French text file"
echo "3. Enable highlight mode: <leader>th"
echo "4. Select text in visual mode and press ,,"
echo "5. Check the Python REPL for the translation"
echo "6. Reopen the file to see highlights persist"

