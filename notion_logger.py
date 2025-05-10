
# notion_logger.py
# Requires: pip install requests

import requests

NOTION_API_KEY = "your_notion_integration_token"
DATABASE_ID = "your_notion_database_id"

def log_to_notion(task, result):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Task": {"title": [{"text": {"content": task}}]},
            "Result": {"rich_text": [{"text": {"content": result}}]}
        }
    }
    r = requests.post(url, headers=headers, json=data)
    return r.status_code
