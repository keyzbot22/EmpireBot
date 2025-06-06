#!/bin/bash
echo "🔁 Killing existing bot processes..."
pkill -f zariah_pro.py
pkill -f deepseek_ai.py
screen -wipe

echo "🚀 Restarting Zariah..."
screen -S zariah -dm python3 zariah_pro.py

echo "🧠 Restarting DeepSeek..."
screen -S deepseek -dm python3 deepseek_ai.py --port 8051

echo "✅ EmpireBot Hard Reset Complete."
