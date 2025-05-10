import requests

NOTION_API_KEY = "ntn_b11350832369ER3csJtkiBTIb8HwCSLmfZO2UkeRKUgeo1"
DATABASE_ID = "1e4043a7fee4803c805dfdbb8a427853"

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
if __name__ == "__main__":
    status = log_to_notion("🔥 Test: EmpireBot Sync", "✅ Notion is fully connected.")
    print("Log Status Code:", status)

