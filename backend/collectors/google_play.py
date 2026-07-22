"""Google Play Store 评论采集"""

import asyncio
import re
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from models import ReviewRaw
from collectors.base_extractor import BaseExtractor


def parse_google_play_url(url: str) -> str:
    """从 Google Play URL 提取 app_id"""
    match = re.search(r'play\.google\.com/store/apps/details\?.*?id=([a-zA-Z0-9._]+)', url)
    if not match:
        raise ValueError(f"无法解析 Google Play URL: {url}")
    return match.group(1)


class GooglePlayExtractor(BaseExtractor):
    """Google Play Store 评论提取器"""

    name = "google"

    def can_handle(self, url: str) -> bool:
        return "play.google.com" in url

    async def extract(self, url: str, max_pages: int = 5) -> list[ReviewRaw]:
        try:
            app_id = parse_google_play_url(url)
        except ValueError:
            return []

        all_reviews = []
        continuation_token = ""

        async with httpx.AsyncClient() as client:
            for page in range(max_pages):
                try:
                    reviews, continuation_token = await self._fetch_page(
                        client, app_id, continuation_token=continuation_token,
                    )
                    if not reviews:
                        break
                    all_reviews.extend(reviews)
                    if not continuation_token:
                        break
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"Google Play page {page + 1} failed: {e}")
                    break

        return all_reviews

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=15))
    async def _fetch_page(self, client: httpx.AsyncClient, app_id: str,
                          lang: str = "en", country: str = "us",
                          sort: int = 2, count: int = 100,
                          continuation_token: str = "") -> tuple[list[ReviewRaw], str]:
        url = "https://storebackend.com/reviews/getReviews"
        payload = {
            "appId": app_id,
            "hl": lang,
            "gl": country,
            "sort": sort,
            "count": count,
        }
        if continuation_token:
            payload["continuationToken"] = continuation_token

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
        }

        response = await client.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        reviews = []
        for entry in data.get("reviews", []):
            reviews.append(ReviewRaw(
                review_id=str(entry.get("reviewId", "")),
                rating=int(entry.get("score", 0)),
                title="",
                content=entry.get("reviewText", "") or "",
                author=entry.get("userName", "") or "",
                version=str(entry.get("reviewCreatedTimestamp", {}).get("seconds", "")),
                date=str(entry.get("reviewCreatedTimestamp", {}).get("seconds", "")),
                vote_sum=int(entry.get("thumbsUpCount", 0)),
                vote_count=0,
                store="google",
            ))

        next_token = data.get("continuationToken", "")
        return reviews, next_token
