from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_DATA_DIR = Path("data")


def game_data_dir(game: str, data_dir: Path | str = DEFAULT_DATA_DIR) -> Path:
    return Path(data_dir) / game


def data_path(game: str, filename: str, data_dir: Path | str = DEFAULT_DATA_DIR) -> Path:
    return game_data_dir(game, data_dir) / filename


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")
