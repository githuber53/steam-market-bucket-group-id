from urllib.parse import quote, urlencode

MARKET_BASE_URL = "https://steamcommunity.com/market"


def build_listing_url(appid: int, market_hash_name: str) -> str:
    return f"{MARKET_BASE_URL}/listings/{appid}/{quote(market_hash_name, safe='')}"


def build_search_render_url(appid: int, *, start: int, count: int) -> str:
    query = urlencode(
        {
            "query": "",
            "start": start,
            "count": count,
            "search_descriptions": 0,
            "sort_column": "popular",
            "sort_dir": "desc",
            "appid": appid,
            "norender": 1,
        }
    )
    return f"{MARKET_BASE_URL}/search/render/?{query}"


def build_search_route_url(appid: int, *, sort: int = 1, direction: int = 1) -> str:
    query = urlencode({"appid": appid, "sort": sort, "dir": direction})
    return f"{MARKET_BASE_URL}/search?{query}"
