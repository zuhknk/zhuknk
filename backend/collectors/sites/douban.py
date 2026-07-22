"""豆瓣评论提取"""

import re
import httpx
from models import ReviewRaw
from collectors.base_extractor import BaseExtractor


class DoubanExtractor(BaseExtractor):
    """豆瓣评论提取器（支持电影/书籍/商品等）"""

    name = "douban"

    def can_handle(self, url: str) -> bool:
        return "douban.com" in url

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
                resp.raise_for_status()
                html = resp.text
                reviews = self._parse_html(html)
        except Exception as e:
            print(f"Douban extraction failed: {e}")

        return reviews

    def _parse_html(self, html: str) -> list[ReviewRaw]:
        reviews = []

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # 豆瓣评论通常在 .comment-item 或 .review-item 中
            selectors = [".comment-item", ".review-item", "[class*='comment']"]
            seen = set()

            for selector in selectors:
                for el in soup.select(selector):
                    # 提取评论内容
                    content_el = el.select_one(".short, .comment-content, p")
                    content = content_el.get_text(strip=True) if content_el else ""
                    if not content or len(content) < 5 or content in seen:
                        continue
                    seen.add(content)

                    # 提取评分（星级）
                    rating = 0
                    rating_el = el.select_one("[class*='star'], .rating")
                    if rating_el:
                        classes = rating_el.get("class", [])
                        for cls in classes:
                            match = re.search(r'allstar(\d+)', cls)
                            if match:
                                rating = int(match.group(1)) // 10
                                break

                    # 提取作者
                    author_el = el.select_one(".name, .author, a[href*='people']")
                    author = author_el.get_text(strip=True) if author_el else ""

                    # 提取日期
                    date_el = el.select_one(".date, .time, time")
                    date = date_el.get_text(strip=True) if date_el else ""

                    # 提取标题
                    title_el = el.select_one(".title, h3")
                    title = title_el.get_text(strip=True) if title_el else ""

                    reviews.append(ReviewRaw(
                        review_id=f"douban-{hash(content[:50]) % 100000}",
                        rating=rating,
                        title=title,
                        content=content[:1000],
                        author=author,
                        version="",
                        date=date,
                        vote_sum=0,
                        vote_count=0,
                        store="douban",
                    ))
        except ImportError:
            reviews = self._parse_with_regex(html)

        return reviews

    def _parse_with_regex(self, html: str) -> list[ReviewRaw]:
        """正则后备方案"""
        reviews = []
        # 匹配豆瓣评论模式
        pattern = r'<span class="short">(.*?)</span>'
        matches = re.findall(pattern, html, re.DOTALL)
        for i, m in enumerate(matches):
            content = re.sub(r'<[^>]+>', '', m).strip()
            if content and len(content) > 5:
                reviews.append(ReviewRaw(
                    review_id=f"douban-regex-{i}",
                    rating=0,
                    title="",
                    content=content[:1000],
                    author="",
                    version="",
                    date="",
                    vote_sum=0,
                    vote_count=0,
                    store="douban",
                ))
        return reviews
