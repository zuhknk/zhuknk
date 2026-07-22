"""GitHub Issues / Discussions 提取"""

import re
import httpx
from models import ReviewRaw
from collectors.base_extractor import BaseExtractor


class GitHubExtractor(BaseExtractor):
    """GitHub Issues 作为用户反馈的提取器"""

    name = "github"

    def can_handle(self, url: str) -> bool:
        return "github.com" in url

    async def extract(self, url: str, max_pages: int = 3) -> list[ReviewRaw]:
        match = re.search(r'github\.com/([^/]+)/([^/]+)', url)
        if not match:
            return []

        owner, repo = match.group(1), match.group(2)
        reviews = []

        async with httpx.AsyncClient(timeout=15) as client:
            for page in range(1, max_pages + 1):
                api_url = f"https://api.github.com/repos/{owner}/{repo}/issues?state=all&per_page=30&page={page}"
                headers = {"Accept": "application/vnd.github.v3+json"}
                resp = await client.get(api_url, headers=headers)

                if resp.status_code == 403:
                    # Rate limited
                    break
                if resp.status_code != 200:
                    break

                issues = resp.json()
                if not issues:
                    break

                for issue in issues:
                    # 跳过 PR（pull_request 字段存在）
                    if "pull_request" in issue:
                        continue

                    labels = [l.get("name", "").lower() for l in issue.get("labels", [])]
                    body = issue.get("body", "") or ""

                    # 根据 label 推断情感/评分
                    rating = 0
                    if any("bug" in l or "error" in l or "crash" in l for l in labels):
                        rating = 2
                    elif any("feature" in l or "enhancement" in l for l in labels):
                        rating = 4
                    elif any("question" in l or "help" in l for l in labels):
                        rating = 3
                    elif any("positive" in l or "love" in l or "great" in l for l in labels):
                        rating = 5

                    reviews.append(ReviewRaw(
                        review_id=f"github-{issue['id']}",
                        rating=rating,
                        title=issue.get("title", ""),
                        content=body[:800] if body else "",
                        author=issue.get("user", {}).get("login", ""),
                        version="",
                        date=issue.get("created_at", ""),
                        vote_sum=issue.get("comments", 0),
                        vote_count=0,
                        store="github",
                    ))

        return reviews
