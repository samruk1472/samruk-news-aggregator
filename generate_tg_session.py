#!/usr/bin/env python3
"""
One-time script to generate a Telethon StringSession for use in GitHub Secrets.
Run locally: python generate_tg_session.py
Copy the printed base64 string to TELEGRAM_SESSION secret.
"""

import asyncio
import base64
import os

from telethon import TelegramClient
from telethon.sessions import StringSession


async def main():
    api_id = int(input("Enter TELEGRAM_API_ID: ").strip())
    api_hash = input("Enter TELEGRAM_API_HASH: ").strip()

    async with TelegramClient(StringSession(), api_id, api_hash) as client:
        session_str = client.session.save()

    encoded = base64.b64encode(session_str.encode()).decode()
    print("\n✅ Your TELEGRAM_SESSION (copy this to GitHub Secrets):")
    print(encoded)


if __name__ == "__main__":
    asyncio.run(main())
