from __future__ import annotations

from pathlib import Path

from .client import SteamMarketClient
from .config import get_game_config
from .gitemid import (
    fetch_Gitemid_results,
    normalize_Gitemid_file,
    serialize_Gitemid_results,
    simplify_Gitemid_results,
)
from .item_nameids import fetch_item_nameids
from .names import fetch_name_list, normalize_name_entries
from .storage import DEFAULT_DATA_DIR, data_path, load_json, save_json


def get_name_list(
    game: str,
    *,
    client: SteamMarketClient | None = None,
    delay: float = 1.0,
    limit: int | None = None,
    show_progress: bool = False,
    processes: int = 1,
    retry_attempts: int = 2,
    mode: str = "resume",
    existing: list | None = None,
    login: bool = False,
) -> list[dict]:
    return fetch_name_list(
        get_game_config(game),
        client=client,
        delay=delay,
        limit=limit,
        show_progress=show_progress,
        processes=processes,
        retry_attempts=retry_attempts,
        mode=mode,
        existing=normalize_name_entries(existing or []),
        login=login,
    )


def get_item_nameids(
    game: str,
    names: list,
    *,
    client: SteamMarketClient | None = None,
    delay: float = 1.0,
    limit: int | None = None,
    processes: int = 1,
    show_progress: bool = False,
    retry_attempts: int = 2,
    retry_until_success: bool = False,
    login: bool = False,
) -> dict[str, str | None]:
    return fetch_item_nameids(
        get_game_config(game),
        names,
        client=client,
        delay=delay,
        limit=limit,
        processes=processes,
        show_progress=show_progress,
        retry_attempts=retry_attempts,
        retry_until_success=retry_until_success,
        login=login,
    )


def get_Gitemid_values(
    game: str,
    names: list,
    *,
    client: SteamMarketClient | None = None,
    delay: float = 1.0,
    limit: int | None = None,
    processes: int = 1,
    show_progress: bool = False,
    retry_attempts: int = 2,
    retry_until_success: bool = False,
    login: bool = False,
) -> dict[str, str | None]:
    config = get_game_config(game)
    results = fetch_Gitemid_results(
        config,
        names,
        client=client,
        delay=delay,
        limit=limit,
        processes=processes,
        show_progress=show_progress,
        retry_attempts=retry_attempts,
        retry_until_success=retry_until_success,
        login=login,
    )
    return simplify_Gitemid_results(results)


def update_game(
    game: str,
    *,
    include_names: bool = True,
    include_item_nameids: bool = True,
    include_Gitemid: bool | None = None,
    client: SteamMarketClient | None = None,
    data_dir: Path | str = DEFAULT_DATA_DIR,
    delay: float = 1.0,
    limit: int | None = None,
    processes: int = 1,
    show_progress: bool = False,
    retry_attempts: int = 2,
    retry_until_success: bool = False,
    force: bool = False,
    scan_mode: str = "resume",
    login: bool = False,
) -> dict[str, object]:
    config = get_game_config(game)
    user_provided_client = client is not None
    client = client or SteamMarketClient(appid=config.appid, login=login)
    worker_client = client if user_provided_client or processes <= 1 else None
    Gitemid_enabled = config.enable_Gitemid if include_Gitemid is None else include_Gitemid
    summary: dict[str, object] = {"game": config.key}

    names_file = data_path(config.key, "names.json", data_dir)
    existing_names = load_json(names_file, [])
    if include_names or force or not names_file.exists():
        names = get_name_list(
            config.key,
            client=client,
            delay=delay,
            limit=limit,
            show_progress=show_progress,
            processes=processes,
            retry_attempts=retry_attempts,
            mode="full" if force else scan_mode,
            existing=existing_names,
            login=login,
        )
        save_json(names_file, names)
    else:
        names = existing_names
    summary["names"] = len(names)

    if include_item_nameids:
        item_nameids = get_item_nameids(
            config.key,
            names,
            client=worker_client,
            delay=delay,
            limit=limit,
            processes=processes,
            show_progress=show_progress,
            retry_attempts=retry_attempts,
            retry_until_success=retry_until_success,
            login=login,
        )
        save_json(data_path(config.key, "item_nameids.json", data_dir), item_nameids)
        summary["item_nameids"] = sum(1 for value in item_nameids.values() if value is not None)

    if Gitemid_enabled:
        Gitemid_results = fetch_Gitemid_results(
            config,
            names,
            client=worker_client,
            delay=delay,
            limit=limit,
            processes=processes,
            show_progress=show_progress,
            retry_attempts=retry_attempts,
            retry_until_success=retry_until_success,
            login=login,
        )
        existing_Gitemid = normalize_Gitemid_file(load_json(data_path(config.key, "Gitemid.json", data_dir), {}))
        existing_Gitemid.update(Gitemid_results)
        Gitemid_results = existing_Gitemid
        save_json(data_path(config.key, "Gitemid.json", data_dir), serialize_Gitemid_results(Gitemid_results))
        summary["Gitemid"] = sum(1 for result in Gitemid_results.values() if result.status == "ok" and result.Gitemid)
    else:
        summary["Gitemid"] = "disabled"

    return summary
