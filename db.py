import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "news.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                published_at TEXT,
                collected_at TEXT NOT NULL,
                views INTEGER,
                summary TEXT,
                sentiment TEXT,
                company TEXT,
                raw_text TEXT
            )
        """)
        conn.commit()


def is_duplicate(url: str, title: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM articles WHERE url = ? OR title = ?", (url, title)
        ).fetchone()
        return row is not None


def save_article(article: dict):
    with get_conn() as conn:
        try:
            conn.execute(
                """INSERT INTO articles
                   (url, title, source, published_at, collected_at, views, summary, sentiment, company, raw_text)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    article.get("url"),
                    article.get("title"),
                    article.get("source"),
                    article.get("published_at"),
                    datetime.utcnow().isoformat(),
                    article.get("views"),
                    article.get("summary"),
                    article.get("sentiment"),
                    article.get("company"),
                    article.get("raw_text"),
                ),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def get_articles_since(since: datetime):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM articles WHERE collected_at >= ? ORDER BY views DESC NULLS LAST",
            (since.isoformat(),),
        ).fetchall()
        return [dict(r) for r in rows]


def purge_old_articles(retention_days: int):
    cutoff = (datetime.utcnow() - timedelta(days=retention_days)).isoformat()
    with get_conn() as conn:
        conn.execute("DELETE FROM articles WHERE collected_at < ?", (cutoff,))
        conn.commit()


def export_json_snapshot(path: Path):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM articles ORDER BY collected_at DESC").fetchall()
    with open(path, "w", encoding="utf-8") as f:
        json.dump([dict(r) for r in rows], f, ensure_ascii=False, indent=2)
