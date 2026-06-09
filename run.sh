#!/bin/bash

echo "=== 013 Bot ==="
echo ""

if [ -z "$BOT_TOKEN" ]; then
    read -p "Enter your Bot Token: " BOT_TOKEN
    export BOT_TOKEN="$BOT_TOKEN"
fi

echo "Starting bot..."
python main.py
