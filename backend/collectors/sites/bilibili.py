"""哔哩哔哩视频评论提取器"""

import re
import httpx
import asyncio
from models import ReviewRaw
from collectors.base_extractor import BaseExtractor


class BilibiliExtractor(BaseExtractor):
    """通过 Bilibili API 获取视频评论"""

    name = "bilibili"

    def can_handle(self, url: str) -> bool:
        return "bilibili.com" in url or "b23.tv" in url

    async def extract(self, url: str, max_pages: int = 3) -> list[ReviewRaw]:
        bvid = self._extract_bvid(url)
        if not bvid:
            return []

        video_info = await self._get_video_info(bvid)
        if not video_info:
            return []

        aid = video_info.get("aid", 0)
        title = video_info.get("title", "")
        owner = video_info.get("owner", {}).get("name", "")

        if not aid:
            return []

        # 并发获取视频信息和评论
        reviews = await self._fetch_comments(aid, title, owner, max_pages)
        return reviews

    def _extract_bvid(self, url: str) -> str | None:
        patterns = [
            r"bilibili\.com/video/(BV[\w]+)",
            r"b23\.tv/(BV[\w]+)",
        ]
        for pattern in patterns:
            m = re.search(pattern, url)
            if m:
                return m.group(1)
        return None

    async def _get_video_info(self, bvid: str) -> dict | None:
        api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com",
        }
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                resp = await client.get(api_url, headers=headers)
                data = resp.json()
                if data.get("code") == 0:
                    return data.get("data", {})
        except Exception as e:
            print(f"Failed to get video info: {e}")
        return None

    async def _fetch_comments(self, aid: int, video_title: str, author: str, max_pages: int) -> list[ReviewRaw]:
        """并发分页获取评论"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com",
        }

        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            # 先获取第一页，确定总页数
            first_url = f"https://api.bilibili.com/x/v2/reply/main?type=1&oid={aid}&mode=3&ps=20&pn=1"
            try:
                resp = await client.get(first_url, headers=headers)
                data = resp.json()
                if data.get("code") != 0:
                    return []
                replies = data.get("data", {}).get("replies") or []
                cursor = data.get("data", {}).get("cursor", {})
                is_end = cursor.get("is_end", True)

                all_reviews = self._parse_replies(replies)

                # 如果有多页，并发获取剩余页
                if not is_end and max_pages > 1:
                    tasks = []
                    for page in range(2, min(max_pages + 1, 6)):  # 最多 5 页
                        next_offset = cursor.get("next", 0) if page == 2 else 0
                        tasks.append(self._fetch_page(client, aid, page, headers))
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, list):
                            all_reviews.extend(result)

                return all_reviews
            except Exception as e:
                print(f"Failed to fetch comments: {e}")
                return []

    async def _fetch_page(self, client, aid: int, page: int, headers: dict) -> list[ReviewRaw]:
        """获取单页评论"""
        try:
            url = f"https://api.bilibili.com/x/v2/reply/main?type=1&oid={aid}&mode=3&ps=20&pn={page}"
            resp = await client.get(url, headers=headers)
            data = resp.json()
            if data.get("code") == 0:
                replies = data.get("data", {}).get("replies") or []
                return self._parse_replies(replies)
        except Exception as e:
            print(f"Failed to fetch page {page}: {e}")
        return []

    def _parse_replies(self, replies: list) -> list[ReviewRaw]:
        """解析评论列表（仅提取主评论，不提取子评论以加速）"""
        reviews = []
        for reply in replies:
            message = reply.get("content", {}).get("message", "").strip()
            if not message or len(message) < 2:
                continue
            member = reply.get("member", {})
            reviews.append(ReviewRaw(
                review_id=f"bili-{reply.get('rpid', 0)}",
                rating=0,
                title="",
                content=message,
                author=member.get("uname", ""),
                version="",
                date=self._format_time(reply.get("ctime", 0)),
                vote_sum=reply.get("like", 0),
                vote_count=0,
                store="bilibili",
            ))
        return reviews

    @staticmethod
    def _format_time(timestamp: int) -> str:
        if not timestamp:
            return ""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
