# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.endpoints import api_router
from app.db import Base, postgres_engine
from app.telegram.bot import bot
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Запуск бота
        await bot.start(bot_token=settings.BOT_TOKEN)

        # Ініціалізація БД
        async with postgres_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield  # Додаток працює

    except Exception as e:
        print(f"Помилка при запуску: {e}")
        raise e  # Зупиняємо додаток, якщо ініціалізація не вдалася

    finally:
        # Цей блок виконається гарантовано при будь-якому виході
        await bot.disconnect()
    await postgres_engine.dispose()


app = FastAPI(title="AI News Bot", lifespan=lifespan)
app.include_router(api_router, prefix="/api")