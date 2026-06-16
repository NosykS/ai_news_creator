import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import Source, Keyword, NewsItem, Post
from app.api.schemas import (
    SourceCreate, SourceUpdate, SourceOut,
    KeywordCreate, KeywordOut,
    NewsItemOut, PostOut,
    TriggerResponse,
    GenerateRequest, GenerateResponse,
)
from app.telegram.publisher import publish_post

logger = logging.getLogger(__name__)
api_router = APIRouter()


# ---- Sources (/api/sources/) ----

@api_router.get("/sources/", response_model=list[SourceOut], tags=["Sources"])
async def list_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source))
    return result.scalars().all()


@api_router.post("/sources/", response_model=SourceOut, status_code=201, tags=["Sources"])
async def create_source(body: SourceCreate, db: AsyncSession = Depends(get_db)):
    source = Source(**body.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@api_router.get("/sources/{source_id}", response_model=SourceOut, tags=["Sources"])
async def get_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@api_router.patch("/sources/{source_id}", response_model=SourceOut, tags=["Sources"])
async def update_source(source_id: int, body: SourceUpdate, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(source, field, value)
    await db.commit()
    await db.refresh(source)
    return source


@api_router.delete("/sources/{source_id}", status_code=204, tags=["Sources"])
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    await db.delete(source)
    await db.commit()


# ---- Keywords (/api/keywords/) ----

@api_router.get("/keywords/", response_model=list[KeywordOut], tags=["Keywords"])
async def list_keywords(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Keyword))
    return result.scalars().all()


@api_router.post("/keywords/", response_model=KeywordOut, status_code=201, tags=["Keywords"])
async def create_keyword(body: KeywordCreate, db: AsyncSession = Depends(get_db)):
    kw = Keyword(**body.model_dump())
    db.add(kw)
    await db.commit()
    await db.refresh(kw)
    return kw


@api_router.delete("/keywords/{keyword_id}", status_code=204, tags=["Keywords"])
async def delete_keyword(keyword_id: int, db: AsyncSession = Depends(get_db)):
    kw = await db.get(Keyword, keyword_id)
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    await db.delete(kw)
    await db.commit()


# ---- News items (/api/news/) ----

@api_router.get("/news/", response_model=list[NewsItemOut], tags=["News"])
async def list_news(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NewsItem).order_by(NewsItem.published_at.desc()))
    return result.scalars().all()


@api_router.delete("/news/{news_id}", status_code=204, tags=["News"])
async def delete_source(news_id: int, db: AsyncSession = Depends(get_db)):
    news = await db.get(NewsItem, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    await db.delete(news)
    await db.commit()


# ---- Posts (/api/posts/) ----

@api_router.get("/posts/", response_model=list[PostOut], tags=["Posts"])
async def list_posts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Post).order_by(Post.id.desc()))
    return result.scalars().all()

@api_router.delete("/posts/{post_id}", status_code=204, tags=["Posts"])
async def delete_post(post_id: int, db: AsyncSession = Depends(get_db)):
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    await db.delete(post)
    await db.commit()
    if post.news_id:
        news = await db.get(NewsItem, post.news_id)
        await db.delete(news)
    await db.commit()

@api_router.get("/posts/errors/", response_model=list[PostOut], tags=["Posts"])
async def list_failed_posts(db: AsyncSession = Depends(get_db)):
    """Returns all posts that failed during generation or publishing."""
    result = await db.execute(
        select(Post).where(Post.status == "failed").order_by(Post.id.desc())
    )
    return result.scalars().all()


# ---- Manual parse trigger (/api/parse/trigger) ----

@api_router.post("/parse/trigger", response_model=TriggerResponse, tags=["Tasks"])
async def trigger_parse():
    """Manually trigger news parsing for all enabled sources."""
    from app.tasks import parse_sites_task, parse_telegram_task
    task_sites = parse_sites_task.delay()
    # parse_telegram_task.delay()
    return TriggerResponse(task_id=task_sites.id, status="queued")


# ---- Manual AI generation (/api/generate/) ----

@api_router.post("/generate/", response_model=GenerateResponse, tags=["Tasks"])
async def generate_post(body: GenerateRequest, db: AsyncSession = Depends(get_db)):
    """
    Manually trigger AI post generation for a specific news item.
    Runs synchronously and returns the generated text immediately — useful for testing.
    """
    from app.ai.generator import generate_post_text
    from datetime import datetime, timezone

    news = await db.get(NewsItem, body.news_id)
    if not news:
        raise HTTPException(status_code=404, detail="NewsItem not found")

    try:
        generated_text = generate_post_text(news)
    except Exception as e:
        logger.error(f"Generation failed for news_id={body.news_id}: {e}")
        post = Post(news_id=body.news_id, generated_text="", status="failed")
        db.add(post)
        await db.commit()
        await db.refresh(post)
        raise HTTPException(status_code=502, detail=f"AI generation failed: {e}")

    post = Post(news_id=body.news_id, generated_text=generated_text, status="generated")
    db.add(post)
    await db.commit()
    await db.refresh(post)

    await publish_post(post.generated_text)

    return GenerateResponse(
        post_id=post.id,
        news_id=post.news_id,
        generated_text=post.generated_text,
        status=post.status,
    )