"""Persistência do progresso (fora da pasta do plugin, sobrevive a updates)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import guide_data


def _data_dir() -> Path:
    base = os.getenv("APPDATA")
    root = Path(base) / "StreamerSidekick" if base else Path.home() / ".streamer_sidekick"
    path = root / "platinas" / guide_data.GUIDE_ID
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_progress() -> set[str]:
    file = _data_dir() / "progress.json"
    try:
        return set(json.loads(file.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return set()


def save_progress(done: set[str]) -> None:
    file = _data_dir() / "progress.json"
    try:
        file.write_text(json.dumps(sorted(done)), encoding="utf-8")
    except OSError:
        pass
