#!/bin/bash

echo "=== Installing 013 Bot ==="
echo ""

echo "[1] Updating packages..."
pkg update -y && pkg upgrade -y 2>/dev/null || true

echo "[2] Installing Python..."
pkg install python -y

echo "[3] Installing pip requirements..."
pip install -r requirements.txt

echo ""
echo "Installation complete!"
echo ""
echo "To run the bot:"
echo "  1. Open config.py and set your BOT_TOKEN"
echo "  2. Run: python main.py"
echo ""
echo "Or use the quick start:"
echo "  bash run.sh"
