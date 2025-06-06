#!/bin/bash
while true; do
  if ! pgrep -f "deepseek_ai.py" > /dev/null; then
    echo "[$(date)] RESTARTING DeepSeek..." >> ~/Documents/EmpireBot/logs/deepseek.log
    ~/Documents/EmpireBot/venv/bin/python ~/Documents/EmpireBot/deepseek_ai.py --port 8051
  fi
  sleep 10
done
