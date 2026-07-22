"""TripAdvisor 评论提取"""

import re
import httpx
from models import ReviewRaw
from collectors.base_extractor import BaseExtractor


class TripAdvisorExtractor(BaseExtractor):
    """TripAdvisor 评论提取器"""

    name = "tripadvisor"

    def can_handle(self, url: str) -> bool:
        return "tripadvisor.com" in url or "tripadvisor.cn" in url

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
            print(f"TripAdvisor extraction failed: {e}")

        return reviews

    def _parse_html(self, html: str) -> list[ReviewRaw]:
        reviews = []

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # TripAdvisor 评论通常在 review 区域
            selectors = [
                "[class*='review']", "[data-automation='reviewCard']",
                "[class*='UserReview']", "q[class*='review']",
            ]

            seen = set()
            for selector in selectors:
                for el in soup.select(selector):
                    # 提取内容
                    content_el = el.select_one("p, .review-text, [class*='comment'], q")
                    content = content_el.get_text(strip=True) if content_el else ""
                    if not content or len(content) < 10 or content in seen:
                        continue
                    seen.add(content)

                    # 评分
                    rating = 0
                    rating_el = el.select_one("[class*='bubble'], [class*='rating']")
                    if rating_el:
                        classes = " ".join(rating_el.get("class", []))
                        match = re.search(r'(\d+)', classes)
                        if match:
                            val = int(match.group(1))
                            rating = val if val <= 5 else val // 10

                    # 作者
                    author_el = el.select_one("[class*='username'], [class*='name'], .info_text")
                    author = author_el.get_text(strip=True) if author_el else ""

                    # 日期
                    date_el = el.select_one("span[class*='date'], [class*='ratingDate']")
                    date = date_el.get_text(strip=True) if date_el else ""

                    # 标题
                    title_el = el.select_one("a[class*='title'], h3, [class*='quote']")
                    title = title_el.get_text(strip=True) if title_el else ""

                    reviews.append(ReviewRaw(
                        review_id=f"tripadvisor-{hash(content[:50]) % 100000}",
                        rating=rating,
                        title=title,
                        content=content[:1000],
                        author=author,
                        version="",
                        date=date,
                        vote_sum=0,
                        vote_count=0,
                        store="tripadvisor",
                    ))
        except ImportError:
            pass

        return reviews
