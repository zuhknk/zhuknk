"""App Store 评论数据采集模块"""

import re
import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from models import ReviewRaw

logger = logging.getLogger(__name__)


# URL 解析正则
APP_STORE_URL_PATTERN = re.compile(
    r"apps\.apple\.com/([a-z]{2})/(?:app/)?[^/]+/id(\d+)"
)


def parse_app_store_url(url: str) -> tuple[str, str]:
    """从 App Store 链接中提取 (country_code, app_id)"""
    match = APP_STORE_URL_PATTERN.search(url)
    if not match:
        raise ValueError(f"无法解析 App Store 链接: {url}")
    return match.group(1), match.group(2)


def build_rss_url(
    app_id: str,
    page: int = 1,
    sort: str = "mostrecent",
    country: str = "us",
) -> str:
    """构建 RSS Feed 请求 URL"""
    return (
        f"{settings.RSS_BASE_URL.format(country=country)}"
        f"/page={page}/id={app_id}/sortby={sort}/json"
    )


def parse_rss_entry(entry: dict) -> ReviewRaw:
    """将 RSS 条目解析为 ReviewRaw 模型"""
    return ReviewRaw(
        review_id=entry["id"]["label"],
        rating=int(entry["im:rating"]["label"]),
        title=entry["title"]["label"],
        content=entry["content"]["label"],
        author=entry["author"]["name"]["label"],
        date=datetime.fromisoformat(entry["updated"]["label"]),
        version=entry["im:version"]["label"],
        vote_sum=int(entry.get("im:voteSum", {}).get("label", "0")),
        vote_count=int(entry.get("im:voteCount", {}).get("label", "0")),
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
async def fetch_page(
    client: httpx.AsyncClient,
    app_id: str,
    page: int,
    sort: str = "mostrecent",
    country: str = "us",
) -> list[ReviewRaw]:
    """获取单页评论数据"""
    url = build_rss_url(app_id, page, sort, country)
    logger.info(f"Fetching page {page}: {url}")

    resp = await client.get(url, timeout=30.0)
    resp.raise_for_status()

    data = resp.json()
    entries = data.get("feed", {}).get("entry", [])

    if not entries:
        logger.info(f"Page {page} returned no entries")
        return []

    reviews = [parse_rss_entry(entry) for entry in entries]
    logger.info(f"Page {page}: fetched {len(reviews)} reviews")
    return reviews


async def collect_reviews(
    app_id: str,
    sort: str = "mostrecent",
    country: str = "us",
    max_pages: int = settings.RSS_MAX_PAGES,
    progress_callback: Optional[callable] = None,
) -> list[ReviewRaw]:
    """
    采集指定 App 的评论数据

    Args:
        app_id: App Store 应用 ID
        sort: 排序方式 (mostrecent / mosthelpful)
        country: 国家代码 (固定 us)
        max_pages: 最大页数
        progress_callback: 进度回调

    Returns:
        评论列表
    """
    all_reviews: list[ReviewRaw] = []

    async with httpx.AsyncClient() as client:
        for page in range(1, max_pages + 1):
            reviews = await fetch_page(client, app_id, page, sort, country)

            if not reviews:
                logger.info(f"Stopping at page {page}: no more reviews")
                break

            all_reviews.extend(reviews)

            if progress_callback:
                progress = min(page * 100 // max_pages, 100)
                await progress_callback(
                    "collecting",
                    progress,
                    f"已采集 {len(all_reviews)} 条评论 (第 {page}/{max_pages} 页)",
                )

            # 速率限制
            await asyncio.sleep(settings.RSS_REQUEST_INTERVAL)

    logger.info(f"Collection complete: {len(all_reviews)} total reviews")
    return all_reviews


async def collect_reviews_from_file(
    file_content: str,
    file_format: str = "json",
    progress_callback: Optional[callable] = None,
) -> list[ReviewRaw]:
    """从文件导入评论数据"""
    import json
    import csv
    from io import StringIO

    reviews: list[ReviewRaw] = []

    if file_format == "json":
        data = json.loads(file_content)
        if isinstance(data, list):
            items = data
        else:
            items = data.get("reviews", data.get("data", []))

        for item in items:
            try:
                reviews.append(ReviewRaw(
                    review_id=str(item.get("review_id", item.get("id", ""))),
                    rating=int(item.get("rating", 0)),
                    title=str(item.get("title", "")),
                    content=str(item.get("content", item.get("review", ""))),
                    author=str(item.get("author", item.get("userName", ""))),
                    date=datetime.fromisoformat(item.get("date", "2020-01-01T00:00:00-07:00")),
                    version=str(item.get("version", "")),
                    vote_sum=int(item.get("vote_sum", item.get("voteSum", 0))),
                    vote_count=int(item.get("vote_count", item.get("voteCount", 0))),
                ))
            except Exception as e:
                logger.warning(f"Skip invalid row: {e}")

    elif file_format == "csv":
        reader = csv.DictReader(StringIO(file_content))
        for row in reader:
            try:
                reviews.append(ReviewRaw(
                    review_id=str(row.get("review_id", row.get("id", ""))),
                    rating=int(row.get("rating", 0)),
                    title=str(row.get("title", "")),
                    content=str(row.get("content", row.get("review", ""))),
                    author=str(row.get("author", row.get("userName", ""))),
                    date=datetime.fromisoformat(row.get("date", "2020-01-01T00:00:00-07:00")),
                    version=str(row.get("version", "")),
                    vote_sum=int(row.get("vote_sum", row.get("voteSum", 0))),
                    vote_count=int(row.get("vote_count", row.get("voteCount", 0))),
                ))
            except Exception as e:
                logger.warning(f"Skip invalid row: {e}")

    if progress_callback:
        await progress_callback("collecting", 100, f"从文件导入 {len(reviews)} 条评论")

    return reviews