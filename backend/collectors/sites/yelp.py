"""Yelp 评论提取"""

import re
import httpx
from models import ReviewRaw
from collectors.base_extractor import BaseExtractor


class YelpExtractor(BaseExtractor):
    """Yelp 评论提取器"""

    name = "yelp"

    def can_handle(self, url: str) -> bool:
        return "yelp.com" in url or "yelp.ca" in url

    async def extract(self, url: str, max_pages: int = 3) -> list[ReviewRaw]:
        reviews = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    reviews = self._parse_html(resp.text)
        except Exception as e:
            print(f"Yelp extraction failed: {e}")

        return reviews

    def _parse_html(self, html: str) -> list[ReviewRaw]:
        reviews = []

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            for el in soup.select("[class*='review'], [class*='comment']"):
                content_el = el.select_one("p, .review-content, [lang]")
                content = content_el.get_text(strip=True) if content_el else ""
                if not content or len(content) < 10:
                    continue

                # 评分
                rating = 0
                rating_el = el.select_one("[class*='star'], [aria-label*='star']")
                if rating_el:
                    label = rating_el.get("aria-label", "") or " ".join(rating_el.get("class", []))
                    match = re.search(r'(\d)', label)
                    if match:
                        rating = int(match.group(1))

                # 作者
                author_el = el.select_one("[class*='user'], [class*='name'], a[href*='/user_details']")
                author = author_el.get_text(strip=True) if author_el else ""

                # 日期
                date_el = el.select_one("[class*='date'], [class*='time'], span")
                date = date_el.get_text(strip=True) if date_el else ""

                reviews.append(ReviewRaw(
                    review_id=f"yelp-{hash(content[:50]) % 100000}",
                    rating=rating,
                    title="",
                    content=content[:1000],
                    author=author,
                    version="",
                    date=date,
                    vote_sum=0,
                    vote_count=0,
                    store="yelp",
                ))
        except ImportError:
            pass

        return reviews
