import logging

# TODO: uncomment when Telegram API credentials are available
# import asyncio
# from datetime import timezone
# from telethon import TelegramClient
# from telethon.tl.types import Message
# from app.config import settings

logger = logging.getLogger(__name__)


# async def _fetch_channel(channel_username: str, source_name: str, limit: int = 20) -> list[dict]:
#     items = []
#     client = TelegramClient(
#         settings.TELEGRAM_SESSION,
#         settings.TELEGRAM_API_ID,
#         settings.TELEGRAM_API_HASH,
#     )
#     try:
#         await client.start()
#         async for message in client.iter_messages(channel_username, limit=limit):
#             if not isinstance(message, Message) or not message.text:
#                 continue
#             title = message.text[:100].replace("\n", " ")
#             items.append({
#                 "title": title,
#                 "url": None,
#                 "summary": message.text[:500],
#                 "source": source_name,
#                 "published_at": message.date.replace(tzinfo=timezone.utc),
#                 "raw_text": message.text,
#             })
#     except Exception as e:
#         logger.error(f"Error fetching Telegram channel {channel_username}: {e}")
#     finally:
#         await client.disconnect()
#     return items


def parse_telegram_channel(channel_username: str, source_name: str) -> list[dict]:
    """Sync wrapper for use inside Celery tasks."""
    logger.warning("Telegram parsing is disabled (no credentials configured)")
    return []
    # return asyncio.run(_fetch_channel(channel_username, source_name))