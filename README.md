# AI News Bot for Telegram

Automated Telegram news channel powered by FastAPI, Celery, RabbitMQ, and OpenAI GPT-4o.
Collects news from websites and Telegram channels, filters by keywords, generates AI posts, and publishes them on a schedule.

## Features

- Parses news from websites (BeautifulSoup) and Telegram channels (Telethon)
- Filters news by configurable keywords, deduplicates by title/URL
- Generates Telegram-ready posts via OpenAI GPT-4o
- Publishes to a Telegram channel automatically
- Celery Beat schedule: runs every 30 minutes
- REST API to manage sources, keywords, view posts, and trigger parsing manually
- Flower dashboard for Celery task monitoring

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI |
| Task queue | Celery + RabbitMQ |
| Result backend | Redis |
| Database | PostgreSQL + SQLAlchemy (async) |
| Parsing | requests + BeautifulSoup |
| Telegram | Telethon |
| AI | OpenAI GPT-4o |
| Monitoring | Flower |

## Project Structure

```
/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings (pydantic-settings)
│   ├── db.py                # SQLAlchemy async engine
│   ├── models.py            # ORM models: Source, NewsItem, Keyword, Post
│   ├── tasks.py             # Celery task pipeline
│   ├── api/
│   │   ├── endpoints.py     # All API route handlers
│   │   └── schemas.py       # Pydantic request/response schemas
│   ├── news_parser/
│   │   ├── sites.py         # Website scraper
│   │   └── telegram.py      # Telegram channel reader (Telethon)
│   ├── ai/
│   │   ├── generator.py     # Post generation logic
│   │   └── openai_client.py # OpenAI client singleton
│   └── telegram/
│       └── publisher.py     # Telegram message sender
├── celery_worker.py         # Celery app + Beat schedule
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env
```

## Setup

### 1. Clone and configure

```bash
git clone <repo-url>
cd ai_news_bot
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
PG_USERNAME=ainewsbot
PG_PASSWORD=postgres
PG_URL=postgres:5432
PG_NAME=ainewsbot

RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672//
REDIS_URL=redis://redis:6379/0

OPENAI_API_KEY=sk-...

# Telegram (optional, see note below)
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_SESSION=anon
TELEGRAM_PUBLISH_CHANNEL=@your_channel
```

> **Telegram credentials**: Get `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` from [my.telegram.org](https://my.telegram.org). The session file must be generated once interactively before running in Docker.

### 2. Start with Docker Compose

```bash
docker-compose up --build
```

Services started:

| Service | URL |
|---|---|
| FastAPI | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| RabbitMQ UI | http://localhost:15672 (guest/guest) |
| Flower | http://localhost:5555 |

Database tables are created automatically on first startup.

## API Endpoints

### Sources

```
GET    /api/sources/          List all sources
POST   /api/sources/          Add a source
GET    /api/sources/{id}      Get a source
PATCH  /api/sources/{id}      Update a source
DELETE /api/sources/{id}      Delete a source
```

**Add a website source:**
```bash
curl -X POST http://localhost:8000/api/sources/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Hacker News", "type": "site", "url": "https://news.ycombinator.com", "enabled": true}'
```

**Add a Telegram channel source:**
```bash
curl -X POST http://localhost:8000/api/sources/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Some Channel", "type": "tg", "url": "@channel_username", "enabled": true}'
```

### Keywords

```
GET    /api/keywords/         List all keywords
POST   /api/keywords/         Add a keyword
DELETE /api/keywords/{id}     Delete a keyword
```

**Add a keyword filter:**
```bash
curl -X POST http://localhost:8000/api/keywords/ \
  -H "Content-Type: application/json" \
  -d '{"word": "python"}'
```

> If no keywords are configured, all news items pass through. If keywords are set, only items containing at least one keyword are stored.

### News & Posts

```
GET /api/news/     List collected news items (newest first)
GET /api/posts/    List generated posts (newest first)
```

### Manual Trigger

```
POST /api/parse/trigger    Trigger parsing immediately (returns task ID)
```

```bash
curl -X POST http://localhost:8000/api/parse/trigger
# {"task_id": "abc-123", "status": "queued"}
```

## Pipeline

```
Celery Beat (every 30 min)
  ├─► parse_sites_task       → scrape enabled site sources
  └─► parse_telegram_task    → read enabled Telegram channel sources
              ↓
  filter_and_store_task      → keyword filter → deduplicate → save NewsItem
              ↓
  generate_post_task         → OpenAI GPT-4o → save Post (status: generated)
              ↓
  publish_telegram_task      → send to Telegram channel → Post (status: published)
```

## Checklist

| # | Feature | Status |
|---|---|---|
| 1 | News collection (sites) | ✅ |
| 2 | News collection (Telegram) | ✅ (disabled until creds added) |
| 3 | Keyword filtering + deduplication | ✅ |
| 4 | Celery task queue (RabbitMQ) | ✅ |
| 5 | AI post generation (OpenAI) | ✅ |
| 6 | Telegram publishing | ✅ (disabled until creds added) |
| 7 | API — sources CRUD | ✅ |
| 8 | API — keywords CRUD | ✅ |
| 9 | API — posts history | ✅ |
| 10 | Manual parse trigger | ✅ |
| 11 | Swagger docs | ✅ `/docs` |
| 12 | Celery Beat schedule | ✅ every 30 min |
| 13 | Flower monitoring | ✅ |
| 14 | Docker Compose | ✅ |