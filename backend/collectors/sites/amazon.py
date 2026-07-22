"""Amazon 产品评论提取"""

import re
import httpx
from models import ReviewRaw
from collectors.base_extractor import BaseExtractor


class AmazonExtractor(BaseExtractor):
    """Amazon 产品评论提取器"""

    name = "amazon"

    def can_handle(self, url: str) -> bool:
        return any(d in url for d in ["amazon.com", "amazon.cn", "amazon.co.jp", "amazon.co.uk"])

    async def extract(self, url: str, max_pages: int = 3) -> list[ReviewRaw]:
        reviews = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        review_url = self._build_review_url(url)

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                resp = await client.get(review_url, headers=headers)
                resp.raise_for_status()
                html = resp.text

                reviews = self._parse_html(html)
        except Exception as e:
            print(f"Amazon extraction failed: {e}")

        return reviews

    def _build_review_url(self, url: str) -> str:
        """从产品页 URL 构建评论页 URL"""
        match = re.search(r'/dp/([A-Z0-9]{10})', url)
        if match:
            asin = match.group(1)
            # 提取域名
            if "amazon.cn" in url:
                return f"https://www.amazon.cn/product-reviews/{asin}"
            elif "amazon.co.jp" in url:
                return f"https://www.amazon.co.jp/product-reviews/{asin}"
            elif "amazon.co.uk" in url:
                return f"https://www.amazon.co.uk/product-reviews/{asin}"
            else:
                return f"https://www.amazon.com/product-reviews/{asin}"
        return url

    def _parse_html(self, html: str) -> list[ReviewRaw]:
        """解析 Amazon 评论 HTML"""
        reviews = []

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            for review_el in soup.select("[data-hook='review']"):
                title_el = review_el.select_one("[data-hook='review-title']")
                body_el = review_el.select_one("[data-hook='review-body']")
                rating_el = review_el.select_one("[data-hook='review-star-rating'], .review-rating")
                author_el = review_el.select_one(".a-profile-name")
                date_el = review_el.select_one("[data-hook='review-date']")

                rating = 0
                if rating_el:
                    match = re.search(r'(\d)', rating_el.get_text())
                    if match:
                        rating = int(match.group(1))

                title = ""
                if title_el:
                    # Amazon 标题格式通常是 "X.0 out of 5 stars Title"
                    title_text = title_el.get_text(strip=True)
                    parts = title_text.split(".", 1)
                    if len(parts) > 1:
                        title = parts[-1].strip()
                    else:
                        title = title_text

                content = body_el.get_text(strip=True) if body_el else ""
                if not content or len(content) < 3:
                    continue

                reviews.append(ReviewRaw(
                    review_id=f"amazon-{hash(content[:50]) % 100000}",
                    rating=rating,
                    title=title,
                    content=content[:1000],
                    author=author_el.get_text(strip=True) if author_el else "",
                    version="",
                    date=date_el.get_text(strip=True) if date_el else "",
                    vote_sum=0,
                    vote_count=0,
                    store="amazon",
                ))
        except ImportError:
            # 无 BeautifulSoup，用正则
            reviews = self._parse_with_regex(html)

        return reviews

    def _parse_with_regex(self, html: str) -> list[ReviewRaw]:
        """使用正则表达式解析 Amazon 评论"""
        reviews = []
        # 匹配评论标题和内容
        patterns = [
            (r'<span[^>]*data-hook="review-title"[^>]*>(.*?)</span>', r'<span[^>]*data-hook="review-body"[^>]*>(.*?)</span>'),
        ]
        for title_pat, body_pat in patterns:
            titles = re.findall(title_pat, html, re.DOTALL)
            bodies = re.findall(body_pat, html, re.DOTALL)
            for i, (t, b) in enumerate(zip(titles, bodies)):
                title = re.sub(r'<[^>]+>', '', t).strip()
                content = re.sub(r'<[^>]+>', '', b).strip()
                if content and len(content) > 3:
                    reviews.append(ReviewRaw(
                        review_id=f"amazon-regex-{i}",
                        rating=0,
                        title=title,
                        content=content[:1000],
                        author="",
                        version="",
                        date="",
                        vote_sum=0,
                        vote_count=0,
                        store="amazon",
                    ))
        return reviews
