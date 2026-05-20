from __future__ import annotations

import argparse
import time
from pathlib import Path

from .api import get_Gitemid_values, get_item_nameids, get_name_list, update_game
from .config import GAMES, get_game_config
from .gitemid import fetch_Gitemid_results, normalize_Gitemid_file, serialize_Gitemid_results
from .names import normalize_name_entries
from .progress import format_duration
from .storage import DEFAULT_DATA_DIR, data_path, load_json, save_json


def add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("game", nargs="?", choices=sorted(GAMES))
    parser.add_argument("--all-games", action="store_true", help="Run the command for all supported games.")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between Steam requests in seconds.")
    parser.add_argument("--limit", type=int, default=None, help="Process at most this many names.")
    parser.add_argument("--processes", type=int, default=1, help="Use multiple processes for paged/item requests.")
    parser.add_argument("--retry-attempts", type=int, default=2, help="Retry failed/null requests this many times.")
    parser.add_argument("--retry-until-success", action="store_true", help="Keep retrying failed/null items until all succeed.")
    parser.add_argument("--force", action="store_true", help="Refresh prerequisites instead of reusing JSON files.")
    parser.add_argument("--scan-mode", choices=("resume", "full"), default="resume", help="Resume names scan or rescan from start.")
    parser.add_argument("--login", action="store_true", help="Read cookies.json and send Steam login cookies.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Directory for JSON output.")
    parser.add_argument("--enable-Gitemid", dest="enable_Gitemid", action="store_true", help="Enable Gitemid fetching even if disabled by game config.")


def selected_games(args: argparse.Namespace) -> list[str]:
    if args.all_games:
        return sorted(GAMES)
    if args.game:
        return [args.game]
    raise SystemExit("Provide a game or --all-games.")


def load_or_fetch_names(args: argparse.Namespace, game: str) -> list[dict]:
    names_file = data_path(game, "names.json", args.data_dir)
    existing = load_json(names_file, [])
    if args.force or args.scan_mode == "full" or not names_file.exists():
        names = get_name_list(
            game,
            delay=args.delay,
            limit=args.limit,
            show_progress=True,
            processes=args.processes,
            retry_attempts=args.retry_attempts,
            mode="full" if args.force else args.scan_mode,
            existing=existing,
            login=args.login,
        )
        save_json(names_file, names)
        return names
    names = existing
    if args.limit is not None:
        return names[: args.limit]
    return names


def command_update_names(args: argparse.Namespace) -> None:
    started_at = time.perf_counter()
    for game in selected_games(args):
        path = data_path(game, "names.json", args.data_dir)
        existing = load_json(path, [])
        names = get_name_list(
            game,
            delay=args.delay,
            limit=args.limit,
            show_progress=True,
            processes=args.processes,
            retry_attempts=args.retry_attempts,
            mode="full" if args.force else args.scan_mode,
            existing=existing,
            login=args.login,
        )
        save_json(path, names)
        print(f"{game}: saved {len(names)} names")
    print(f"total elapsed: {format_duration(time.perf_counter() - started_at)}")


def command_update_item_nameids(args: argparse.Namespace) -> None:
    started_at = time.perf_counter()
    for game in selected_games(args):
        names = load_or_fetch_names(args, game)
        output = data_path(game, "item_nameids.json", args.data_dir)
        current = {} if args.force else load_json(output, {})
        wanted_names = [entry.name for entry in normalize_name_entries(names)]
        pending_names = [
            name
            for name in wanted_names
            if args.force or name not in current or current.get(name) is None
        ]
        if args.limit is not None:
            pending_names = pending_names[: args.limit]
        if pending_names:
            item_nameids = get_item_nameids(
                game,
                pending_names,
                delay=args.delay,
                processes=args.processes,
                show_progress=True,
                retry_attempts=args.retry_attempts,
                retry_until_success=args.retry_until_success,
                login=args.login,
            )
            current.update(item_nameids)
        save_json(output, current)
        ok_count = sum(1 for value in current.values() if value is not None)
        print(f"{game}: saved {len(current)} item_nameids ({ok_count} ok)")
    print(f"total elapsed: {format_duration(time.perf_counter() - started_at)}")


def _load_Gitemid_file(game: str, data_dir: Path) -> dict:
    path = data_path(game, "Gitemid.json", data_dir)
    return load_json(path, {})


