from __future__ import annotations

import sys
import time


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, rest = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}m {rest:.1f}s"
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)}h {int(minutes)}m {rest:.1f}s"


class ProgressPrinter:
    def __init__(self, label: str, total: int | None = None, *, enabled: bool = True) -> None:
        self.label = label
        self.total = total
        self.enabled = enabled
        self.started_at = time.perf_counter()
        self.current = 0
        self._last_line_length = 0

    def update(self, current: int | None = None, *, suffix: str = "") -> None:
        if not self.enabled:
            return
        if current is None:
            self.current += 1
        else:
            self.current = current

        elapsed = format_duration(time.perf_counter() - self.started_at)
        if self.total:
            percent = self.current / self.total * 100
            text = f"{self.label}: {self.current}/{self.total} ({percent:5.1f}%) elapsed {elapsed}"
        else:
            text = f"{self.label}: {self.current} elapsed {elapsed}"
        if suffix:
            text = f"{text} {suffix}"

        padding = " " * max(0, self._last_line_length - len(text))
        print(f"\r{text}{padding}", end="", file=sys.stderr, flush=True)
        self._last_line_length = len(text)

    def finish(self, *, suffix: str = "") -> float:
        elapsed_seconds = time.perf_counter() - self.started_at
        if self.enabled:
            elapsed = format_duration(elapsed_seconds)
            if self.total:
                text = f"{self.label}: {self.current}/{self.total} (100.0%) elapsed {elapsed}"
            else:
                text = f"{self.label}: {self.current} elapsed {elapsed}"
            if suffix:
                text = f"{text} {suffix}"
            padding = " " * max(0, self._last_line_length - len(text))
            print(f"\r{text}{padding}", file=sys.stderr, flush=True)
        return elapsed_seconds
