#tasks.py
import logging
from celery_worker import celery_app
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.db import SyncSessionLocal
from app.models import Source, NewsItem, Keyword, Post
from app.news_parser.sites import parse_site
from app.news_parser.telegram import parse_telegram_channel

logger = logging.getLogger(__name__)


# ─── Task 1: Parse all enabled site sources ──────────────────────────────────

@celery_app.task(name="app.tasks.parse_sites_task", bind=True, max_retries=3)
def parse_sites_task(self):
    with SyncSessionLocal() as db:
        result = db.execute(
            select(Source).where(Source.type == "site", Source.enabled == True)
        )
        sources = result.scalars().all()

    # ДЕБАГ: виводимо скільки джерел знайдено
    logger.info(f"DEBUG: Found {len(sources)} sources to parse.")

    try:
        all_items = []
        for source in sources:
            logger.info(f"DEBUG: Parsing source: {source.url}")
            items = parse_site(source.url, source.name)
            logger.info(f"DEBUG: Got {len(items)} items from {source.url}")
            all_items.extend(items)

        if all_items:
            filter_and_store_task.delay(all_items)

        logger.info(f"parse_sites_task: fetched {len(all_items)} items from {len(sources)} sources")
        return {"number_of_items": len(all_items)}

    except Exception as exc:  # <--- Цей рядок має бути рівно під словом 'try'
        logger.error(f"Error in parse_sites_task: {exc}")  # Корисно додати лог помилки
        raise self.retry(exc=exc, countdown=60)

# ─── Task 2: Parse all enabled Telegram sources ───────────────────────────────
# TODO: enable when Telegram API credentials are available

@celery_app.task(name="app.tasks.parse_telegram_task", bind=True, max_retries=3)
def parse_telegram_task(self):
    with SyncSessionLocal() as db:
        result = db.execute(
            select(Source).where(Source.type == "tg", Source.enabled == True)
        )
        sources = result.scalars().all()
    try:
        all_items = []
        for source in sources:
            items = parse_telegram_channel(source.url, source.name)  # returns [] until creds set
            all_items.extend(items)
        if all_items:
            filter_and_store_task.delay(all_items)
        logger.info(f"parse_telegram_task: fetched {len(all_items)} items from {len(sources)} sources")
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


# ─── Task 3: Filter by keywords, deduplicate, store NewsItems ─────────────────

@celery_app.task(name="app.tasks.filter_and_store_task")
def filter_and_store_task(items: list):
    with SyncSessionLocal() as db:
        kw_result = db.execute(select(Keyword))
        keywords = [k.word.lower() for k in kw_result.scalars().all()]

    saved_ids = []
    for item in items:
        # Keyword filter: if keywords are configured, only pass matching items
        if keywords:
            text = (
                f"{item.get('title', '')} "
                f"{item.get('summary', '')} "
                f"{item.get('raw_text', '')}"
            ).lower()
            if not any(kw in text for kw in keywords):
                continue

        with SyncSessionLocal() as db:
            news = NewsItem(**item)
            db.add(news)
            try:
                db.commit()
                db.refresh(news)
                saved_ids.append(news.id)
            except IntegrityError:
                db.rollback()  # duplicate title/url — skip

    logger.info(f"filter_and_store_task: stored {len(saved_ids)} new news items")
    for news_id in saved_ids:
        generate_post_task.delay(news_id)


# ─── Task 4: Generate AI post for a NewsItem ─────────────────────────────────

@celery_app.task(name="app.tasks.generate_post_task", bind=True, max_retries=2)
def generate_post_task(self, news_id: int):
    from app.ai.generator import generate_post_text

    with SyncSessionLocal() as db:
        news = db.get(NewsItem, news_id)
        if not news:
            return None

        # 1. Спробуємо згенерувати текст
        try:
            generated_text = generate_post_text(news)
        except Exception as exc:
            # Якщо сталася помилка AI, ставимо статус failed
            post = Post(news_id=news_id, generated_text="Error generating", status="failed")
            db.add(post)
            db.commit()
            raise self.retry(exc=exc, countdown=120)

        # 2. Додаткова перевірка: якщо текст пустий — не зберігаємо "null"
        if not generated_text:
            logger.error(f"AI returned empty text for news_id {news_id}")
            return None

        # 3. Тепер зберігаємо успішний результат
        post = Post(news_id=news_id, generated_text=generated_text, status="generated")
        db.add(post)
        db.commit()
        db.refresh(post)

    publish_telegram_task.delay(post.id)
    return post.id


# ─── Task 5: Publish a Post to Telegram ──────────────────────────────────────

@celery_app.task(name="app.tasks.publish_telegram_task", bind=True, max_retries=3)
def publish_telegram_task(self, post_id: int):
    from app.telegram.publisher import publish_post
    from datetime import datetime, timezone
    with SyncSessionLocal() as db:
        post = db.get(Post, post_id)
        if not post or post.status == "published":
            return
        try:
            publish_post(post.generated_text)
            post.status = "published"
            post.published_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as exc:
            post.status = "failed"
            db.commit()
            raise self.retry(exc=exc, countdown=60)


# parse_sites_task|parse_telegram_task -> ParsedItem
# -> filter_and_store_task -> Save to DB -> NewsItem
# -> generate_post_task -> Post
# -> publish_telegram_task -> Make Telegram Post