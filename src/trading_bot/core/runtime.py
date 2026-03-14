from __future__ import annotations

import fcntl
import hashlib
import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from trading_bot.core.config import AppConfig


class RunLock:
    def __init__(self, lock_path: Path) -> None:
        self._lock_path = lock_path
        self._handle: Any = None

    def __enter__(self) -> "RunLock":
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self._lock_path.open("w", encoding="utf-8")
        fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        self._handle.write(str(os.getpid()))
        self._handle.flush()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._handle is not None:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
            self._handle.close()
        if self._lock_path.exists():
            self._lock_path.unlink()


def config_fingerprint(config: AppConfig) -> str:
    normalized = _serialize(config)
    payload = json.dumps(normalized, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def _serialize(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _serialize(item) for key, item in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value
