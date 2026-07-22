"""统一评论采集接口"""

from models import ReviewRaw
from collectors.registry import detect_site, get_extractor
from collectors.generic_extractor import GenericExtractor
from collectors.app_store import AppStoreExtractor, collect_reviews_from_file

_generic = GenericExtractor()


async def collect_from_url(url: str, max_pages: int = 5) -> tuple[list[ReviewRaw], str]:
    """
    统一采集入口
    返回: (reviews, site_type)
    """
    site_key = detect_site(url)

    if site_key:
        extractor = get_extractor(site_key)
        if extractor:
            try:
                reviews = await extractor.extract(url, max_pages)
                if reviews:
                    return reviews, site_key
            except Exception as e:
                print(f"Extractor {site_key} failed: {e}, falling back to generic")

    # 未知网站或专用提取器失败 → 通用提取器
    reviews = await _generic.extract(url, max_pages)
    return reviews, "web"
