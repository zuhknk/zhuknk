"""知乎评论/回答提取"""

import re
import httpx
from models import ReviewRaw
from collectors.base_extractor import BaseExtractor


class ZhihuExtractor(BaseExtractor):
    """知乎评论/回答提取器"""

    name = "zhihu"

    def can_handle(self, url: str) -> bool:
        return "zhihu.com" in url

    async def extract(self, url: str, max_pages: int = 3) -> list[ReviewRaw]:
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
            print(f"Zhihu extraction failed: {e}")

        return reviews

    def _parse_html(self, html: str) -> list[ReviewRaw]:
        reviews = []

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # 知乎回答通常在 .AnswerItem 或 .RichContent 中
            selectors = [
                ".AnswerItem", ".RichContent", "[class*='answer']",
                ".CommentItem", "[class*='comment']",
            ]

            seen = set()
            for selector in selectors:
                for el in soup.select(selector):
                    # 提取内容
                    content_el = el.select_one(".RichContent-inner, .comment-content, p")
                    content = content_el.get_text(strip=True) if content_el else ""
                    if not content or len(content) < 10 or content in seen:
                        continue
                    seen.add(content)

                    # 作者
                    author_el = el.select_one(".AuthorInfo-name, .UserLink-link, [class*='author']")
                    author = author_el.get_text(strip=True) if author_el else ""

                    # 知乎通常没有评分
                    reviews.append(ReviewRaw(
                        review_id=f"zhihu-{hash(content[:50]) % 100000}",
                        rating=0,
                        title="",
                        content=content[:1000],
                        author=author,
                        version="",
                        date="",
                        vote_sum=0,
                        vote_count=0,
                        store="zhihu",
                    ))
        except ImportError:
            pass

        return reviews
