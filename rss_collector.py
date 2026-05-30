import logging
import feedparser
from datetime import datetime
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)


def _parse_date(entry):
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                return parsedate_to_datetime(raw).isoformat()
            except Exception:
                pass
    return None


def _entry_text(entry) -> str:
    parts = [entry.get("title", ""), entry.get("summary", "")]
    content = entry.get("content", [])
    if content:
        parts.append(content[0].get("value", ""))
    return " ".join(parts)


def collect_rss(sources: list[dict]) -> list[dict]:
    articles = []
    for source in sources:
        try:
            feed = feedparser.parse(source["url"], request_headers={"User-Agent": "Mozilla/5.0"})
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                url = entry.get("link", "").strip()
                if not title or not url:
                    continue
                articles.append(
                    {
                        "title": title,
                        "url": url,
                        "source": source["name"],
                        "published_at": _parse_date(entry),
                        "raw_text": _entry_text(entry),
                        "views": None,
                    }
                )
            logger.info("RSS %s: %d entries", source["name"], len(feed.entries))
        except Exception as exc:
            logger.error("RSS %s failed: %s", source["name"], exc)
    return articles
