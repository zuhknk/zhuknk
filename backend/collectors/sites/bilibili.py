"""哔哩哔哩视频评论提取器"""

import re
import httpx
from models import ReviewRaw
from collectors.base_extractor import BaseExtractor


class BilibiliExtractor(BaseExtractor):
    """通过 Bilibili API 获取视频评论"""

    name = "bilibili"

    def can_handle(self, url: str) -> bool:
        return "bilibili.com" in url or "b23.tv" in url

    async def extract(self, url: str, max_pages: int = 3) -> list[ReviewRaw]:
        # 1. 解析视频 ID
        bvid = self._extract_bvid(url)
        if not bvid:
            print(f"Cannot extract BV id from URL: {url}")
            return []

        # 2. 获取视频信息（aid 等）
        video_info = await self._get_video_info(bvid)
        if not video_info:
            return []

        aid = video_info.get("aid", 0)
        title = video_info.get("title", "")
        owner = video_info.get("owner", {}).get("name", "")

        if not aid:
            return []

        # 3. 获取评论
        reviews = await self._fetch_comments(aid, title, owner, max_pages)
        return reviews

    def _extract_bvid(self, url: str) -> str | None:
        """从 URL 中提取 BV 号"""
        # 匹配 bilibili.com/video/BVxxxxxxxxxx
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
        """获取视频基本信息"""
        api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com",
        }
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                resp = await client.get(api_url, headers=headers)
                data = resp.json()
                if data.get("code") == 0:
                    return data.get("data", {})
        except Exception as e:
            print(f"Failed to get video info: {e}")
        return None

    async def _fetch_comments(self, aid: int, video_title: str, author: str, max_pages: int) -> list[ReviewRaw]:
        """分页获取评论"""
        all_reviews = []
        page = 1
        next_offset = 0

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com",
        }

        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            while page <= max_pages:
                api_url = (
                    f"https://api.bilibili.com/x/v2/reply/main"
                    f"?type=1&oid={aid}&mode=3&ps=20&pn={page}"
                )
                if next_offset:
                    api_url += f"&next={next_offset}"

                try:
                    resp = await client.get(api_url, headers=headers)
                    data = resp.json()
                    if data.get("code") != 0:
                        break

                    replies = data.get("data", {}).get("replies") or []
                    cursor = data.get("data", {}).get("cursor", {})
                    is_end = cursor.get("is_end", True)
                    next_offset = cursor.get("next", 0)

                    for reply in replies:
                        message = reply.get("content", {}).get("message", "").strip()
                        if not message or len(message) < 2:
                            continue

                        member = reply.get("member", {})
                        all_reviews.append(ReviewRaw(
                            review_id=f"bili-{reply.get('rpid', 0)}",
                            rating=0,  # Bilibili 没有评分
                            title="",
                            content=message,
                            author=member.get("uname", ""),
                            version="",
                            date=self._format_time(reply.get("ctime", 0)),
                            vote_sum=reply.get("like", 0),
                            vote_count=0,
                            store="bilibili",
                        ))

                        # 也提取热门子评论
                        sub_replies = reply.get("replies") or []
                        for sub in sub_replies[:3]:
                            sub_msg = sub.get("content", {}).get("message", "").strip()
                            if sub_msg and len(sub_msg) >= 2:
                                sub_member = sub.get("member", {})
                                all_reviews.append(ReviewRaw(
                                    review_id=f"bili-{sub.get('rpid', 0)}",
                                    rating=0,
                                    title="",
                                    content=sub_msg,
                                    author=sub_member.get("uname", ""),
                                    version="",
                                    date=self._format_time(sub.get("ctime", 0)),
                                    vote_sum=sub.get("like", 0),
                                    vote_count=0,
                                    store="bilibili",
                                ))

                    page += 1
                    if is_end or not replies:
                        break

                except Exception as e:
                    print(f"Failed to fetch comments page {page}: {e}")
                    break

        return all_reviews

    @staticmethod
    def _format_time(timestamp: int) -> str:
        """Unix 时间戳转可读日期"""
        if not timestamp:
            return ""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
