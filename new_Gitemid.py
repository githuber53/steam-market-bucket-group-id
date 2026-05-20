from __future__ import annotations

import sys
import time
from pathlib import Path

from steam_market_params.api import get_item_nameids, get_name_list, update_game
from steam_market_params.cli import main as cli_main
from steam_market_params.config import get_game_config
from steam_market_params.gitemid import fetch_Gitemid_results, normalize_Gitemid_file, serialize_Gitemid_results
from steam_market_params.names import normalize_name_entries
from steam_market_params.progress import format_duration
from steam_market_params.storage import data_path, load_json, save_json


# 直接运行本文件时修改这里即可。
# 支持游戏: "cs2", "dota2", "tf2"
GAME = "cs2"

# 支持操作:
# "names"          获取并保存 name_list 对象列表
# "item_nameids"   获取并保存 item_nameid，缺少 names.json 时会先抓 name_list
# "Gitemid"        获取并保存 Gitemid，缺少 names.json 时会先抓 name_list
# "retry_item_nameids" 只读取 names 中缺失或 item_nameids.json 中为 null 的项并补抓
# "retry_Gitemid"  只读取 names 中缺失或 Gitemid.json 中 status 非 ok/Gitemid 为 null 的项并补抓
# "all"            依次获取 name_list、item_nameid、Gitemid
OPERATION = "Gitemid"

# 测试时建议先用 5 或 10；确认可用后改成 None 抓完整数据。
<<<<<<< HEAD
LIMIT: int | None = 99999
DELAY = 1.0
PROCESSES = 5
=======
LIMIT: int | None = 999999
DELAY = 0
PROCESSES = 32
>>>>>>> a04f59d (Update: Use market_bucket_group_name instead of market_hash_name)
RETRY_ATTEMPTS = 2
RETRY_UNTIL_ALL_SUCCESS = False
DATA_DIR = Path("data")
SCAN_MODE = "resume"  # "resume" / "full"
FORCE_REFRESH_NAMES = False
USE_LOGIN_COOKIES = True

# CS2 默认允许 Gitemid；TF2/DOTA2 默认不允许，设置 True 可强制尝试抓 Gitemid。
ENABLE_GITEMID_FOR_THIS_RUN = False


def save_name_list(
    game: str,
    *,
    limit: int | None = LIMIT,
    delay: float = DELAY,
    processes: int = PROCESSES,
    retry_attempts: int = RETRY_ATTEMPTS,
    retry_until_success: bool = RETRY_UNTIL_ALL_SUCCESS,
    data_dir: Path = DATA_DIR,
    scan_mode: str = SCAN_MODE,
    force: bool = FORCE_REFRESH_NAMES,
    login: bool = USE_LOGIN_COOKIES,
) -> list[dict]:
    del retry_until_success
    started_at = time.perf_counter()
    names_file = data_path(game, "names.json", data_dir)
    existing = load_json(names_file, [])
    names = get_name_list(
        game,
        limit=limit,
        delay=delay,
        processes=processes,
        retry_attempts=retry_attempts,
        show_progress=True,
        existing=existing,
        mode="full" if force else scan_mode,
        login=login,
    )
    save_json(names_file, names)
    elapsed = format_duration(time.perf_counter() - started_at)
    print(f"{game}: saved {len(names)} names -> {names_file}")
    print(f"{game}: elapsed {elapsed}")
    return names


def load_or_save_name_list(
    game: str,
    *,
    limit: int | None = LIMIT,
    delay: float = DELAY,
    processes: int = PROCESSES,
    retry_attempts: int = RETRY_ATTEMPTS,
    retry_until_success: bool = RETRY_UNTIL_ALL_SUCCESS,
    data_dir: Path = DATA_DIR,
    force: bool = FORCE_REFRESH_NAMES,
    scan_mode: str = SCAN_MODE,
    login: bool = USE_LOGIN_COOKIES,
) -> list[dict]:
    del retry_until_success
    names_file = data_path(game, "names.json", data_dir)
    if force or scan_mode == "full" or not names_file.exists():
        return save_name_list(
            game,
            limit=limit,
            delay=delay,
            processes=processes,
            retry_attempts=retry_attempts,
            data_dir=data_dir,
            scan_mode=scan_mode,
            force=force,
            login=login,
        )

    names = load_json(names_file, [])
    if limit is not None:
        names = names[:limit]
    print(f"{game}: loaded {len(names)} names <- {names_file}")
    return names


