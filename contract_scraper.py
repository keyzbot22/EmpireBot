import feedparser
import sqlite3
from datetime import datetime

GOV_FEEDS = {
    "SAM.gov": "https://sam.gov/api/prod/sgs/v1/search?index=opp&format=rss",
    "Beta.SAM": "https://beta.sam.gov/api/prod/sgs/v1/search?index=opp&format=rss"
}

def scrape_contracts():
    conn = sqlite3.connect('empirebot.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS contracts (
            id TEXT PRIMARY KEY,
            title TEXT,
            due_date TEXT,
            link TEXT,
            source TEXT,
            scraped_at TEXT
        )
    ''')
    new_contracts = []

    for source, url in GOV_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                contract_id = entry.id
                title = entry.title
                link = entry.link
                due_date = entry.updated
                conn.execute('''
                    INSERT OR IGNORE INTO contracts (id, title, due_date, link, source, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (contract_id, title, due_date, link, source, datetime.utcnow().isoformat()))
                new_contracts.append(title)
        except Exception as e:
            print(f"Error scraping {source}: {e}")
    
    conn.commit()
    conn.close()
    return new_contracts
