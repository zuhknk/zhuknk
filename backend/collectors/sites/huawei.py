"""华为应用市场评论提取"""

import re
import httpx
from models import ReviewRaw
from collectors.base_extractor import BaseExtractor


class HuaweiExtractor(BaseExtractor):
    """华为应用市场评论提取器"""

    name = "huawei"

    def can_handle(self, url: str) -> bool:
        return "appgallery.huawei.com" in url

    async def extract(self, url: str, max_pages: int = 3) -> list[ReviewRaw]:
        # 从 URL 提取 app ID
        app_id = self._extract_app_id(url)
        if not app_id:
            return []

        reviews = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/html",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                # 华为应用市场 API
                api_url = f"https://appgallery.huawei.com/appdl/{app_id}"
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    reviews = self._parse_html(resp.text)
        except Exception as e:
            print(f"Huawei extraction failed: {e}")

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

            # 查找评论区域
            for el in soup.select("[class*='comment'], [class*='review'], [class*='rating']"):
                content_el = el.select_one("p, .content, .text")
                content = content_el.get_text(strip=True) if content_el else ""
                if not content or len(content) < 3:
                    continue

                # 评分
                rating = 0
                rating_el = el.select_one("[class*='star']")
                if rating_el:
                    match = re.search(r'(\d)', rating_el.get("class", [""])[0] if rating_el.get("class") else "")
                    if match:
                        rating = int(match.group(1))

                # 作者
                author_el = el.select_one(".name, .user")
                author = author_el.get_text(strip=True) if author_el else ""

                # 日期
                date_el = el.select_one(".date, .time")
                date = date_el.get_text(strip=True) if date_el else ""

                reviews.append(ReviewRaw(
                    review_id=f"huawei-{hash(content[:50]) % 100000}",
                    rating=rating,
                    title="",
                    content=content[:1000],
                    author=author,
                    version="",
                    date=date,
                    vote_sum=0,
                    vote_count=0,
                    store="huawei",
                ))
        except ImportError:
            pass

        return reviews
