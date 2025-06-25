#!/usr/bin/env python3
import os
import sys
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

def send_alert(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print(f"Telegram error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        send_alert(sys.argv[1])
