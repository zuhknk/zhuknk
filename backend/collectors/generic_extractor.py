"""通用 LLM 驱动的评论提取器 — 处理未知网站"""

import re
import json
import httpx
from models import ReviewRaw
from collectors.base_extractor import BaseExtractor


class GenericExtractor(BaseExtractor):
    """通用提取器：先用 HTML 解析提取文本，再用 LLM 结构化"""

    name = "generic"

    # 常见评论相关的 CSS 选择器
    REVIEW_SELECTORS = [
        "[class*='review']", "[class*='comment']",
        "[class*='feedback']", "[class*='rating']",
        "[itemtype*='Review']", "[itemtype*='review']",
        "article[class*='review']",
        "[class*='user-review']",
        "[class*='review-item']",
        "[class*='review-content']",
    ]

    def can_handle(self, url: str) -> bool:
        return True  # 作为兜底，处理所有 URL

    async def extract(self, url: str, max_pages: int = 1) -> list[ReviewRaw]:
        html = await self._fetch_page(url)
        if not html:
            return []

        candidates = self._extract_candidates(html)
        if not candidates:
            return []

        reviews = await self._llm_structure(candidates, url)
        return reviews

    async def _fetch_page(self, url: str) -> str:
        """获取网页 HTML"""
        # 快速校验：只处理 http/https
        if not url.startswith(("http://", "https://")):
            return ""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=5) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                return resp.text
        except Exception:
            return ""

    def _extract_candidates(self, html: str) -> list[dict]:
        """从 HTML 中提取可能的评论区块"""
        # 尝试用 BeautifulSoup（可选依赖）
        try:
            from bs4 import BeautifulSoup
            return self._extract_with_bs4(html)
        except ImportError:
            return self._extract_with_regex(html)

    def _extract_with_bs4(self, html: str) -> list[dict]:
        """使用 BeautifulSoup 提取评论候选"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        candidates = []

        # 策略 1：CSS 选择器匹配
        seen_texts = set()
        for selector in self.REVIEW_SELECTORS:
            try:
                elements = soup.select(selector)
                for el in elements:
                    text = el.get_text(separator=" ", strip=True)
                    if len(text) > 15 and text not in seen_texts:
                        seen_texts.add(text)
                        candidates.append({
                            "text": text[:600],
                            "source": "css",
                        })
            except Exception:
                continue

        # 策略 2：JSON-LD 结构化数据
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                reviews = self._extract_jsonld_reviews(data)
                candidates.extend(reviews)
            except (json.JSONDecodeError, TypeError):
                pass

        # 策略 3：aria-label 包含 review/comment 的元素
        for el in soup.find_all(attrs={"aria-label": re.compile(r"review|comment|feedback", re.I)}):
            text = el.get_text(strip=True)
            if len(text) > 15:
                candidates.append({"text": text[:600], "source": "aria"})

        return candidates[:25]

    def _extract_jsonld_reviews(self, data) -> list[dict]:
        """从 JSON-LD 中提取评论"""
        candidates = []
        if isinstance(data, dict):
            if data.get("@type") == "Review":
                candidates.append({
                    "text": json.dumps(data, ensure_ascii=False)[:600],
                    "source": "jsonld",
                    "structured": True,
                })
            elif "review" in data:
                reviews = data["review"] if isinstance(data["review"], list) else [data["review"]]
                for r in reviews:
                    if isinstance(r, dict):
                        candidates.append({
                            "text": json.dumps(r, ensure_ascii=False)[:600],
                            "source": "jsonld",
                            "structured": True,
                        })
        elif isinstance(data, list):
            for item in data:
                candidates.extend(self._extract_jsonld_reviews(item))
        return candidates

    def _extract_with_regex(self, html: str) -> list[dict]:
        """使用正则表达式提取评论（无 BeautifulSoup 时的后备方案）"""
        candidates = []
        # 匹配常见评论模式
        patterns = [
            r'<div[^>]*class="[^"]*review[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*comment[^"]*"[^>]*>(.*?)</div>',
            r'<p[^>]*class="[^"]*review[^"]*"[^>]*>(.*?)</p>',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for m in matches:
                text = re.sub(r'<[^>]+>', ' ', m).strip()
                if len(text) > 15:
                    candidates.append({"text": text[:600], "source": "regex"})
        return candidates[:25]

    async def _llm_structure(self, candidates: list[dict], url: str) -> list[ReviewRaw]:
        """用 LLM 将候选文本结构化为评论"""
        from llm_client import analyze_batch

        texts = []
        for i, c in enumerate(candidates):
            prefix = f"[JSON-LD] " if c.get("structured") else ""
            texts.append(f"--- 候选 {i+1} ({c.get('source', 'unknown')}) {prefix}---\n{c['text']}")

        prompt = f"""分析以下从网页提取的文本区块，识别其中的用户评论/反馈。

网页 URL: {url}

文本区块:
{chr(10).join(texts)}

请识别每个文本块中是否包含用户评论。对于确认是评论的内容，提取：
- rating: 评分 1-5（如果无法判断则为 0）
- title: 评论标题（如果没有则为空字符串）
- content: 评论正文内容
- author: 作者名/用户名（如果没有则为空字符串）
- date: 发布日期（如果没有则为空字符串）

只输出确实包含评论内容的条目，忽略广告、导航等无关内容。

输出 JSON 格式:
{{
  "reviews": [
    {{"rating": 5, "title": "", "content": "...", "author": "", "date": ""}}
  ]
}}"""

        system = "你是网页评论提取专家。从给定的 HTML 文本区块中识别用户评论并结构化。只输出 JSON，不要其他内容。"

        try:
            result = await analyze_batch(system, prompt, max_tokens=4096)
            reviews = []
            for i, r in enumerate(result.get("reviews", [])):
                content = r.get("content", "").strip()
                if not content or len(content) < 5:
                    continue
                reviews.append(ReviewRaw(
                    review_id=f"web-{hash(url) % 100000}-{i}",
                    rating=int(r.get("rating", 0)),
                    title=r.get("title", ""),
                    content=content,
                    author=r.get("author", ""),
                    version="",
                    date=r.get("date", ""),
                    vote_sum=0,
                    vote_count=0,
                    store="web",
                ))
            return reviews
        except Exception as e:
            print(f"Generic LLM extraction failed: {e}")
            return []
