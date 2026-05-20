from dataclasses import dataclass


@dataclass(frozen=True)
class GameConfig:
    key: str
    appid: int
    enable_Gitemid: bool = False


GAMES: dict[str, GameConfig] = {
    "cs2": GameConfig(key="cs2", appid=730, enable_Gitemid=True),
    "tf2": GameConfig(key="tf2", appid=440, enable_Gitemid=False),
    "dota2": GameConfig(key="dota2", appid=570, enable_Gitemid=False),
}


def get_game_config(game: str) -> GameConfig:
    key = game.lower()
    try:
        return GAMES[key]
    except KeyError as exc:
        supported = ", ".join(sorted(GAMES))
        raise ValueError(f"Unsupported game '{game}'. Supported games: {supported}") from exc
