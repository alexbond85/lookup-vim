#!/bin/bash
# Setup script for nvim selection FIFO

FIFO="/tmp/nvim-selection.fifo"

# Create FIFO if it doesn't exist
if [ ! -p "$FIFO" ]; then
    mkfifo "$FIFO"
    echo "✓ FIFO created at $FIFO"
else
    echo "✓ FIFO already exists at $FIFO"
fi

