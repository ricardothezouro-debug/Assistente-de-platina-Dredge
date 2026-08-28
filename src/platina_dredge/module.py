"""Adaptador de plugin do Streamer Sidekick (categoria: platina)."""
from dataclasses import dataclass

from . import guide_data

MODULE_ID = guide_data.GUIDE_ID


@dataclass(frozen=True)
class ModuleInfo:
    module_id: str
    title: str
    subtitle: str
    status: str
    accent: str


def module_info():
    from .progress import trophy_keys
    from .storage import load_progress

    done_keys = load_progress()
    trophies = trophy_keys()
    done = sum(1 for key in trophies if key in done_keys)
    data = dict(
        module_id=guide_data.GUIDE_ID,
        title=guide_data.GAME_NAME,
        subtitle=guide_data.GAME_SUBTITLE,
        status=f"{done}/{len(trophies)} troféus",
        accent=guide_data.ACCENT,
    )
    try:
        from streamer_sidekick.core.modules import ModuleInfo as SidekickModuleInfo

        return SidekickModuleInfo(**data)
    except Exception:
        return ModuleInfo(**data)


def help_text() -> str:
    return (
        "Guia de platina completo de DREDGE em PT-BR, dividido em 10 abas.\n\n"
        "Como usar:\n"
        "• Comece pela aba “Passo a passo”: são 90 passos em ordem cronológica, "
        "agrupados por fase. Faça o passo, marque a caixa e siga.\n"
        "• A busca do topo procura em passos, itens, peixes e missões ao mesmo "
        "tempo — digite o nome de um item (“Caixa de Música”) ou uma coordenada "
        "(“E12”) para descobrir onde ele está.\n"
        "• “Onde está...?” lista as 23 relíquias e itens de missão com coordenada, "
        "caminho e pré-requisito.\n"
        "• “67 Peixes” tem duas caixas por linha: a primeira é a espécie, a segunda "
        "é a variante anômala daquela espécie.\n"
        "• “40 Troféus” alimenta o contador que aparece no card do guia.\n"
        "• As abas Santuários, Docas, Missões, Pesquisa, Mapas e Fontes completam o "
        "restante do checklist.\n\n"
        "O progresso é salvo automaticamente em "
        "%APPDATA%/StreamerSidekick/platinas/dredge/ e sobrevive a atualizações. "
        "Use Exportar/Importar para levar o progresso para outro PC.\n\n"
        "Atenção às DLCs: libere Mestre Pescador e Atraindo Anomalias antes de "
        "instalar Pale Reach ou Iron Rig, senão as espécies das expansões entram no "
        "requisito desses dois troféus."
    )


def build_page(config=None):
    from .page import GuidePage

    return GuidePage()
