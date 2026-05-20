from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import re
import time
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse

from .client import SteamMarketClient
from .config import GameConfig
from .names import base_market_name, normalize_name_entries
from .progress import ProgressPrinter
from .urls import build_listing_url

GITEMID_PATTERN = re.compile(r"^G[A-Za-z0-9]+$")


@dataclass(frozen=True)
class GitemidResult:
    Gitemid: str | None
    status: str
    source: str = "redirect"
    location: str | None = None


def extract_Gitemid_from_location(location: str | None) -> str | None:
    if not location:
        return None
    last_segment = urlparse(location).path.rstrip("/").split("/")[-1]
    return last_segment if GITEMID_PATTERN.match(last_segment) else None


def fetch_Gitemid_result(
    config: GameConfig,
    name: str,
    *,
    client: SteamMarketClient | None = None,
) -> GitemidResult:
    client = client or SteamMarketClient(appid=config.appid)
    url = build_listing_url(config.appid, base_market_name(name))
    response = client.get(url, allow_redirects=False)
    location = response.headers.get("location")
    Gitemid = extract_Gitemid_from_location(location)
    if response.status_code != 302:
        return GitemidResult(Gitemid=None, status=f"http_{response.status_code}", location=location)
    if Gitemid is None:
        return GitemidResult(Gitemid=None, status="redirect_without_Gitemid", location=location)
    return GitemidResult(Gitemid=Gitemid, status="ok", source="redirect", location=location)


def _fetch_single_Gitemid(appid: int, name: str, delay: float, login: bool) -> tuple[str, GitemidResult]:
    config = GameConfig(key="worker", appid=appid)
    try:
        return name, fetch_Gitemid_result(config, name, client=SteamMarketClient(appid=appid, login=login))
    except Exception as exc:
        return name, GitemidResult(Gitemid=None, status=f"error:{type(exc).__name__}")
    finally:
        if delay > 0:
            time.sleep(delay)


def _result_from_name_entry(entry: Any) -> tuple[str, GitemidResult] | None:
    normalized = normalize_name_entries([entry])
    if not normalized:
        return None
    name_entry = normalized[0]
    if not name_entry.Gitemid:
        return name_entry.name, GitemidResult(Gitemid=None, status="missing_in_names", source="names")
    return name_entry.name, GitemidResult(Gitemid=name_entry.Gitemid, status="ok", source="names")


def fetch_Gitemid_results(
    config: GameConfig,
    names: list[Any],
    *,
    client: SteamMarketClient | None = None,
    delay: float = 1.0,
    limit: int | None = None,
    processes: int = 1,
    show_progress: bool = False,
    retry_attempts: int = 2,
    retry_until_success: bool = False,
    login: bool = False,
) -> dict[str, GitemidResult]:
    selected = names[:limit] if limit is not None else names
    name_entries = normalize_name_entries(selected)
    selected_names = [entry.name for entry in name_entries]
    results: dict[str, GitemidResult] = {}
    pending_names: list[str] = []

    for entry in name_entries:
        if entry.Gitemid:
            results[entry.name] = GitemidResult(Gitemid=entry.Gitemid, status="ok", source="names")
        else:
            results[entry.name] = GitemidResult(Gitemid=None, status="missing_in_names", source="names")
            pending_names.append(entry.name)

    attempt = 0
    while pending_names:
        label = f"{config.key} Gitemid"
        if attempt > 0:
            label = f"{label} retry {attempt}"
        progress = ProgressPrinter(label, len(pending_names), enabled=show_progress)

        if processes > 1:
            if client is not None:
                raise ValueError("A custom client cannot be shared across multiple processes.")
            with ProcessPoolExecutor(max_workers=processes) as executor:
                futures = [
                    executor.submit(_fetch_single_Gitemid, config.appid, name, delay, login)
                    for name in pending_names
                ]
                for future in as_completed(futures):
                    name, result = future.result()
                    results[name] = result
                    ok_count = sum(1 for value in results.values() if value.status == "ok" and value.Gitemid)
                    progress.update(suffix=f"ok={ok_count}")
        else:
            worker_client = client or SteamMarketClient(appid=config.appid, login=login)
            for name in pending_names:
                try:
                    results[name] = fetch_Gitemid_result(config, name, client=worker_client)
                except Exception as exc:
                    results[name] = GitemidResult(Gitemid=None, status=f"error:{type(exc).__name__}")
                ok_count = sum(1 for value in results.values() if value.status == "ok" and value.Gitemid)
                progress.update(suffix=f"ok={ok_count}")
                if delay > 0:
                    time.sleep(delay)

        ok_count = sum(1 for value in results.values() if value.status == "ok" and value.Gitemid)
        progress.finish(suffix=f"ok={ok_count}")

        pending_names = [
            name
            for name in selected_names
            if results[name].status != "ok" or results[name].Gitemid is None
        ]
        attempt += 1
        if not pending_names:
            break
        if not retry_until_success and attempt > retry_attempts:
            break

    return results


def simplify_Gitemid_results(results: dict[str, GitemidResult]) -> dict[str, str | None]:
    return {name: result.Gitemid for name, result in results.items()}


def serialize_Gitemid_results(results: dict[str, GitemidResult]) -> dict[str, dict[str, str | None]]:
    return {name: asdict(result) for name, result in results.items()}


def normalize_Gitemid_file(data: Any) -> dict[str, GitemidResult]:
    if not isinstance(data, dict):
        return {}
    normalized: dict[str, GitemidResult] = {}
    for name, value in data.items():
        if not isinstance(name, str):
            continue
        if isinstance(value, str):
            normalized[name] = GitemidResult(Gitemid=value, status="ok", source="legacy")
        elif isinstance(value, dict):
            raw_Gitemid = value.get("Gitemid")
            Gitemid = raw_Gitemid if isinstance(raw_Gitemid, str) and raw_Gitemid else None
            raw_status = value.get("status")
            status = raw_status if isinstance(raw_status, str) and raw_status else ("ok" if Gitemid else "missing")
            raw_source = value.get("source")
            source = raw_source if isinstance(raw_source, str) and raw_source else "legacy"
            raw_location = value.get("location")
            location = raw_location if isinstance(raw_location, str) and raw_location else None
            normalized[name] = GitemidResult(Gitemid=Gitemid, status=status, source=source, location=location)
        else:
            normalized[name] = GitemidResult(Gitemid=None, status="missing", source="legacy")
    return normalized
