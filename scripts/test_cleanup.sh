#!/bin/bash
# Test script to verify Neovim process cleanup

set -e

echo "🧪 Testing Neovim process cleanup..."
echo ""

# Count initial nvim processes
INITIAL_COUNT=$(ps aux | grep -c "nvim --headless" || echo "0")
echo "📊 Initial Neovim processes: $INITIAL_COUNT"

# Start the MCP server in background
echo "🚀 Starting MCP server..."
cd "$(dirname "$0")/.."
IDE_PROJECT_PATH=/tmp PYTHONPATH=src uv run python -m otter.mcp_server &
SERVER_PID=$!
echo "   Server PID: $SERVER_PID"

# Give it time to start and create Neovim process
sleep 3

# Count nvim processes after start
AFTER_START=$(ps aux | grep -c "nvim --headless" || echo "0")
echo "📊 After server start: $AFTER_START Neovim processes"

if [ "$AFTER_START" -le "$INITIAL_COUNT" ]; then
    echo "❌ FAIL: Neovim process not created"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# Kill the server (simulating Claude Desktop closing)
echo "🛑 Killing server (simulating Claude Desktop close)..."
kill -TERM $SERVER_PID
sleep 2

# Give cleanup handlers time to run
sleep 1

# Count nvim processes after cleanup
AFTER_CLEANUP=$(ps aux | grep -c "nvim --headless" || echo "0")
echo "📊 After cleanup: $AFTER_CLEANUP Neovim processes"

# Verify cleanup worked
if [ "$AFTER_CLEANUP" -gt "$INITIAL_COUNT" ]; then
    echo "❌ FAIL: Neovim process not cleaned up!"
    echo "   Orphaned processes:"
    ps aux | grep "nvim --headless" | grep -v grep || true
    exit 1
else
    echo "✅ SUCCESS: Neovim process properly cleaned up!"
fi

echo ""
echo "🎉 All tests passed!"

