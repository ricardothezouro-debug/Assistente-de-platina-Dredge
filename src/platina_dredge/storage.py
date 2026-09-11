"""Persistência do progresso (fora da pasta do plugin, sobrevive a updates)."""
from __future__ import annotations

import json
from pathlib import Path

from .paths import guide_dir


def _data_dir() -> Path:
    return guide_dir()


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


# Preferências de interface (ex.: cabeçalho recolhido). Ficam num arquivo
# separado do progresso para que "Resetar marcações" não mexa nelas.
def load_ui() -> dict:
    file = _data_dir() / "ui.json"
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_ui(prefs: dict) -> None:
    file = _data_dir() / "ui.json"
    try:
        file.write_text(json.dumps(prefs), encoding="utf-8")
    except OSError:
        pass
