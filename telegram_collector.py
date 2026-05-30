import asyncio
import base64
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

POSTS_PER_CHANNEL = 50


async def _fetch_channel(client, channel: str) -> list[dict]:
    articles = []
    try:
        entity = await client.get_entity(channel)
        async for message in client.iter_messages(entity, limit=POSTS_PER_CHANNEL):
            if not message.text:
                continue
            title = message.text[:200].split("\n")[0].strip()
            url = f"https://t.me/{channel}/{message.id}"
            articles.append(
                {
                    "title": title,
                    "url": url,
                    "source": f"Telegram @{channel}",
                    "published_at": message.date.isoformat() if message.date else None,
                    "raw_text": message.text,
                    "views": getattr(message, "views", None),
                }
            )
        logger.info("Telegram @%s: %d posts", channel, len(articles))
    except Exception as exc:
        logger.error("Telegram @%s failed: %s", channel, exc)
    return articles


def collect_telegram(channels: list[str]) -> list[dict]:
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    session_b64 = os.environ.get("TELEGRAM_SESSION")

    if not all([api_id, api_hash, session_b64]):
        logger.warning("Telegram credentials not set — skipping Telegram collection")
        return []

    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession

        session_str = base64.b64decode(session_b64).decode()

        async def _run():
            async with TelegramClient(StringSession(session_str), int(api_id), api_hash) as client:
                tasks = [_fetch_channel(client, ch) for ch in channels]
                results = await asyncio.gather(*tasks)
                return [item for sublist in results for item in sublist]

        return asyncio.run(_run())
    except ImportError:
        logger.warning("telethon not installed — skipping Telegram collection")
        return []
    except Exception as exc:
        logger.error("Telegram collection failed: %s", exc)
        return []
