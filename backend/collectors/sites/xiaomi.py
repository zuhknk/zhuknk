"""小米应用商店评论提取"""

import re
import httpx
from models import ReviewRaw
from collectors.base_extractor import BaseExtractor


class XiaomiExtractor(BaseExtractor):
    """小米应用商店评论提取器"""

    name = "xiaomi"

    def can_handle(self, url: str) -> bool:
        return "app.mi.com" in url

    async def extract(self, url: str, max_pages: int = 3) -> list[ReviewRaw]:
        app_id = self._extract_app_id(url)
        if not app_id:
            return []

        reviews = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    reviews = self._parse_html(resp.text)
        except Exception as e:
            print(f"Xiaomi extraction failed: {e}")

        return reviews

    def _extract_app_id(self, url: str) -> str:
        """从 URL 提取应用 ID"""
        match = re.search(r'/(\d+)', url)
        return match.group(1) if match else ""

    def _parse_html(self, html: str) -> list[ReviewRaw]:
        reviews = []

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            for el in soup.select("[class*='comment'], [class*='review'], [class*='user-review']"):
                content_el = el.select_one("p, .content, .text, .comment-content")
                content = content_el.get_text(strip=True) if content_el else ""
                if not content or len(content) < 3:
                    continue

                rating = 0
                rating_el = el.select_one("[class*='star']")
                if rating_el:
                    classes = " ".join(rating_el.get("class", []))
                    match = re.search(r'(\d)', classes)
                    if match:
                        rating = int(match.group(1))

                author_el = el.select_one(".name, .user, .nick")
                author = author_el.get_text(strip=True) if author_el else ""

                date_el = el.select_one(".date, .time")
                date = date_el.get_text(strip=True) if date_el else ""

                reviews.append(ReviewRaw(
                    review_id=f"xiaomi-{hash(content[:50]) % 100000}",
                    rating=rating,
                    title="",
                    content=content[:1000],
                    author=author,
                    version="",
                    date=date,
                    vote_sum=0,
                    vote_count=0,
                    store="xiaomi",
                ))
        except ImportError:
            pass

        return reviews
