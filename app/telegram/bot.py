# app/telegram/bot.py
from telethon import TelegramClient
from app.config import settings

bot = TelegramClient('bot_session', settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)

async def send_news(text: str):
    await bot.send_message(settings.TELEGRAM_PUBLISH_CHANNEL, text)