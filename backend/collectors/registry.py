"""网站检测 + Extractor 注册表"""

from urllib.parse import urlparse


# 已知网站域名 → Extractor 映射
SITE_DOMAINS = {
    "app_store": ["apps.apple.com"],
    "google_play": ["play.google.com"],
    "amazon": ["amazon.com", "amazon.cn", "amazon.co.jp", "amazon.co.uk", "amazon.de"],
    "tripadvisor": ["tripadvisor.com", "tripadvisor.cn"],
    "yelp": ["yelp.com", "yelp.ca"],
    "douban": ["douban.com"],
    "zhihu": ["zhihu.com"],
    "github": ["github.com"],
    "huawei": ["appgallery.huawei.com"],
    "xiaomi": ["app.mi.com"],
    "bilibili": ["bilibili.com", "b23.tv"],
}


def detect_site(url: str) -> str | None:
    """检测 URL 属于哪个网站，返回 site_key 或 None"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # 去掉 www. 前缀
        if domain.startswith("www."):
            domain = domain[4:]

        for site_key, domains in SITE_DOMAINS.items():
            for d in domains:
                if domain == d or domain.endswith("." + d):
                    return site_key
    except Exception:
        pass
    return None


def get_extractor(site_key: str):
    """根据 site_key 获取 Extractor 实例"""
    EXTRACTORS = {
        "app_store": lambda: _import("collectors.app_store", "AppStoreExtractor")(),
        "google_play": lambda: _import("collectors.google_play", "GooglePlayExtractor")(),
        "amazon": lambda: _import("collectors.sites.amazon", "AmazonExtractor")(),
        "tripadvisor": lambda: _import("collectors.sites.tripadvisor", "TripAdvisorExtractor")(),
        "yelp": lambda: _import("collectors.sites.yelp", "YelpExtractor")(),
        "douban": lambda: _import("collectors.sites.douban", "DoubanExtractor")(),
        "zhihu": lambda: _import("collectors.sites.zhihu", "ZhihuExtractor")(),
        "github": lambda: _import("collectors.sites.github", "GitHubExtractor")(),
        "huawei": lambda: _import("collectors.sites.huawei", "HuaweiExtractor")(),
        "xiaomi": lambda: _import("collectors.sites.xiaomi", "XiaomiExtractor")(),
        "bilibili": lambda: _import("collectors.sites.bilibili", "BilibiliExtractor")(),
    }

    factory = EXTRACTORS.get(site_key)
    if factory:
        try:
            return factory()
        except Exception as e:
            print(f"Failed to load extractor for {site_key}: {e}")
    return None


def _import(module_path: str, class_name: str):
    """动态导入 Extractor 类"""
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)
