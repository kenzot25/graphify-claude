#!/usr/bin/env sh
# nexo bootstrap script - ensures nexo is available in any terminal session
# Usage: sh ~/.local/bin/nexo-bootstrap.sh
# Or after install: sh $(dirname $(which nexo))/nexo-bootstrap.sh

set -eu

NEXO_OUT_DIR="nexo-out"

# Create nexo-out directory if it doesn't exist
if [ ! -d "$NEXO_OUT_DIR" ]; then
    mkdir -p "$NEXO_OUT_DIR"
fi

# Step 1: Try to find 'nexo' command on PATH
if command -v nexo >/dev/null 2>&1; then
    if nexo --help >/dev/null 2>&1; then
        echo "Found working 'nexo' command: $(command -v nexo)"
        command -v nexo > "$NEXO_OUT_DIR/.nexo_bin"
        exit 0
    fi
fi

# Step 2: Fallback to python -m nexo
echo "nexo command not found, trying python..."

if command -v python3 >/dev/null 2>&1; then
    python_cmd="python3"
elif command -v python >/dev/null 2>&1; then
    python_cmd="python"
else
    python_cmd=""
fi

if [ -n "$python_cmd" ]; then
    if ! $python_cmd -c "import nexo" 2>/dev/null; then
        echo "Installing nexo via pip..."
        $python_cmd -m pip install nexo -q 2>/dev/null || \
        $python_cmd -m pip install nexo -q --break-system-packages 2>/dev/null || true
    fi

    if $python_cmd -c "import nexo" 2>/dev/null; then
        echo "Using $python_cmd -m nexo"
        echo "$python_cmd -m nexo" > "$NEXO_OUT_DIR/.nexo_bin"
        exit 0
    fi
fi

# Failure
echo "error: Failed to find or install nexo. Please install it manually: pip install nexo" >&2
exit 1