def save_item_nameids(
    game: str,
    *,
    limit: int | None = LIMIT,
    delay: float = DELAY,
    processes: int = PROCESSES,
    retry_attempts: int = RETRY_ATTEMPTS,
    retry_until_success: bool = RETRY_UNTIL_ALL_SUCCESS,
    data_dir: Path = DATA_DIR,
    force_names: bool = FORCE_REFRESH_NAMES,
    scan_mode: str = SCAN_MODE,
    login: bool = USE_LOGIN_COOKIES,
) -> dict[str, str | None]:
    started_at = time.perf_counter()
    names = load_or_save_name_list(
        game,
        limit=limit,
        delay=delay,
        processes=processes,
        retry_attempts=retry_attempts,
        data_dir=data_dir,
        force=force_names,
        scan_mode=scan_mode,
        login=login,
    )
    output = data_path(game, "item_nameids.json", data_dir)
    current = {} if force_names or scan_mode == "full" else load_json(output, {})
    wanted_names = [entry.name for entry in normalize_name_entries(names)]
    pending_names = [name for name in wanted_names if name not in current or current.get(name) is None]
    if limit is not None:
        pending_names = pending_names[:limit]
    if pending_names:
        current.update(
            get_item_nameids(
                game,
                pending_names,
                delay=delay,
                processes=processes,
                show_progress=True,
                retry_attempts=retry_attempts,
                retry_until_success=retry_until_success,
                login=login,
            )
        )
    save_json(output, current)
    elapsed = format_duration(time.perf_counter() - started_at)
    ok_count = sum(1 for value in current.values() if value is not None)
    print(f"{game}: saved {len(current)} item_nameids ({ok_count} ok) -> {output}")
    print(f"{game}: elapsed {elapsed}")
    return current


def _load_Gitemid_file(game: str, data_dir: Path) -> dict:
    output = data_path(game, "Gitemid.json", data_dir)
    return load_json(output, {})


def save_Gitemid(
    game: str,
    *,
    limit: int | None = LIMIT,
    delay: float = DELAY,
    processes: int = PROCESSES,
    retry_attempts: int = RETRY_ATTEMPTS,
    retry_until_success: bool = RETRY_UNTIL_ALL_SUCCESS,
    data_dir: Path = DATA_DIR,
    force_names: bool = FORCE_REFRESH_NAMES,
    scan_mode: str = SCAN_MODE,
    enable_Gitemid: bool = ENABLE_GITEMID_FOR_THIS_RUN,
    login: bool = USE_LOGIN_COOKIES,
) -> dict[str, str | None]:
    started_at = time.perf_counter()
    config = get_game_config(game)
    if not config.enable_Gitemid and not enable_Gitemid:
        raise RuntimeError(f"{game}: Gitemid is disabled by config. Set ENABLE_GITEMID_FOR_THIS_RUN = True to override.")

    names = load_or_save_name_list(
        game,
        limit=limit,
        delay=delay,
        processes=processes,
        retry_attempts=retry_attempts,
        data_dir=data_dir,
        force=force_names,
        scan_mode=scan_mode,
        login=login,
    )
    output = data_path(game, "Gitemid.json", data_dir)
    current = {} if force_names or scan_mode == "full" else normalize_Gitemid_file(_load_Gitemid_file(game, data_dir))
    wanted = normalize_name_entries(names)
    generated = fetch_Gitemid_results(
        config,
        wanted,
        delay=delay,
        processes=processes,
        show_progress=True,
        retry_attempts=retry_attempts,
        retry_until_success=retry_until_success,
        login=login,
    )
    current.update(generated)
    pending = [
        entry
        for entry in wanted
        if entry.name not in current or current[entry.name].status != "ok" or current[entry.name].Gitemid is None
    ]
    if limit is not None:
        pending = pending[:limit]
    if pending:
        current.update(
            fetch_Gitemid_results(
                config,
                pending,
                delay=delay,
                processes=processes,
                show_progress=True,
                retry_attempts=retry_attempts,
                retry_until_success=retry_until_success,
                login=login,
            )
        )
    save_json(output, serialize_Gitemid_results(current))
    ok_count = sum(1 for result in current.values() if result.status == "ok" and result.Gitemid)
    elapsed = format_duration(time.perf_counter() - started_at)
    print(f"{game}: saved {len(current)} Gitemid results ({ok_count} ok) -> {output}")
    print(f"{game}: elapsed {elapsed}")
    return {name: result.Gitemid for name, result in current.items()}