def command_update_Gitemid(args: argparse.Namespace) -> None:
    started_at = time.perf_counter()
    for game in selected_games(args):
        config = get_game_config(game)
        if not config.enable_Gitemid and not args.enable_Gitemid:
            print(f"{game}: Gitemid disabled by config, use --enable-Gitemid to override")
            continue
        names = load_or_fetch_names(args, game)
        output = data_path(game, "Gitemid.json", args.data_dir)
        current_results = {} if args.force else normalize_Gitemid_file(_load_Gitemid_file(game, args.data_dir))
        wanted_entries = normalize_name_entries(names)
        generated = fetch_Gitemid_results(
            config,
            wanted_entries,
            delay=args.delay,
            processes=args.processes,
            show_progress=True,
            retry_attempts=args.retry_attempts,
            retry_until_success=args.retry_until_success,
            login=args.login,
        )
        current_results.update(generated)
        pending = [
            entry
            for entry in wanted_entries
            if args.force
            or entry.name not in current_results
            or current_results[entry.name].status != "ok"
            or current_results[entry.name].Gitemid is None
        ]
        if args.limit is not None:
            pending = pending[: args.limit]
        if pending:
            retried = fetch_Gitemid_results(
                config,
                pending,
                delay=args.delay,
                processes=args.processes,
                show_progress=True,
                retry_attempts=args.retry_attempts,
                retry_until_success=args.retry_until_success,
                login=args.login,
            )
            current_results.update(retried)
        save_json(output, serialize_Gitemid_results(current_results))
        ok_count = sum(1 for result in current_results.values() if result.status == "ok" and result.Gitemid)
        print(f"{game}: saved {len(current_results)} Gitemid results ({ok_count} ok)")
    print(f"total elapsed: {format_duration(time.perf_counter() - started_at)}")


def command_retry_item_nameids(args: argparse.Namespace) -> None:
    started_at = time.perf_counter()
    for game in selected_games(args):
        path = data_path(game, "item_nameids.json", args.data_dir)
        current = load_json(path, {})
        names = load_json(data_path(game, "names.json", args.data_dir), [])
        wanted_names = [entry.name for entry in normalize_name_entries(names)]
        failed_names = [
            name
            for name in wanted_names
            if name not in current or current.get(name) is None
        ]
        if args.limit is not None:
            failed_names = failed_names[: args.limit]
        if not failed_names:
            print(f"{game}: no failed item_nameids to retry")
            continue
        retried = get_item_nameids(
            game,
            failed_names,
            delay=args.delay,
            processes=args.processes,
            show_progress=True,
            retry_attempts=args.retry_attempts,
            retry_until_success=args.retry_until_success,
            login=args.login,
        )
        current.update(retried)
        save_json(path, current)
        ok_count = sum(1 for value in current.values() if value is not None)
        print(f"{game}: retried {len(failed_names)} item_nameids ({ok_count}/{len(current)} ok)")
    print(f"total elapsed: {format_duration(time.perf_counter() - started_at)}")


def command_retry_Gitemid(args: argparse.Namespace) -> None:
    started_at = time.perf_counter()
    for game in selected_games(args):
        config = get_game_config(game)
        if not config.enable_Gitemid and not args.enable_Gitemid:
            print(f"{game}: Gitemid disabled by config, use --enable-Gitemid to override")
            continue
        current = normalize_Gitemid_file(_load_Gitemid_file(game, args.data_dir))
        names = load_json(data_path(game, "names.json", args.data_dir), [])
        entries_by_name = {entry.name: entry for entry in normalize_name_entries(names)}
        failed = [
            entries_by_name[name]
            for name, value in current.items()
            if name in entries_by_name and (value.status != "ok" or value.Gitemid is None)
        ]
        missing = [
            entry
            for name, entry in entries_by_name.items()
            if name not in current
        ]
        failed.extend(missing)
        if args.limit is not None:
            failed = failed[: args.limit]
        if not failed:
            print(f"{game}: no failed Gitemid values to retry")
            continue
        retried = fetch_Gitemid_results(
            config,
            failed,
            delay=args.delay,
            processes=args.processes,
            show_progress=True,
            retry_attempts=args.retry_attempts,
            retry_until_success=args.retry_until_success,
            login=args.login,
        )
        current.update(retried)
        save_json(data_path(game, "Gitemid.json", args.data_dir), serialize_Gitemid_results(current))
        ok_count = sum(1 for value in current.values() if value.status == "ok" and value.Gitemid is not None)
        print(f"{game}: retried {len(failed)} Gitemid values ({ok_count}/{len(current)} ok)")
    print(f"total elapsed: {format_duration(time.perf_counter() - started_at)}")


def command_update_all(args: argparse.Namespace) -> None:
    started_at = time.perf_counter()
    for game in selected_games(args):
        summary = update_game(
            game,
            include_Gitemid=args.enable_Gitemid or None,
            data_dir=args.data_dir,
            delay=args.delay,
            limit=args.limit,
            processes=args.processes,
            show_progress=True,
            retry_attempts=args.retry_attempts,
            retry_until_success=args.retry_until_success,
            force=args.force,
            scan_mode=args.scan_mode,
            login=args.login,
        )
        print(f"{game}: {summary}")
    print(f"total elapsed: {format_duration(time.perf_counter() - started_at)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m steam_market_params")
    subparsers = parser.add_subparsers(dest="command", required=True)

    commands = {
        "update-names": command_update_names,
        "update-item-nameids": command_update_item_nameids,
        "update-Gitemid": command_update_Gitemid,
        "retry-item-nameids": command_retry_item_nameids,
        "retry-Gitemid": command_retry_Gitemid,
        "update-all": command_update_all,
    }
    for name, handler in commands.items():
        subparser = subparsers.add_parser(name)
        add_common_options(subparser)
        subparser.set_defaults(handler=handler)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.handler(args)
    return 0
