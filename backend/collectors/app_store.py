"""RSS Feed 数据采集 + 文件导入"""

import asyncio
import re
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from models import ReviewRaw


def parse_app_store_url(url: str) -> tuple[str, str]:
    """从 App Store URL 提取 (country_code, app_id)"""
    match = re.search(r'apps\.apple\.com/([a-z]{2})/(?:app/)?[^/]+/id(\d+)', url)
    if not match:
        raise ValueError(f"\u65e0\u6cd5\u89e3\u6790 App Store URL: {url}")
    return match.group(1), match.group(2)


def build_rss_url(app_id: str, page: int = 1, sort: str = "mostrecent", country: str = "us") -> str:
    return f"https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id/{app_id}/sortby={sort}/json"


def parse_rss_entry(entry: dict) -> ReviewRaw:
    return ReviewRaw(
        review_id=entry.get("id", {}).get("label", "") or "",
        rating=int(entry.get("im:rating", {}).get("label", "0")),
        title=entry.get("title", {}).get("label", "") or "",
        content=entry.get("content", {}).get("label", "") or "",
        author=entry.get("author", {}).get("name", {}).get("label", "") or "",
        version=entry.get("im:version", {}).get("label", "") or "",
        date=entry.get("updated", {}).get("label", "") or "",
        vote_sum=int(entry.get("im:voteSum", {}).get("label", "0")),
        vote_count=int(entry.get("im:voteCount", {}).get("label", "0")),
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=30))
async def fetch_page(client: httpx.AsyncClient, app_id: str, page: int, sort: str, country: str) -> list[ReviewRaw]:
    url = build_rss_url(app_id, page, sort, country)
    response = await client.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    entries = data.get("feed", {}).get("entry", [])
    return [parse_rss_entry(e) for e in entries] if entries else []


async def collect_reviews(app_id: str, sort: str = "mostrecent", country: str = "us",
                          max_pages: int = 10, progress_callback=None) -> list[ReviewRaw]:
    all_reviews = []
    async with httpx.AsyncClient() as client:
        for page in range(1, max_pages + 1):
            reviews = await fetch_page(client, app_id, page, sort, country)
            if not reviews:
                break
            all_reviews.extend(reviews)
            if progress_callback:
                await progress_callback("collecting", int(page / max_pages * 100),
                                        f"\u91c7\u96c6\u7b2c {page}/{max_pages} \u9875")
            await asyncio.sleep(1.0)
    return all_reviews


async def collect_reviews_from_file(file_data: list[dict]) -> list[ReviewRaw]:
    """从文件导入数据创建 ReviewRaw 列表"""
    reviews = []
    for i, item in enumerate(file_data):
        try:
            reviews.append(ReviewRaw(
                review_id=item.get("review_id", f"file-{i}"),
                rating=int(item.get("rating", 0)),
                title=item.get("title", "") or "",
                content=item.get("content", "") or "",
                author=item.get("author", "") or "",
                version=item.get("version", "") or "",
                date=item.get("date", "") or "",
                vote_sum=int(item.get("vote_sum", 0)),
                vote_count=int(item.get("vote_count", 0)),
            ))
        except Exception:
            continue
    return reviews
