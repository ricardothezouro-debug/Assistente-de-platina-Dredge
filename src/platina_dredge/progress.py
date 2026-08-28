"""Chaves de progresso do guia.

O guia tem itens marcáveis em sete listas diferentes (passos, missões, peixes,
anomalias, santuários, docas, troféus e pesquisa). Este módulo centraliza o
formato das chaves para que `module.py`, `page.py` e o importador/exportador
falem a mesma língua.

As chaves de passo/missão/peixe/doca/pesquisa/santuário são idênticas às do guia
HTML original, o que permite importar um progresso exportado por ele.
"""
from __future__ import annotations

from . import guide_data


def step_key(num: str) -> str:
    return "step_" + str(num).replace(".", "_")


def quest_key(index: int) -> str:
    return f"quest_{index}"


def fish_key(index: int) -> str:
    return f"fish_{index}"


def anomaly_key(index: int) -> str:
    return f"ab_{index}"


def shrine_key(index: int) -> str:
    return f"shrine_{index}"


def dock_key(index: int) -> str:
    return f"dock_{index}"


def research_key(index: int) -> str:
    return f"research_{index}"


def trophy_key(trophy_id: str) -> str:
    return f"trophy_{trophy_id}"


def trophy_keys() -> list[str]:
    return [trophy_key(t["id"]) for t in guide_data.TROPHIES]


def all_keys() -> list[str]:
    """Todas as chaves marcáveis do guia, na ordem das abas."""
    keys = [step_key(step["num"]) for step in guide_data.ROUTE]
    keys += [quest_key(i) for i in range(len(guide_data.PURSUITS))]
    for i in range(len(guide_data.FISH)):
        keys.append(fish_key(i))
        keys.append(anomaly_key(i))
    keys += [shrine_key(i) for i in range(len(guide_data.SHRINES))]
    keys += [dock_key(i) for i in range(len(guide_data.DOCKS))]
    keys += trophy_keys()
    keys += [research_key(i) for i in range(len(guide_data.RESEARCH))]
    return keys


def normalize_imported(raw) -> set[str]:
    """Aceita o formato deste plugin e o do guia HTML original.

    O HTML salvava um dicionário `{chave: bool}` e numerava os troféus por
    índice (`trophy_0`); aqui os troféus usam o id estável (`trophy_t02`).
    """
    if isinstance(raw, dict):
        raw = [key for key, value in raw.items() if value]
    done: set[str] = set()
    for key in raw:
        key = str(key)
        if key.startswith("trophy_"):
            suffix = key[len("trophy_") :]
            if suffix.isdigit():
                index = int(suffix)
                if 0 <= index < len(guide_data.TROPHIES):
                    done.add(trophy_key(guide_data.TROPHIES[index]["id"]))
                continue
        done.add(key)
    return done
