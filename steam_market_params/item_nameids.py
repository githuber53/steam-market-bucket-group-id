from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import re
import time

from .client import SteamMarketClient
from .config import GameConfig
from .names import base_market_name, name_strings
from .progress import ProgressPrinter
from .urls import build_listing_url

ITEM_NAMEID_PATTERN = re.compile(r"Market_LoadOrderSpread\(\s*(\d+)\s*\)")


def force_legacy_market(client: SteamMarketClient) -> SteamMarketClient:
    """
    强制 Steam Community Market 使用旧版页面。
    旧版页面里才有 Market_LoadOrderSpread(item_nameid)。
    """
    if hasattr(client, "session"):
        client.session.cookies.set(
            "bMarketOptOut",
            "1",
            domain="steamcommunity.com",
            path="/",
        )
        client.session.cookies.set(
            "bMarketOptOut",
            "1",
            domain=".steamcommunity.com",
            path="/",
        )

    return client


def extract_item_nameid(html: str) -> str | None:
    match = ITEM_NAMEID_PATTERN.search(html)
    return match.group(1) if match else None


def is_ssr_market_page(html: str) -> bool:
    return "window.SSR.renderContext" in html or "/steamcommunity/public/ssr/" in html


def is_legacy_market_page(html: str) -> bool:
    return "Market_LoadOrderSpread" in html


def fetch_html_with_legacy_cookie(
    client: SteamMarketClient,
    appid: int,
    name: str,
):
    force_legacy_market(client)

    url = build_listing_url(appid, base_market_name(name))
    response = client.get(url)
    response.raise_for_status()
    return url, response


def _fetch_single_item_nameid(
    appid: int,
    name: str,
    delay: float,
    debug_name: str | None = None,
    login: bool = False,
) -> tuple[str, str | None]:
    client = force_legacy_market(SteamMarketClient(appid=appid, legacy=True, login=login))

    try:
        url, response = fetch_html_with_legacy_cookie(client, appid, name)
        html = response.text

        item_nameid = extract_item_nameid(html)

        if debug_name is not None and name == debug_name:
            print(url)
            print(f"legacy={is_legacy_market_page(html)} ssr={is_ssr_market_page(html)}")
            print(f"item_nameid={item_nameid}")

            if item_nameid is None:
                print(html[:3000])

        return name, item_nameid

    except Exception as e:
        if debug_name is not None and name == debug_name:
            print(f"[ERROR] {name}: {e}")
        return name, None

    finally:
        if delay > 0:
            time.sleep(delay)


def fetch_item_nameids(
    config: GameConfig,
    names: list,
    *,
    client: SteamMarketClient | None = None,
    delay: float = 1.0,
    limit: int | None = None,
    processes: int = 1,
    show_progress: bool = False,
    debug_name: str | None = "Rainy Day Cosmetic Key",
    retry_attempts: int = 2,
    retry_until_success: bool = False,
    login: bool = False,
) -> dict[str, str | None]:
    selected_names = name_strings(names)
    if limit is not None:
        selected_names = selected_names[:limit]
    item_nameids: dict[str, str | None] = {name: None for name in selected_names}
    pending_names = list(selected_names)
    attempt = 0

    while pending_names:
        label = f"{config.key} item_nameids"
        if attempt > 0:
            label = f"{label} retry {attempt}"
        progress = ProgressPrinter(label, len(pending_names), enabled=show_progress)

        if processes > 1:
            if client is not None:
                raise ValueError("A custom client cannot be shared across multiple processes.")

            with ProcessPoolExecutor(max_workers=processes) as executor:
                futures = [
                    executor.submit(
                        _fetch_single_item_nameid,
                        config.appid,
                        name,
                        delay,
                        debug_name,
                        login,
                    )
                    for name in pending_names
                ]

                for future in as_completed(futures):
                    name, item_nameid = future.result()
                    item_nameids[name] = item_nameid
                    ok_count = sum(1 for value in item_nameids.values() if value is not None)
                    progress.update(suffix=f"ok={ok_count}")

            ok_count = sum(1 for value in item_nameids.values() if value is not None)
            progress.finish(suffix=f"ok={ok_count}")
        else:
            worker_client = force_legacy_market(
                client or SteamMarketClient(appid=config.appid, legacy=True, login=login)
            )

            for name in pending_names:
                try:
                    url, response = fetch_html_with_legacy_cookie(worker_client, config.appid, name)
                    html = response.text

                    item_nameid = extract_item_nameid(html)

                    item_nameids[name] = item_nameid

                    if debug_name is not None and name == debug_name:
                        print(url)
                        print(f"legacy={is_legacy_market_page(html)} ssr={is_ssr_market_page(html)}")
                        print(f"item_nameid={item_nameid}")

                        if item_nameid is None:
                            print(html[:3000])

                except Exception as e:
                    item_nameids[name] = None
                    if debug_name is not None and name == debug_name:
                        print(f"[ERROR] {name}: {e}")

                ok_count = sum(1 for value in item_nameids.values() if value is not None)
                progress.update(suffix=f"ok={ok_count}")

                if delay > 0:
                    time.sleep(delay)

            ok_count = sum(1 for value in item_nameids.values() if value is not None)
            progress.finish(suffix=f"ok={ok_count}")

        pending_names = [name for name in selected_names if item_nameids.get(name) is None]
        if not pending_names:
            break

        attempt += 1
        if not retry_until_success and attempt > retry_attempts:
            break

    return item_nameids