def retry_failed_item_nameids(
    game: str,
    *,
    limit: int | None = LIMIT,
    delay: float = DELAY,
    processes: int = PROCESSES,
    retry_attempts: int = RETRY_ATTEMPTS,
    retry_until_success: bool = RETRY_UNTIL_ALL_SUCCESS,
    data_dir: Path = DATA_DIR,
    login: bool = USE_LOGIN_COOKIES,
) -> dict[str, str | None]:
    return save_item_nameids(
        game,
        limit=limit,
        delay=delay,
        processes=processes,
        retry_attempts=retry_attempts,
        retry_until_success=retry_until_success,
        data_dir=data_dir,
        login=login,
    )


def retry_failed_Gitemid(
    game: str,
    *,
    limit: int | None = LIMIT,
    delay: float = DELAY,
    processes: int = PROCESSES,
    retry_attempts: int = RETRY_ATTEMPTS,
    retry_until_success: bool = RETRY_UNTIL_ALL_SUCCESS,
    data_dir: Path = DATA_DIR,
    enable_Gitemid: bool = ENABLE_GITEMID_FOR_THIS_RUN,
    login: bool = USE_LOGIN_COOKIES,
) -> dict[str, str | None]:
    return save_Gitemid(
        game,
        limit=limit,
        delay=delay,
        processes=processes,
        retry_attempts=retry_attempts,
        retry_until_success=retry_until_success,
        data_dir=data_dir,
        enable_Gitemid=enable_Gitemid,
        login=login,
    )


def save_all(
    game: str,
    *,
    limit: int | None = LIMIT,
    delay: float = DELAY,
    processes: int = PROCESSES,
    retry_attempts: int = RETRY_ATTEMPTS,
    retry_until_success: bool = RETRY_UNTIL_ALL_SUCCESS,
    data_dir: Path = DATA_DIR,
    force_names: bool = FORCE_REFRESH_NAMES,
    scan_mode: str = SCAN_MODE,
    enable_Gitemid: bool = ENABLE_GITEMID_FOR_THIS_RUN,
    login: bool = USE_LOGIN_COOKIES,
) -> dict[str, object]:
    started_at = time.perf_counter()
    summary = update_game(
        game,
        include_names=True,
        include_item_nameids=True,
        include_Gitemid=enable_Gitemid or None,
        data_dir=data_dir,
        delay=delay,
        limit=limit,
        processes=processes,
        show_progress=True,
        retry_attempts=retry_attempts,
        retry_until_success=retry_until_success,
        force=force_names,
        scan_mode=scan_mode,
        login=login,
    )
    elapsed = format_duration(time.perf_counter() - started_at)
    print(f"{game}: {summary}")
    print(f"{game}: elapsed {elapsed}")
    return summary


def run_configured_operation() -> None:
    operations = {
        "names": save_name_list,
        "item_nameids": save_item_nameids,
        "Gitemid": save_Gitemid,
        "retry_item_nameids": retry_failed_item_nameids,
        "retry_Gitemid": retry_failed_Gitemid,
        "all": save_all,
    }
    try:
        operation = operations[OPERATION]
    except KeyError as exc:
        supported = ", ".join(operations)
        raise ValueError(f"Unsupported OPERATION '{OPERATION}'. Supported: {supported}") from exc

    operation(
        GAME,
        limit=LIMIT,
        delay=DELAY,
        processes=PROCESSES,
        retry_attempts=RETRY_ATTEMPTS,
        retry_until_success=RETRY_UNTIL_ALL_SUCCESS,
        data_dir=DATA_DIR,
        login=USE_LOGIN_COOKIES,
    )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(cli_main())
    run_configured_operation()
