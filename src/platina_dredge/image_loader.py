"""Carrega imagens por URL com cache em disco."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Callable
from urllib import parse, request

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QPixmap

from . import guide_data


def _cache_dir() -> Path:
    base = os.getenv("APPDATA")
    root = Path(base) / "StreamerSidekick" if base else Path.home() / ".streamer_sidekick"
    path = root / "platinas" / guide_data.GUIDE_ID / "img_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_path(url: str) -> Path:
    ext = ".img"
    clean = url.lower().split("?")[0]
    for candidate in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if clean.endswith(candidate):
            ext = candidate
            break
    return _cache_dir() / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ext)


_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _headers(url: str) -> dict[str, str]:
    """Cabeçalhos de navegador.

    Vários hosts de guia (o GameFAQs, por exemplo) devolvem 403 para um
    `User-Agent` genérico sem `Referer`/`Sec-Fetch-*`. O `Referer` é a raiz do
    próprio host da imagem, então nenhuma outra origem é revelada.
    """
    parts = parse.urlsplit(url)
    return {
        "User-Agent": _USER_AGENT,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Referer": f"{parts.scheme}://{parts.netloc}/",
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-origin",
    }


class _DownloadWorker(QThread):
    done = Signal(str)

    def __init__(self, url: str, dest: Path) -> None:
        super().__init__()
        self._url = url
        self._dest = dest

    def run(self) -> None:
        try:
            req = request.Request(self._url, headers=_headers(self._url))
            with request.urlopen(req, timeout=20) as response:
                data = response.read()
            self._dest.write_bytes(data)
            self.done.emit(str(self._dest))
        except Exception:
            self.done.emit("")


class ImageLoader(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._workers: list[_DownloadWorker] = []

    def load(self, url: str, on_ready: Callable[[QPixmap], None]) -> QPixmap | None:
        cache = _cache_path(url)
        if cache.exists():
            pixmap = QPixmap(str(cache))
            if not pixmap.isNull():
                return pixmap
        worker = _DownloadWorker(url, cache)

        def _finish(path: str) -> None:
            if worker in self._workers:
                self._workers.remove(worker)
            if path:
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    on_ready(pixmap)

        worker.done.connect(_finish)
        self._workers.append(worker)
        worker.start()
        return None

    def shutdown(self) -> None:
        """Encerra os downloads pendentes antes que o objeto seja destruído.

        Único acréscimo ao arquivo genérico do template: sem isto, fechar o app
        com um download em andamento destrói um QThread ainda rodando e o Qt
        aborta o processo ("QThread: Destroyed while thread is still running").
        """
        for worker in list(self._workers):
            try:
                worker.done.disconnect()
            except (RuntimeError, TypeError):
                pass
            if worker.isRunning() and not worker.wait(1500):
                worker.terminate()
                worker.wait(1000)
        self._workers.clear()
