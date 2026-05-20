from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
import re
import time
from typing import Any

from .client import SteamMarketClient
from .config import GameConfig
from .progress import ProgressPrinter
from .urls import build_search_route_url


@dataclass(frozen=True)
class NameEntry:
    count_id: int
    name: str
    Gitemid: str | None = None
    start: int = 0
    status: str = "ok"


NAME_SUFFIX_PATTERN = re.compile(r" #\d+$")


def build_search_payload(
    appid: int,
    *,
    start: int,
    sort: int = 1,
    direction: int = 1,
    currency: int = 23,
) -> list[dict[str, Any]]:
    return [
        {
            "appid": appid,
            "filters": {},
            "price": {"eCurrency": currency},
            "accessoryFilters": {},
            "sort": sort,
            "direction": direction,
            "start": start,
        }
    ]


<<<<<<< HEAD
def extract_market_hash_name(result: dict[str, Any]) -> str | None:
    for key in ("strHash", "market_hash_name", "hash_name", "name"):
=======
def extract_market_bucket_group_name(result: dict[str, Any]) -> str | None:
    for key in ("market_bucket_group_name"):
>>>>>>> a04f59d (Update: Use market_bucket_group_name instead of market_hash_name)
        value = result.get(key)
        if isinstance(value, str) and value:
            return value
    asset_description = result.get("asset_description")
    if isinstance(asset_description, dict):
<<<<<<< HEAD
        value = asset_description.get("market_hash_name")
=======
        value = asset_description.get("market_bucket_group_name")
>>>>>>> a04f59d (Update: Use market_bucket_group_name instead of market_hash_name)
        if isinstance(value, str) and value:
            return value
    return None


def extract_Gitemid(result: dict[str, Any]) -> str | None:
    asset_description = result.get("asset_description")
    if not isinstance(asset_description, dict):
        return None
    value = asset_description.get("market_bucket_group_id")
    return value if isinstance(value, str) and value else None


def serialize_name_entries(entries: list[NameEntry]) -> list[dict[str, Any]]:
    return [asdict(entry) for entry in entries]


def normalize_name_entries(data: Any) -> list[NameEntry]:
    if not isinstance(data, list):
        return []

    entries: list[NameEntry] = []
    seen_keys: set[str] = set()
    for index, item in enumerate(data):
        if isinstance(item, NameEntry):
            name = item.name
            Gitemid = item.Gitemid
            start = item.start
            status = item.status
            count_id = item.count_id
        elif isinstance(item, str):
            name = item
            Gitemid = None
            start = index
            status = "legacy"
            count_id = index
        elif isinstance(item, dict):
            raw_name = item.get("name") or item.get("market_hash_name") or item.get("strHash")
            if not isinstance(raw_name, str) or not raw_name:
                continue
            name = raw_name
            raw_count_id = item.get("count_id")
            count_id = raw_count_id if isinstance(raw_count_id, int) else index
            raw_start = item.get("start")
            start = raw_start if isinstance(raw_start, int) else count_id
            raw_Gitemid = item.get("Gitemid")
            Gitemid = raw_Gitemid if isinstance(raw_Gitemid, str) and raw_Gitemid else None
            raw_status = item.get("status")
            status = raw_status if isinstance(raw_status, str) and raw_status else "ok"
        else:
            continue

        key = Gitemid or f"missing:{count_id}:{name}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        entries.append(
            NameEntry(
                count_id=count_id,
                name=name,
                Gitemid=Gitemid,
                start=start,
                status=status,
            )
        )

    return canonicalize_name_entries(entries)


def name_strings(data: Any) -> list[str]:
    return [entry.name for entry in normalize_name_entries(data)]


def base_market_name(name: str) -> str:
    return NAME_SUFFIX_PATTERN.sub("", name)


