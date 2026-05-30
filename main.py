#!/usr/bin/env python3
"""Main orchestrator — run by GitHub Actions every 3 hours."""

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("main")

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.yaml"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_claude_client(engine: str):
    if engine != "claude_api":
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — falling back to dictionary sentiment")
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        logger.warning("anthropic package not installed — falling back to dictionary sentiment")
        return None


def run():
    cfg = load_config()

    from db import init_db, is_duplicate, save_article, get_articles_since, purge_old_articles, export_json_snapshot
    from rss_collector import collect_rss
    from telegram_collector import collect_telegram
    from filter import filter_articles
    from sentiment import classify, generate_summary
    from mailer import render_digest, send_email, save_last_digest

    init_db()
    purge_old_articles(cfg["storage"]["retention_days"])

    engine = cfg["sentiment"]["engine"]
    claude_client = build_claude_client(engine)

    # Collect
    logger.info("Collecting RSS…")
    rss_articles = collect_rss(cfg["rss_sources"])

    logger.info("Collecting Telegram…")
    tg_articles = collect_telegram(cfg["telegram_channels"])

    all_raw = rss_articles + tg_articles
    logger.info("Total raw articles: %d", len(all_raw))

    # Filter by company keywords
    filtered = filter_articles(all_raw, cfg["companies"])
    logger.info("After keyword filter: %d", len(filtered))

    # Deduplicate, enrich, save
    new_articles = []
    for article in filtered:
        if is_duplicate(article.get("url", ""), article.get("title", "")):
            continue
        text = f"{article.get('title', '')} {article.get('raw_text', '')}"
        article["sentiment"] = classify(text, engine, claude_client)
        article["summary"] = generate_summary(
            article.get("title", ""), article.get("raw_text", ""), engine, claude_client
        )
        if save_article(article):
            new_articles.append(article)

    logger.info("New articles saved: %d", len(new_articles))

    # Export snapshot
    export_json_snapshot(DATA_DIR / "snapshot.json")

    now_utc = datetime.now(timezone.utc)
    period_from = now_utc - timedelta(hours=cfg["schedule"]["interval_hours"])

    # Always render and save digest for GitHub Pages (even if no new articles)
    all_recent = get_articles_since(period_from - timedelta(hours=cfg["schedule"]["interval_hours"] * 4))
    display_articles = new_articles if new_articles else all_recent
    if display_articles:
        html = render_digest(display_articles, period_from, now_utc)
        save_last_digest(html)
        logger.info("Digest saved (%d articles)", len(display_articles))

    if not new_articles:
        logger.info("No new articles — skipping email")
        return

    html = render_digest(new_articles, period_from, now_utc)
    save_last_digest(html)

    if not os.environ.get("GMAIL_USER"):
        logger.info("GMAIL_USER not set — skipping email send")
        return

    send_email(html, now_utc)
    logger.info("Done.")


if __name__ == "__main__":
    run()
