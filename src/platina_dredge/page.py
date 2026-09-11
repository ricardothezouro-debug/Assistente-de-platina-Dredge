"""Página do guia: as 10 abas do guia original, com progresso, busca e imagens."""
from __future__ import annotations

import html
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

from . import guide_data
from . import progress as keys
from .image_loader import ImageLoader
from .storage import load_progress, load_ui, save_progress, save_ui
from .topbar import InfoCorner, TopBar

_IMG_MAX_W = 620
_IMG_MAX_H = 420
_IMG_TIMEOUT_MS = 26000
_SEARCH_LIMIT = 18

_TIER_COLORS = {
    "bronze": "#C77B3B",
    "prata": "#B8C0CC",
    "ouro": "#E7C64A",
    "platina": "#7FE7FF",
}

_PROGRESS_QSS = (
    "QProgressBar{background:#0B111A;border:1px solid #273140;border-radius:9px;"
    "min-height:18px;text-align:center;color:#F3F6FF;font-weight:600}"
    "QProgressBar::chunk{border-radius:8px;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
    "stop:0 #37F2FF,stop:0.5 #B9FF43,stop:1 #FF4FD8)}"
)

_NAV_QSS = (
    "QPushButton#NavButton{background:#0D121B;border:1px solid #273140;border-radius:8px;"
    "padding:7px 10px;color:#A8B0BC;text-align:left}"
    "QPushButton#NavButton:hover{border-color:#3C4A5C;color:#F3F6FF}"
    "QPushButton#NavButton:checked{background:#101922;border-color:%s;color:#F3F6FF;font-weight:600}"
    % guide_data.ACCENT
)

_PHASE_QSS = (
    "QPushButton#PhaseHead{background:#101922;border:1px solid #273140;border-radius:9px;"
    "padding:10px 12px;color:#F3F6FF;text-align:left;font-weight:600}"
    "QPushButton#PhaseHead:hover{border-color:%s}" % guide_data.ACCENT
)


def _norm(text) -> str:
    """Minúsculas sem acento, para busca tolerante."""
    stripped = unicodedata.normalize("NFD", str(text or ""))
    return "".join(c for c in stripped if not unicodedata.combining(c)).lower()


def _esc(text) -> str:
    """Escapa o texto do guia antes de entrar em um QLabel com rich text."""
    return html.escape(str(text or ""))


def _label(text: str, object_name: str = "", wrap: bool = True) -> QLabel:
    label = QLabel(str(text or ""))
    if object_name:
        label.setObjectName(object_name)
    label.setWordWrap(wrap)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
    return label


def _link(text: str, url: str) -> QLabel:
    label = QLabel(
        f'<a href="{_esc(url)}" style="color:{guide_data.ACCENT}">{_esc(text)}</a>'
    )
    label.setOpenExternalLinks(True)
    label.setWordWrap(True)
    return label


def _card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("NeonPanel")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(6)
    return frame, layout


def _notice(text: str, tone: str = "info") -> QFrame:
    frame = QFrame()
    frame.setObjectName("NeonPanel")
    color = "#B95146" if tone == "red" else guide_data.ACCENT
    frame.setStyleSheet(
        "QFrame{background:#0D121B;border:1px solid #273140;"
        "border-left:3px solid %s;border-radius:10px}" % color
    )
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 11, 14, 11)
    layout.addWidget(_label(text, "Muted"))
    return frame


def _pill(text: str) -> QLabel:
    label = QLabel(str(text or ""))
    label.setObjectName("StatusPill")
    label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    return label


def _detail(layout: QVBoxLayout, title: str, value: str) -> None:
    """Linha “rótulo → valor” usada nos passos e nos cards."""
    if not value:
        return
    row = QLabel(f"<b>{_esc(title)}:</b> {_esc(value)}")
    row.setObjectName("Muted")
    row.setWordWrap(True)
    row.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
    layout.addWidget(row)