def canonicalize_name_entries(entries: list[NameEntry]) -> list[NameEntry]:
    canonical: list[NameEntry] = []
    seen_Gitemids: set[str] = set()
    name_counts: dict[str, int] = {}

    for entry in sorted(entries, key=lambda item: item.count_id):
        if entry.Gitemid:
            if entry.Gitemid in seen_Gitemids:
                continue
            seen_Gitemids.add(entry.Gitemid)

        base_name = base_market_name(entry.name)
        duplicate_index = name_counts.get(base_name, 0)
        name_counts[base_name] = duplicate_index + 1
        name = base_name if duplicate_index == 0 else f"{base_name} #{duplicate_index}"
        canonical.append(replace(entry, name=name))

    return canonical


def _entries_from_page(data: dict[str, Any], *, start: int) -> tuple[list[NameEntry], int | None]:
    results = data.get("results", [])
    if not isinstance(results, list) or not results:
        return [], data.get("total_count") if isinstance(data.get("total_count"), int) else None

    entries: list[NameEntry] = []
    for offset, result in enumerate(results):
        if not isinstance(result, dict):
            continue
<<<<<<< HEAD
        name = extract_market_hash_name(result)
=======
        name = extract_market_bucket_group_name(result)
>>>>>>> a04f59d (Update: Use market_bucket_group_name instead of market_hash_name)
        if not name:
            continue
        Gitemid = extract_Gitemid(result)
        entries.append(
            NameEntry(
                count_id=start + offset,
                name=name,
                Gitemid=Gitemid,
                start=start,
                status="ok" if Gitemid else "missing_Gitemid",
            )
        )
    total_count = data.get("total_count")
    return entries, total_count if isinstance(total_count, int) else None


def fetch_name_page(
    config: GameConfig,
    *,
    start: int,
    client: SteamMarketClient | None = None,
) -> tuple[list[NameEntry], int | None]:
    client = client or SteamMarketClient(appid=config.appid)
    url = build_search_route_url(config.appid)
    data = client.post_json(url, build_search_payload(config.appid, start=start))
    return _entries_from_page(data, start=start)


def _fetch_name_page_worker(
    appid: int,
    start: int,
    login: bool,
    retry_attempts: int,
    delay: float,
) -> tuple[int, list[NameEntry], int | None, str | None]:
    config = GameConfig(key="worker", appid=appid)
    try:
        entries, total_count = fetch_page_with_retries(
            config,
            start=start,
            client=SteamMarketClient(appid=appid, login=login),
            retry_attempts=retry_attempts,
            delay=delay,
        )
        return start, entries, total_count, None
    except Exception as exc:
        return start, [], None, f"{type(exc).__name__}: {exc}"


def merge_name_entries(existing: list[NameEntry], fetched: list[NameEntry]) -> list[NameEntry]:
    return canonicalize_name_entries([*existing, *fetched])


def resume_start(entries: list[NameEntry]) -> int:
    if not entries:
        return 0
    expected = 0
    existing_ids = {entry.count_id for entry in entries}
    while expected in existing_ids:
        expected += 1
    return expected


def missing_count_ids(entries: list[NameEntry], total_count: int, limit: int | None) -> list[int]:
    effective_total = total_count if limit is None else min(total_count, limit)
    existing_ids = {entry.count_id for entry in entries if 0 <= entry.count_id < effective_total}
    return [count_id for count_id in range(effective_total) if count_id not in existing_ids]


