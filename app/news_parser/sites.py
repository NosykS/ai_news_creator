import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


def parse_site(url: str, source_name: str) -> list[dict]:
    items = []
    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

        # Використовуємо 'xml' для читання RSS-фіду
        soup = BeautifulSoup(response.text, "xml")

        # В усіх RSS-фідах новини лежать у тегах <item>
        entries = soup.find_all("item")

        for entry in entries[:5]:
            title = entry.find("title").text if entry.find("title") else "Без заголовка"
            link = entry.find("link").text if entry.find("link") else None
            description = entry.find("description").text if entry.find("description") else title

            items.append({
                "title": title,
                "url": link,
                "summary": description[:500],
                "source": source_name,
                "published_at": datetime.now(timezone.utc),
                "raw_text": description,
            })

    except Exception as e:
        logger.error(f"Error parsing RSS {url}: {e}")

    return items