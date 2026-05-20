from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any

import requests


class SteamMarketError(RuntimeError):
    pass


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def build_default_headers(appid: int) -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Origin": "https://steamcommunity.com",
        "Referer": f"https://steamcommunity.com/market/search?appid={appid}",
        "Content-Type": "application/json; charset=utf-8",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "x-valve-request-type": "routeAction",
        "x-valve-action-type": "ZFJAHYDA:SearchMarketListings",
        "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-viewport-height": "1271",
        "sec-ch-viewport-width": "1152",
    }


def build_legacy_headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": "https://steamcommunity.com/market/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-viewport-height": "1271",
        "sec-ch-viewport-width": "1787",
    }


def load_login_cookies(path: Path | str = "cookies.json") -> dict[str, str]:
    cookie_path = Path(path)
    if not cookie_path.exists():
        return {}

    with cookie_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise SteamMarketError(f"Expected cookie object in {cookie_path}")

    cookies: dict[str, str] = {}
    for key, value in data.items():
        if value is not None:
            cookies[str(key)] = str(value)
    return cookies


class SteamMarketClient:
    def __init__(
        self,
        *,
        appid: int,
        session: requests.Session | None = None,
        retries: int = 3,
        timeout: float = 20.0,
        retry_delay: float = 2.0,
        headers: dict[str, str] | None = None,
        legacy: bool = False,
        login: bool = False,
        cookies_path: Path | str = "cookies.json",
    ) -> None:
        self.session = session or requests.Session()
        self.appid = appid
        self.retries = retries
        self.timeout = timeout
        self.retry_delay = retry_delay

        merged_headers = build_legacy_headers() if legacy else build_default_headers(appid)
        if headers:
            merged_headers.update(headers)
        self.session.headers.update(merged_headers)

        if login:
            self.session.cookies.update(load_login_cookies(cookies_path))

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", url, **kwargs)

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                if response.status_code not in RETRYABLE_STATUS_CODES:
                    return response
                last_error = SteamMarketError(
                    f"Steam returned retryable status {response.status_code} for {url}"
                )
            except requests.RequestException as exc:
                last_error = exc

            if attempt < self.retries:
                time.sleep(self.retry_delay * attempt)

        raise SteamMarketError(f"Request failed after {self.retries} attempts: {url}") from last_error

    def get_json(self, url: str, **kwargs: Any) -> dict[str, Any]:
        response = self.get(url, **kwargs)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise SteamMarketError(f"Expected JSON object from {url}")
        return data

    def post_json(self, url: str, payload: Any, **kwargs: Any) -> dict[str, Any]:
        response = self.post(url, json=payload, **kwargs)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise SteamMarketError(f"Expected JSON object from {url}")
        return data