def _scroll_page(build_content) -> QWidget:
    """Wrapper de aba: um QScrollArea vertical com o conteúdo dentro."""
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 10, 0)
    layout.setSpacing(12)
    build_content(layout)
    layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setObjectName("PageScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(container)
    return scroll


class GuidePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._done = load_progress()
        self._image_loader = ImageLoader(self)
        self._boxes: dict[str, list[QCheckBox]] = {}
        self._built: set[int] = set()
        self._phase_pills: list[tuple[QLabel, list[str]]] = []
        self._loc_rows: list[tuple[QWidget, str, str]] = []
        self._fish_rows: list[tuple[QWidget, str, str, int]] = []
        self._trophy_rows: list[tuple[QWidget, str, str]] = []
        self._section_index = {s["key"]: i for i, s in enumerate(guide_data.SECTIONS)}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 22, 0)
        outer.setSpacing(12)
        self._build_header(outer)
        self._build_progress(outer)
        self._build_nav(outer)
        self.top = TopBar(
            self, title=self._title_box, header=self._header_box,
            progress=self._progress_box, nav=self._nav_box, bar=self.progress,
            pills=self._progress_pills, load_ui=load_ui, save_ui=save_ui)
        outer.addWidget(self.top.widget)

        self.stack = QStackedWidget()
        self._holders: list[QVBoxLayout] = []
        for _section in guide_data.SECTIONS:
            placeholder = QWidget()
            holder = QVBoxLayout(placeholder)
            holder.setContentsMargins(0, 0, 0, 0)
            holder.addWidget(_label("Carregando…", "Muted"))
            holder.addStretch(1)
            self._holders.append(holder)
            self.stack.addWidget(placeholder)
        self.stack.currentChanged.connect(self._ensure_built)
        outer.addWidget(self.stack, 1)

        outer.addWidget(InfoCorner(guide_data.FOOTER))

        self._update_progress()
        # Constrói a primeira aba só depois que o event loop girar, para que
        # build_page() retorne instantaneamente (regra 2 do padrão de plugins).
        QTimer.singleShot(0, lambda: self._ensure_built(0))

        # Downloads em andamento precisam ser encerrados antes que o Qt destrua
        # a página (fechar o app ou atualizar o plugin), senão o processo aborta.
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._image_loader.shutdown)

    def closeEvent(self, event):  # noqa: N802 (assinatura do Qt)
        self._image_loader.shutdown()
        super().closeEvent(event)

    def hideEvent(self, event):  # noqa: N802 (assinatura do Qt)
        # O hub troca a página do QStackedWidget ao atualizar o plugin.
        if self.window() is not None and self.window().isHidden():
            self._image_loader.shutdown()
        super().hideEvent(event)

    # ------------------------------------------------------------------ topo
    def _build_header(self, outer: QVBoxLayout) -> None:
        """O topo tem três níveis (ver topbar.py). Aqui só se montam as peças:
        o título, e o bloco que some primeiro — abertura, números, busca e
        botões de progresso."""
        self._title_box = QWidget()
        title_row = QHBoxLayout(self._title_box)
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.addWidget(_label(guide_data.GAME_NAME, "PageTitle", wrap=False), 1)

        self._header_box = QWidget()
        box = QVBoxLayout(self._header_box)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(12)
        box.addWidget(_label(guide_data.INTRO, "Muted"))
        stats = QHBoxLayout()
        stats.setSpacing(8)
        for stat in guide_data.HERO_STATS:
            stats.addWidget(_pill(f"{stat['value']}  {stat['label']}"))
        stats.addStretch(1)
        box.addLayout(stats)
        self._build_search(box)
        self._build_toolbar(box)

    def _build_search(self, outer: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setSpacing(8)
        self.global_search = QLineEdit()
        self.global_search.setPlaceholderText(
            "Onde está...? Ex.: Caixa de Música, Fivela, Peixe-remo, Congro, Tabuleta, E12..."
        )
        self.global_search.textChanged.connect(self._global_search)
        clear = QPushButton("Limpar")
        clear.clicked.connect(lambda: self.global_search.setText(""))
        row.addWidget(self.global_search, 1)
        row.addWidget(clear, 0)
        outer.addLayout(row)

        self.results_box = QWidget()
        self.results_layout = QVBoxLayout(self.results_box)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(6)
        self.results_box.hide()
        outer.addWidget(self.results_box)

    def _build_progress(self, outer: QVBoxLayout) -> None:
        self._progress_box = QWidget()
        row = QHBoxLayout(self._progress_box)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.progress = QProgressBar()
        self.progress.setStyleSheet(_PROGRESS_QSS)
        self.progress.setRange(0, max(1, len(keys.all_keys())))
        self.progress_label = _pill("")
        self.trophy_label = _pill("")
        row.addWidget(self.progress, 1)
        row.addWidget(self.progress_label, 0)
        row.addWidget(self.trophy_label, 0)
        self._progress_pills = [self.progress_label, self.trophy_label]

    def _build_toolbar(self, outer: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setSpacing(8)
        export = QPushButton("Exportar progresso")
        export.clicked.connect(self._export)
        importer = QPushButton("Importar progresso")
        importer.clicked.connect(self._import)
        reset = QPushButton("Resetar marcações")
        reset.clicked.connect(self._reset)
        for button in (export, importer, reset):
            row.addWidget(button)
        row.addStretch(1)
        outer.addLayout(row)

    def _build_nav(self, outer: QVBoxLayout) -> None:
        holder = QWidget()
        holder.setStyleSheet(_NAV_QSS)
        grid = QGridLayout(holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)
        self._nav_buttons: list[QPushButton] = []
        for i, section in enumerate(guide_data.SECTIONS):
            button = QPushButton(f"{section['num']}  {section['nav']}")
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setChecked(i == 0)
            button.clicked.connect(lambda _=False, index=i: self.show_section(index))
            grid.addWidget(button, i // 5, i % 5)
            self._nav_buttons.append(button)
        for column in range(5):
            grid.setColumnStretch(column, 1)
        self._nav_box = holder

    def show_section(self, index: int) -> None:
        for i, button in enumerate(self._nav_buttons):
            button.setChecked(i == index)
        self.stack.setCurrentIndex(index)

    # -------------------------------------------------------------- progresso
    def _checkbox(self, key: str, text: str = "") -> QCheckBox:
        box = QCheckBox(text)
        box.setChecked(key in self._done)
        box.toggled.connect(lambda checked, k=key: self._on_toggle(k, checked))
        self._boxes.setdefault(key, []).append(box)
        return box

    def _on_toggle(self, key: str, checked: bool) -> None:
        if checked:
            self._done.add(key)
        else:
            self._done.discard(key)
        for box in self._boxes.get(key, []):
            if box.isChecked() != checked:
                box.blockSignals(True)
                box.setChecked(checked)
                box.blockSignals(False)
        save_progress(self._done)
        self._update_progress()

    def _update_progress(self) -> None:
        all_keys = keys.all_keys()
        done = sum(1 for key in all_keys if key in self._done)
        percent = round(done / len(all_keys) * 100) if all_keys else 0
        self.progress.setValue(done)
        self.progress_label.setText(f"{done} / {len(all_keys)}  •  {percent}%")
        trophies = keys.trophy_keys()
        got = sum(1 for key in trophies if key in self._done)
        self.trophy_label.setText(f"{got}/{len(trophies)} troféus")
        for pill, phase_keys in self._phase_pills:
            phase_done = sum(1 for key in phase_keys if key in self._done)
            pill.setText(f"{phase_done}/{len(phase_keys)}")
        if hasattr(self, "top"):
            self.top.sync()

    def _refresh_boxes(self) -> None:
        for key, boxes in self._boxes.items():
            checked = key in self._done
            for box in boxes:
                box.blockSignals(True)
                box.setChecked(checked)
                box.blockSignals(False)
        self._update_progress()
        if self._trophy_rows:
            self._filter_trophies()
        if self._fish_rows:
            self._filter_fish()

    # ------------------------------------------------------ exportar/importar
    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar progresso", "dredge-platina-ptbr-progresso.json",
            "JSON (*.json)",
        )
        if not path:
            return
        payload = {
            "guide": guide_data.GUIDE_ID,
            "version": 2,
            "exportedAt": datetime.now(timezone.utc).isoformat(),
            "state": {key: True for key in sorted(self._done)},
        }
        try:
            Path(path).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError as error:
            QMessageBox.warning(self, "Exportar", f"Não foi possível salvar: {error}")

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar progresso", "", "JSON (*.json)"
        )
        if not path:
            return
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            QMessageBox.warning(self, "Importar", "Arquivo JSON inválido.")
            return
        state = raw.get("state", raw) if isinstance(raw, dict) else raw
        self._done = keys.normalize_imported(state)
        save_progress(self._done)
        self._refresh_boxes()

    def _reset(self) -> None:
        answer = QMessageBox.question(
            self, "Resetar", "Apagar todas as marcações deste guia?"
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._done = set()
        save_progress(self._done)
        self._refresh_boxes()

    # ------------------------------------------------------------- busca geral
    def _global_search(self) -> None:
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        query = _norm(self.global_search.text()).strip()
        if len(query) < 2:
            self.results_box.hide()
            return

        hits: list[tuple[str, str, str, str, str]] = []
        for item in guide_data.LOCATIONS:
            if query in _norm(" ".join(item.values())):
                hits.append(("ITEM", item["name"], item["coord"], item["path"], "locator"))
        for step in guide_data.ROUTE:
            if query in _norm(" ".join(step.values())):
                hits.append(
                    (f"PASSO {step['num']}", step["title"], step["place"], step["exact"], "route")
                )
        for fish in guide_data.FISH:
            if query in _norm(" ".join(fish.values())):
                detail = (
                    f"{fish['region']} • {fish['water']} • {fish['time']} • "
                    f"{fish['method']}. {fish['quest']}"
                )
                hits.append(("PEIXE", fish["name"], fish["spot"], detail, "fish"))
        for quest in guide_data.PURSUITS:
            if query in _norm(" ".join(quest.values())):
                hits.append(("MISSÃO", quest["name"], quest["start"], quest["route"], "quests"))

        if not hits:
            self.results_layout.addWidget(
                _notice("Nada encontrado. Tente o nome do item, missão, peixe ou coordenada.")
            )
            self.results_box.show()
            return

        for kind, name, where, text, page in hits[:_SEARCH_LIMIT]:
            frame, layout = _card()
            head = QHBoxLayout()
            head.setSpacing(8)
            head.addWidget(_label(kind, "Kicker", wrap=False))
            head.addWidget(_label(f"<b>{_esc(name)}</b>", "SectionTitle"), 1)
            if where:
                head.addWidget(_pill(where))
            layout.addLayout(head)
            layout.addWidget(_label(text, "Muted"))
            go = QPushButton(f"Ir para “{guide_data.SECTIONS[self._section_index[page]]['nav']}”")
            go.clicked.connect(
                lambda _=False, target=page: self.show_section(self._section_index[target])
            )
            row = QHBoxLayout()
            row.addWidget(go)
            row.addStretch(1)
            layout.addLayout(row)
            self.results_layout.addWidget(frame)
        if len(hits) > _SEARCH_LIMIT:
            self.results_layout.addWidget(
                _label(f"…e mais {len(hits) - _SEARCH_LIMIT} resultado(s). Refine a busca.", "Muted")
            )
        self.results_box.show()

    # ---------------------------------------------------------------- imagens
    def _add_image(self, layout: QVBoxLayout, url: str) -> None:
        if not url:
            return
        holder = QLabel("Carregando imagem…")
        holder.setObjectName("Muted")
        layout.addWidget(holder)
        state = {"loaded": False}

        def show(pixmap: QPixmap) -> None:
            state["loaded"] = True
            holder.setText("")
            holder.setPixmap(
                pixmap.scaled(
                    _IMG_MAX_W, _IMG_MAX_H,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        cached = self._image_loader.load(url, show)
        if cached is not None:
            show(cached)
            return

        def timeout() -> None:
            if not state["loaded"]:
                holder.setText(
                    f'Imagem indisponível offline — <a href="{url}" '
                    f'style="color:{guide_data.ACCENT}">abrir no navegador</a>'
                )
                holder.setOpenExternalLinks(True)

        QTimer.singleShot(_IMG_TIMEOUT_MS, timeout)

    # ------------------------------------------------------- construção lazy
    def _ensure_built(self, index: int) -> None:
        if index in self._built or index < 0:
            return
        self._built.add(index)
        holder = self._holders[index]
        # Troca o "Carregando…" pelo conteúdo real. Esvaziar o layout (em vez de
        # trocar a página do QStackedWidget) evita depender de deleteLater().
        while holder.count():
            item = holder.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        key = guide_data.SECTIONS[index]["key"]
        builder = getattr(self, f"_build_{key}")
        holder.addWidget(
            _scroll_page(lambda layout: self._with_header(layout, index, builder))
        )
        self._update_progress()

    def _with_header(self, layout: QVBoxLayout, index: int, builder) -> None:
        section = guide_data.SECTIONS[index]
        layout.addWidget(_label(section["eyebrow"], "Kicker", wrap=False))
        layout.addWidget(_label(section["title"], "CardTitle"))
        layout.addWidget(_label(section["lead"], "Muted"))
        for notice in section["notices"]:
            layout.addWidget(_notice(notice["text"], notice["tone"]))
        builder(layout)

    # ------------------------------------------------------- 01 Passo a passo
    def _build_route(self, layout: QVBoxLayout) -> None:
        phases: dict[str, list[dict]] = {}
        for step in guide_data.ROUTE:
            phases.setdefault(step["phase"], []).append(step)

        for phase, steps in phases.items():
            phase_keys = [keys.step_key(step["num"]) for step in steps]
            head_holder = QWidget()
            head_holder.setStyleSheet(_PHASE_QSS)
            head_row = QHBoxLayout(head_holder)
            head_row.setContentsMargins(0, 0, 0, 0)
            head_row.setSpacing(8)
            toggle = QPushButton(f"{phase}   ({len(steps)} passos)")
            toggle.setObjectName("PhaseHead")
            pill = _pill("")
            head_row.addWidget(toggle, 1)
            head_row.addWidget(pill, 0)
            layout.addWidget(head_holder)
            self._phase_pills.append((pill, phase_keys))

            body = QWidget()
            body_layout = QVBoxLayout(body)
            body_layout.setContentsMargins(0, 0, 0, 0)
            body_layout.setSpacing(8)
            for step in steps:
                body_layout.addWidget(self._route_step(step))
            layout.addWidget(body)
            toggle.clicked.connect(lambda _=False, target=body: target.setVisible(not target.isVisible()))

    def _route_step(self, step: dict) -> QFrame:
        frame, layout = _card()
        head = QHBoxLayout()
        head.setSpacing(8)
        head.addWidget(self._checkbox(keys.step_key(step["num"])), 0, Qt.AlignmentFlag.AlignTop)
        head.addWidget(_label(step["num"], "Kicker", wrap=False), 0, Qt.AlignmentFlag.AlignTop)
        head.addWidget(_label(step["title"], "SectionTitle"), 1)
        head.addWidget(_pill(step["place"]), 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(head)
        _detail(layout, "Quando", step["when"])
        _detail(layout, "Faça exatamente", step["exact"])
        _detail(layout, "Por que agora", step["why"])
        self._add_image(layout, step.get("image", ""))
        return frame

    # ------------------------------------------------------ 02 Onde está...?
    def _build_locator(self, layout: QVBoxLayout) -> None:
        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.loc_search = QLineEdit()
        self.loc_search.setPlaceholderText("Pesquisar item, coordenada ou missão...")
        self.loc_search.textChanged.connect(self._filter_locations)
        self.loc_region = QComboBox()
        self.loc_region.addItem("Todas as regiões", "")
        for region in dict.fromkeys(item["region"] for item in guide_data.LOCATIONS):
            self.loc_region.addItem(region, region)
        self.loc_region.currentIndexChanged.connect(self._filter_locations)
        filters.addWidget(self.loc_search, 1)
        filters.addWidget(self.loc_region, 0)
        layout.addLayout(filters)

        self.loc_empty = _label("Nenhum item corresponde ao filtro.", "Muted")
        self.loc_empty.hide()
        layout.addWidget(self.loc_empty)

        for item in guide_data.LOCATIONS:
            frame, card = _card()
            card.addWidget(_label(item["type"], "Kicker", wrap=False))
            head = QHBoxLayout()
            head.setSpacing(8)
            head.addWidget(_label(item["name"], "SectionTitle"), 1)
            head.addWidget(_pill(item["coord"]), 0)
            card.addLayout(head)
            _detail(card, "Região", item["region"])
            _detail(card, "Como chegar", item["path"])
            _detail(card, "Pré-requisito", item["need"])
            layout.addWidget(frame)
            self._loc_rows.append((frame, _norm(" ".join(item.values())), item["region"]))

    def _filter_locations(self) -> None:
        query = _norm(self.loc_search.text()).strip()
        region = self.loc_region.currentData() or ""
        visible = 0
        for frame, haystack, row_region in self._loc_rows:
            show = (not region or row_region == region) and query in haystack
            frame.setVisible(show)
            visible += int(show)
        self.loc_empty.setVisible(visible == 0)

    # --------------------------------------------------- 03 Missões / Figuras
    def _build_quests(self, layout: QVBoxLayout) -> None:
        total = len(guide_data.PURSUITS)
        for i, quest in enumerate(guide_data.PURSUITS):
            frame, card = _card()
            head = QHBoxLayout()
            head.setSpacing(8)
            head.addWidget(self._checkbox(keys.quest_key(i)), 0, Qt.AlignmentFlag.AlignTop)
            head.addWidget(_label(f"MISSÃO {i + 1}/{total}", "Kicker", wrap=False), 0)
            head.addWidget(_label(quest["name"], "SectionTitle"), 1)
            card.addLayout(head)
            _detail(card, "Onde começa", quest["start"])
            _detail(card, "O que fazer", quest["todo"])
            _detail(card, "Local / rota", quest["route"])
            layout.addWidget(frame)

    # ------------------------------------------------------------ 04 Peixes
    def _build_fish(self, layout: QVBoxLayout) -> None:
        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.fish_search = QLineEdit()
        self.fish_search.setPlaceholderText("Buscar peixe, coordenada ou missão...")
        self.fish_search.textChanged.connect(self._filter_fish)
        self.fish_region = QComboBox()
        self.fish_region.addItem("Todas as regiões", "")
        for region in dict.fromkeys(fish["region"] for fish in guide_data.FISH):
            self.fish_region.addItem(region, region)
        self.fish_region.currentIndexChanged.connect(self._filter_fish)
        self.fish_pending = QCheckBox("só pendentes")
        self.fish_pending.toggled.connect(self._filter_fish)
        filters.addWidget(self.fish_search, 1)
        filters.addWidget(self.fish_region, 0)
        filters.addWidget(self.fish_pending, 0)
        layout.addLayout(filters)

        self.fish_empty = _label("Nenhuma espécie corresponde ao filtro.", "Muted")
        self.fish_empty.hide()
        layout.addWidget(self.fish_empty)

        for i, fish in enumerate(guide_data.FISH):
            frame, card = _card()
            head = QHBoxLayout()
            head.setSpacing(8)
            head.addWidget(self._checkbox(keys.fish_key(i)), 0, Qt.AlignmentFlag.AlignTop)
            head.addWidget(
                self._checkbox(keys.anomaly_key(i), "anom."), 0, Qt.AlignmentFlag.AlignTop
            )
            names = QVBoxLayout()
            names.setSpacing(0)
            names.addWidget(_label(fish["name"], "SectionTitle"))
            names.addWidget(_label(fish["name_en"], "Muted"))
            head.addLayout(names, 1)
            head.addWidget(_pill(fish["region"]), 0, Qt.AlignmentFlag.AlignTop)
            card.addLayout(head)
            _detail(
                card, "Onde e quando",
                f"{fish['water']} • {fish['time']} • {fish['method']}",
            )
            _detail(card, "Ponto recomendado", fish["spot"])
            _detail(card, "Uso", fish["quest"])
            layout.addWidget(frame)
            self._fish_rows.append((frame, _norm(" ".join(fish.values())), fish["region"], i))

    def _filter_fish(self) -> None:
        query = _norm(self.fish_search.text()).strip()
        region = self.fish_region.currentData() or ""
        pending = self.fish_pending.isChecked()
        visible = 0
        for frame, haystack, row_region, index in self._fish_rows:
            complete = (
                keys.fish_key(index) in self._done and keys.anomaly_key(index) in self._done
            )
            show = (
                (not region or row_region == region)
                and query in haystack
                and (not pending or not complete)
            )
            frame.setVisible(show)
            visible += int(show)
        self.fish_empty.setVisible(visible == 0)

    # -------------------------------------------------------- 05 Santuários
    def _build_shrines(self, layout: QVBoxLayout) -> None:
        total = len(guide_data.SHRINES)
        for i, shrine in enumerate(guide_data.SHRINES):
            frame, card = _card()
            head = QHBoxLayout()
            head.setSpacing(8)
            head.addWidget(self._checkbox(keys.shrine_key(i)), 0, Qt.AlignmentFlag.AlignTop)
            head.addWidget(_label(f"SANTUÁRIO {i + 1}/{total}", "Kicker", wrap=False), 0)
            head.addWidget(_label(shrine["name"], "SectionTitle"), 1)
            head.addWidget(_pill(shrine["coord"]), 0, Qt.AlignmentFlag.AlignTop)
            card.addLayout(head)
            _detail(card, "Oferta", shrine["offer"])
            _detail(card, "Como obter", shrine["how"])
            _detail(card, "Recompensa", shrine["reward"])
            self._add_image(card, shrine.get("image", ""))
            layout.addWidget(frame)

    # ------------------------------------------------------------- 06 Docas
    def _build_docks(self, layout: QVBoxLayout) -> None:
        for i, dock in enumerate(guide_data.DOCKS):
            frame, card = _card()
            head = QHBoxLayout()
            head.setSpacing(8)
            head.addWidget(self._checkbox(keys.dock_key(i)), 0, Qt.AlignmentFlag.AlignTop)
            named = dock["kind"] == "Nomeado"
            head.addWidget(
                _label("CAIS NOMEADO" if named else "COMPATIBILIDADE", "Kicker", wrap=False), 0
            )
            head.addWidget(_label(dock["name"], "SectionTitle"), 1)
            head.addWidget(_pill(dock["region"]), 0, Qt.AlignmentFlag.AlignTop)
            card.addLayout(head)
            layout.addWidget(frame)

    # ---------------------------------------------------------- 07 Troféus
    def _build_trophies(self, layout: QVBoxLayout) -> None:
        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.trophy_search = QLineEdit()
        self.trophy_search.setPlaceholderText("Buscar troféu ou requisito...")
        self.trophy_search.textChanged.connect(self._filter_trophies)
        self.trophy_pending = QCheckBox("só pendentes")
        self.trophy_pending.toggled.connect(self._filter_trophies)
        filters.addWidget(self.trophy_search, 1)
        filters.addWidget(self.trophy_pending, 0)
        layout.addLayout(filters)

        self.trophy_empty = _label("Nenhum troféu corresponde ao filtro.", "Muted")
        self.trophy_empty.hide()
        layout.addWidget(self.trophy_empty)

        for trophy in guide_data.TROPHIES:
            frame, card = _card()
            head = QHBoxLayout()
            head.setSpacing(8)
            head.addWidget(
                self._checkbox(keys.trophy_key(trophy["id"])), 0, Qt.AlignmentFlag.AlignTop
            )
            head.addWidget(_label(trophy["name"], "SectionTitle"), 1)
            tier = QLabel(trophy["tier"].upper())
            tier.setStyleSheet(
                "color:%s;font-weight:700;font-size:11px;"
                % _TIER_COLORS.get(trophy["tier"], "#A8B0BC")
            )
            head.addWidget(tier, 0, Qt.AlignmentFlag.AlignTop)
            card.addLayout(head)
            _detail(card, "Requisito", trophy["requirement"])
            _detail(card, "Atalho", trophy["shortcut"])
            layout.addWidget(frame)
            haystack = _norm(
                f"{trophy['name']} {trophy['tier']} {trophy['requirement']} {trophy['shortcut']}"
            )
            self._trophy_rows.append((frame, haystack, trophy["id"]))

    def _filter_trophies(self) -> None:
        query = _norm(self.trophy_search.text()).strip()
        pending = self.trophy_pending.isChecked()
        visible = 0
        for frame, haystack, trophy_id in self._trophy_rows:
            got = keys.trophy_key(trophy_id) in self._done
            show = query in haystack and (not pending or not got)
            frame.setVisible(show)
            visible += int(show)
        self.trophy_empty.setVisible(visible == 0)

    # --------------------------------------------------------- 08 Pesquisa
    def _build_research(self, layout: QVBoxLayout) -> None:
        for i, item in enumerate(guide_data.RESEARCH):
            frame, card = _card()
            head = QHBoxLayout()
            head.setSpacing(8)
            head.addWidget(self._checkbox(keys.research_key(i)), 0, Qt.AlignmentFlag.AlignTop)
            head.addWidget(_label(f"#{item['order']}", "Kicker", wrap=False), 0)
            head.addWidget(_label(item["item"], "SectionTitle"), 1)
            head.addWidget(_pill(item["when"]), 0, Qt.AlignmentFlag.AlignTop)
            card.addLayout(head)
            _detail(card, "Por quê", item["why"])
            layout.addWidget(frame)

    # ---------------------------------------------------- 09 Mapas / Imagens
    def _build_visuals(self, layout: QVBoxLayout) -> None:
        for visual in guide_data.VISUALS:
            frame, card = _card()
            card.addWidget(_label(visual["title"], "SectionTitle"))
            card.addWidget(_label(visual["caption"], "Muted"))
            self._add_image(card, visual["image"])
            card.addWidget(_label(f"Fonte da imagem: {visual['source']}", "Muted"))
            card.addWidget(_link("Abrir imagem no navegador ↗", visual["image"]))
            layout.addWidget(frame)

    # ------------------------------------------------------------ 10 Fontes
    def _build_sources(self, layout: QVBoxLayout) -> None:
        for source in guide_data.SOURCES:
            frame, card = _card()
            card.addWidget(_label(source["title"], "SectionTitle"))
            card.addWidget(_label(source["note"], "Muted"))
            card.addWidget(_link("Abrir fonte ↗", source["url"]))
            layout.addWidget(frame)