def page_starts_for_missing_ids(missing_ids: list[int], page_size: int) -> list[int]:
    if page_size <= 0:
        raise ValueError("page_size must be positive")
    return sorted({(count_id // page_size) * page_size for count_id in missing_ids})


def fetch_page_with_retries(
    config: GameConfig,
    *,
    start: int,
    client: SteamMarketClient,
    retry_attempts: int,
    delay: float,
) -> tuple[list[NameEntry], int | None]:
    last_error: Exception | None = None
    for attempt in range(retry_attempts + 1):
        try:
            entries, total_count = fetch_name_page(config, start=start, client=client)
            if entries or (total_count is not None and start >= total_count):
                return entries, total_count
        except Exception as exc:
            last_error = exc
        if attempt < retry_attempts and delay > 0:
            time.sleep(delay * (attempt + 1))
    if last_error is not None:
        raise last_error
    return [], None


def fetch_name_entries(
    config: GameConfig,
    *,
    client: SteamMarketClient | None = None,
    count: int = 100,
    delay: float = 1.0,
    limit: int | None = None,
    show_progress: bool = False,
    existing: list[NameEntry] | None = None,
    mode: str = "resume",
    processes: int = 1,
    retry_attempts: int = 2,
    login: bool = False,
) -> list[NameEntry]:
    if mode not in {"resume", "full"}:
        raise ValueError("mode must be 'resume' or 'full'")
    if processes < 1:
        raise ValueError("processes must be at least 1")

    existing_entries = [] if mode == "full" else canonicalize_name_entries(list(existing or []))
    worker_client = client or SteamMarketClient(appid=config.appid, login=login)
    first_entries, first_total_count = fetch_page_with_retries(
        config,
        start=0,
        client=worker_client,
        retry_attempts=retry_attempts,
        delay=delay,
    )
    if first_total_count is None:
        first_total_count = len(first_entries)

    page_size = len(first_entries) or count
    total_count = first_total_count
    target_missing_ids = missing_count_ids(existing_entries, total_count, limit)
    if not target_missing_ids:
        return existing_entries[:limit] if limit is not None else existing_entries

    page_starts = page_starts_for_missing_ids(target_missing_ids, page_size)
    fetched_by_start: dict[int, list[NameEntry]] = {}
    if 0 in page_starts and first_entries:
        fetched_by_start[0] = first_entries

    progress = ProgressPrinter(f"{config.key} names", len(target_missing_ids), enabled=show_progress)
    completed_ids: set[int] = set()

    def record_page(page_entries: list[NameEntry]) -> None:
        for entry in page_entries:
            if entry.count_id in target_missing_ids:
                completed_ids.add(entry.count_id)
        progress.update(len(completed_ids))

    if 0 in fetched_by_start:
        record_page(first_entries)

    starts_to_fetch = [page_start for page_start in page_starts if page_start not in fetched_by_start]
    if processes == 1:
        for page_start in starts_to_fetch:
            page_entries, page_total = fetch_page_with_retries(
                config,
                start=page_start,
                client=worker_client,
                retry_attempts=retry_attempts,
                delay=delay,
            )
            if page_total is not None:
                total_count = min(total_count, page_total)
            fetched_by_start[page_start] = page_entries
            record_page(page_entries)
            if delay > 0:
                time.sleep(delay)
    else:
        if client is not None:
            raise ValueError("A custom client cannot be shared across multiple processes.")
        with ProcessPoolExecutor(max_workers=processes) as executor:
            futures = [
                executor.submit(_fetch_name_page_worker, config.appid, page_start, login, retry_attempts, delay)
                for page_start in starts_to_fetch
            ]
            for future in as_completed(futures):
                page_start, page_entries, page_total, error = future.result()
                if error:
                    progress.update(len(completed_ids), suffix=f"failed_start={page_start}")
                    continue
                if page_total is not None:
                    total_count = min(total_count, page_total)
                fetched_by_start[page_start] = page_entries
                record_page(page_entries)

    progress.finish(suffix=f"total_count={total_count}")
    fetched_entries = [entry for page_start in sorted(fetched_by_start) for entry in fetched_by_start[page_start]]
    entries = merge_name_entries(existing_entries, fetched_entries)
    if limit is not None:
        entries = [entry for entry in entries if entry.count_id < min(limit, total_count)]
    return entries


def fetch_name_list(
    config: GameConfig,
    *,
    client: SteamMarketClient | None = None,
    count: int = 100,
    delay: float = 1.0,
    limit: int | None = None,
    show_progress: bool = False,
    existing: list[NameEntry] | None = None,
    mode: str = "resume",
    processes: int = 1,
    retry_attempts: int = 2,
    login: bool = False,
) -> list[dict[str, Any]]:
    entries = fetch_name_entries(
        config,
        client=client,
        count=count,
        delay=delay,
        limit=limit,
        show_progress=show_progress,
        existing=existing,
        mode=mode,
        processes=processes,
        retry_attempts=retry_attempts,
        login=login,
    )
    return serialize_name_entries(entries)
