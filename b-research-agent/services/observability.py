from __future__ import annotations

import time
from typing import Any


class RunLogger:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self._started = time.perf_counter()

    def log(self, event: str, **kwargs: Any) -> None:
        self.events.append({"event": event, "ts": time.time(), **kwargs})

    @property
    def duration_ms(self) -> int:
        return int((time.perf_counter() - self._started) * 1000)
