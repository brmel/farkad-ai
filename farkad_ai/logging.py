from __future__ import annotations

import json
import logging
import sys
from typing import Any

LOGGED_FIELDS = frozenset({"pillar", "model", "primary_model", "because", "tier", "step"})


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update((key, value) for key, value in vars(record).items() if key in LOGGED_FIELDS)
        return json.dumps(payload)


def configure_logging(level: int = logging.INFO, *, json_format: bool = False) -> None:
    root = logging.getLogger("farkad_ai")
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    if json_format:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s]: %(message)s")
        )
    root.addHandler(handler)
