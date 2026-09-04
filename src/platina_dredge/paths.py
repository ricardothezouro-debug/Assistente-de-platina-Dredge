"""Onde este guia guarda progresso e cache — na convenção de cada sistema.

Antes isto era `%APPDATA%` com um fallback para `~/.streamer_sidekick`. No
Windows dava certo; fora dele o progresso ia parar numa pasta oculta na home,
que não é onde o Streamer Sidekick guarda nada. Agora perguntamos ao próprio
Sidekick quando ele está importável (rodando como plugin, que é o caso normal) e
só reproduzimos a regra dele quando não está.
"""
from __future__ import annotations

import os
import ssl
import sys
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import guide_data

APP_NAME = "StreamerSidekick"


def _fallback_root() -> Path:
    """A mesma regra do Sidekick, para quando não dá para perguntar a ele."""
    if sys.platform == "win32":
        base = os.getenv("APPDATA") or os.getenv("LOCALAPPDATA")
        if base:
            return Path(base) / APP_NAME
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        xdg = os.getenv("XDG_CONFIG_HOME")
        return (Path(xdg) if xdg else Path.home() / ".config") / APP_NAME
    return Path.home() / ".streamer_sidekick"


@lru_cache(maxsize=1)
def sidekick_root() -> Path:
    try:
        from streamer_sidekick.core.paths import app_data_dir  # type: ignore

        return app_data_dir()
    except Exception:
        return _fallback_root()


def guide_dir() -> Path:
    """Pasta deste guia. Fica fora do plugin, então sobrevive a atualizações."""
    path = sidekick_root() / "platinas" / guide_data.GUIDE_ID
    path.mkdir(parents=True, exist_ok=True)
    return path


def guide_dir_label() -> str:
    """O caminho como texto, para mostrar ao usuário na tela certa do SO dele."""
    return str(guide_dir())


def _has_roots(context: ssl.SSLContext) -> bool:
    """O contexto carregou alguma CA? Na dúvida, assume que sim e não mexe."""
    try:
        return int(context.cert_store_stats().get("x509_ca", 0)) > 0
    except Exception:
        return True


@lru_cache(maxsize=1)
def _ssl_context() -> ssl.SSLContext:
    """Contexto TLS que não depende do cert store da máquina.

    O Python do python.org no macOS não usa o Keychain: sem isto, baixar as
    imagens do guia morre em CERTIFICATE_VERIFY_FAILED — e como o download falha
    em silêncio, o guia simplesmente aparece sem nenhuma imagem.

    Só completamos com o certifi quando a loja do sistema vem vazia. No Windows
    ela é justamente o que faz um proxy corporativo com raiz própria funcionar,
    então substituí-la quebraria quem depende disso.
    """
    context = ssl.create_default_context()
    if _has_roots(context):
        return context
    try:
        import certifi  # type: ignore

        context.load_verify_locations(cafile=certifi.where())
    except (ImportError, OSError):
        pass
    return context


def urlopen(request: Any, timeout: float) -> Any:
    """``urllib.request.urlopen`` com o contexto TLS acima."""
    return urllib.request.urlopen(request, timeout=timeout, context=_ssl_context())
