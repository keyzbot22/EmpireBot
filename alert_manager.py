# alert_manager.py

import os
import time
import json
import logging
import traceback
import requests
from datetime import datetime

MAX_RETRIES = 3

class AlertManager:
    def __init__(self, db):
        self.db = db
        self._current_retries = 0
        self.telegram_bots = [
            {'name': 'empire', 'token': os.getenv('EMPIRE_BOT_TOKEN')},
            {'name': 'zariah', 'token': os.getenv('ZARIAH_BOT_TOKEN')},
            {'name': 'keycontrol', 'token': os.getenv('KEYCONTROL_BOT_TOKEN')},
        ]

    def send(self, message, priority='medium'):
        if self._current_retries >= MAX_RETRIES:
            self._log_failure(message)
            self._log_recursion_attempt()
            return {"status": "max_retries_exceeded"}

        try:
            self._current_retries += 1
            results = {}
            for bot in self.telegram_bots:
                results[f"telegram_{bot['name']}"] = self._send_with_retry(
                    lambda: self._send_telegram(message, bot),
                    max_retries=MAX_RETRIES
                )

            if not any(results.values()) and priority == 'high':
                results['email'] = self._send_with_retry(self._send_zoho, 2)
                results['sms'] = self._send_with_retry(self._send_twilio, 2)

            return results

        finally:
            self._current_retries = 0

    def _send_with_retry(self, send_func, max_retries=3):
        for attempt in range(max_retries):
            try:
                if send_func():
                    return True
            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed: {str(e)}")
                time.sleep(2 ** attempt)
        return False

    def _send_telegram(self, message, bot):
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{bot['token']}/sendMessage",
                json={
                    'chat_id': os.getenv('ADMIN_CHAT_ID'),
                    'text': message,
                    'parse_mode': 'HTML'
                },
                timeout=5
            )
            return response.json().get('ok', False)
        except Exception as e:
            logging.error(f"Telegram bot {bot['name']} failed: {e}")
            return False

    def _send_twilio(self):
        # Twilio logic goes here
        return False

    def _send_zoho(self):
        # Zoho email logic goes here
        return False

    def _log_failure(self, message):
        logging.error(f"Alert failed after {MAX_RETRIES} retries: {message}")

    def _log_recursion_attempt(self):
        self.db.safe_execute("""
            INSERT INTO recursion_events (timestamp, stack_trace)
            VALUES (?, ?)
        """, [datetime.now(), traceback.format_exc()])
