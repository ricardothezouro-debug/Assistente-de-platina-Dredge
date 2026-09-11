"""O topo recolhível do guia: três níveis, uma linha neon, bolinhas e movimento.

Com o jogo aberto, o que importa é a lista; o cabeçalho inteiro (abertura,
números, busca, botões) custa meia tela. Então o topo tem três níveis:

  1  tudo à vista        — título, abertura, números, busca, botões, progresso, abas
  2  minimizado          — título, progresso e abas (é o nível em que o guia abre)
  3  balão               — some tudo; o progresso vira um balão flutuante que
                           você arrasta para onde quiser

Entre o topo e o conteúdo fica uma linha no gradiente do design system
(ciano → magenta, a mesma da base dos NeonPanel) com bolinhas neon no meio:
em repouso são só pontos; ao passar o mouse crescem e mostram a seta do que
fazem. No nível 1 há uma bolinha (▲, fecha para o 2); no nível 2 há duas
(▼ abre para o 1, ▲ fecha para o 3); no nível 3 a bolinha vai no balão (▼
volta para o 2) — e o clique duplo no balão faz o mesmo.

COMO A ANIMAÇÃO FUNCIONA (e por que não é a óbvia). Animar a altura do topo
dentro do layout obrigaria o Qt a reaplicar o layout dos milhares de widgets
da lista a cada quadro — ~125 ms por quadro num guia grande; nada fica fluido
assim. Então a transição é feita com dois retratos: congelamos a tela, aplicamos
o estado final de uma vez só (o custo fica escondido atrás de um quadro
parado), tiramos o segundo retrato e animamos a passagem de um para o outro
num overlay de pixmaps — o conteúdo desliza para a nova posição e o topo se
revela/recolhe como uma cortina. O balão é um widget de verdade e viaja por
cima do overlay: nasce sobre a barra de progresso e voa até o lugar dele; na
volta faz o caminho inverso, some sobre a barra, e o topo se abre.

O nível não é lembrado entre aberturas (abre sempre no 2); a posição do balão é.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import (
    QCoreApplication, QEasingCurve, QEvent, QObject, QPoint, QPointF,
    QPropertyAnimation, QRectF, Qt, QVariantAnimation, Signal,
)
from PySide6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QMouseEvent, QPainter, QPen,
    QPixmap, QRadialGradient,
)
from PySide6.QtWidgets import (
    QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QVBoxLayout, QWidget,
)

CYAN = "#37F2FF"
MAGENTA = "#FF4FD8"
INK = QColor(10, 11, 18)
PAGE_BG = QColor(10, 11, 18)

LEVEL_FULL = 1
LEVEL_MIN = 2
LEVEL_BALLOON = 3

_EASE = QEasingCurve.Type.InOutCubic
_SLIDE_MS = 360
_TRAVEL_MS = 480


# ── peças ──────────────────────────────────────────────────────────────────
class NeonDot(QWidget):
    """Um ponto neon que cresce ao passar o mouse e mostra a seta do que faz.

    O halo cabe inteiro dentro do widget (raio máximo < metade do lado): se
    passar da borda o Qt recorta e o brilho vira um quadrado.
    """

    clicked = Signal()
    SIDE = 38

    def __init__(self, arrow: str, tip: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._arrow = arrow      # "▲" ou "▼"
        self._grow = 0.0         # 0 = repouso, 1 = mouse em cima
        self.setToolTip(tip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(self.SIDE, self.SIDE)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_grow)

    def _on_grow(self, value) -> None:
        self._grow = float(value)
        self.update()

    def _animate_to(self, target: float) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._grow)
        self._anim.setEndValue(target)
        self._anim.start()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._animate_to(0.0)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(self.width() / 2, self.height() / 2)
        g = self._grow
        radius = 6.5 + 3.5 * g
        halo_r = 11.0 + 7.5 * g          # 18.5 no máximo: cabe nos 38 de lado

        halo = QRadialGradient(center, halo_r)
        halo.setColorAt(0.0, QColor(55, 242, 255, int(60 + 70 * g)))
        halo.setColorAt(0.55, QColor(255, 79, 216, int(24 + 40 * g)))
        halo.setColorAt(1.0, QColor(55, 242, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(halo))
        painter.drawEllipse(center, halo_r, halo_r)

        fill = QLinearGradient(center.x() - radius, center.y() - radius,
                               center.x() + radius, center.y() + radius)
        fill.setColorAt(0.0, QColor(CYAN))
        fill.setColorAt(1.0, QColor(MAGENTA))
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(INK, 1.2))
        painter.drawEllipse(center, radius, radius)

        if g > 0.35:
            font = QFont(self.font())
            font.setPointSizeF(8.5)
            font.setBold(True)
            painter.setFont(font)
            ink = QColor(INK)
            ink.setAlphaF(min(1.0, (g - 0.35) / 0.45))
            painter.setPen(ink)
            painter.drawText(QRectF(0, 0, self.width(), self.height() - 1),
                             Qt.AlignmentFlag.AlignCenter, self._arrow)
        painter.end()


class NeonRule(QWidget):
    """A linha que separa o topo do conteúdo, com as bolinhas no meio."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(NeonDot.SIDE)
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(14)
        self._row.addStretch(1)
        self._dots: list[NeonDot] = []
        self._row.addStretch(1)

    def set_dots(self, dots: list[NeonDot]) -> None:
        for dot in self._dots:
            self._row.removeWidget(dot)
            dot.setParent(None)
        self._dots = dots
        for i, dot in enumerate(dots):
            self._row.insertWidget(1 + i, dot, 0, Qt.AlignmentFlag.AlignCenter)
            dot.show()  # widget novo num pai já visível nasce escondido

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        y = self.height() / 2
        line = QLinearGradient(0.0, y, float(self.width()), y)
        line.setColorAt(0.0, QColor(0, 0, 0, 0))
        line.setColorAt(0.12, QColor(CYAN))
        line.setColorAt(0.5, QColor(39, 49, 64))
        line.setColorAt(0.88, QColor(MAGENTA))
        line.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(QPen(QBrush(line), 1.6))
        painter.drawLine(QPointF(0, y), QPointF(self.width(), y))
        painter.end()
        super().paintEvent(event)


class SlideOverlay(QWidget):
    """Anima a passagem entre dois retratos da página.

    `y0`/`y1` são a altura do topo antes e depois. O conteúdo desliza de y0
    para y1; o topo se revela (ou recolhe) como uma cortina; os dois retratos
    se fundem num crossfade para esconder qualquer diferença miúda.
    """

    finished = Signal()

    def __init__(self, page: QWidget) -> None:
        super().__init__(page)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._before = QPixmap()
        self._after = QPixmap()
        self._y0 = self._y1 = 0
        self._p = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(_SLIDE_MS)
        self._anim.setEasingCurve(_EASE)
        self._anim.valueChanged.connect(self._on_step)
        self._anim.finished.connect(self._on_finished)
        self.hide()

    def play(self, before: QPixmap, after: QPixmap, y0: int, y1: int) -> None:
        self._before, self._after, self._y0, self._y1 = before, after, y0, y1
        self._p = 0.0
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def _on_step(self, value) -> None:
        self._p = float(value)
        self.update()

    def _on_finished(self) -> None:
        self.hide()
        self._before = QPixmap()
        self._after = QPixmap()
        self.finished.emit()

    def _draw_slice(self, painter: QPainter, pix: QPixmap, src_y: float, src_h: float,
                    dst_y: float, opacity: float) -> None:
        if src_h <= 0 or opacity <= 0.0 or pix.isNull():
            return
        dpr = pix.devicePixelRatio() or 1.0
        w = self.width()
        painter.setOpacity(opacity)
        painter.drawPixmap(
            QRectF(0, dst_y, w, src_h), pix,
            QRectF(0, src_y * dpr, w * dpr, src_h * dpr))

    def paintEvent(self, event) -> None:  # noqa: N802
        if self._before.isNull() or self._after.isNull():
            return
        p = self._p
        h = self.height()
        y0, y1 = self._y0, self._y1
        y = y0 + (y1 - y0) * p          # onde o conteúdo começa neste quadro
        painter = QPainter(self)
        painter.fillRect(self.rect(), PAGE_BG)
        # conteúdo: o retrato de depois inteiro por baixo (é ele que fica) e o
        # de antes se dissolvendo por cima — cobertura total, sem escurecer
        # nem deixar faixa vazia embaixo enquanto desliza
        self._draw_slice(painter, self._after, y1, h - y1, y, 1.0)
        self._draw_slice(painter, self._before, y0, h - y0, y, 1.0 - p)
        # topo: cortina — só o que já cabe acima do ponto que desliza
        painter.setOpacity(1.0)
        painter.fillRect(QRectF(0, 0, self.width(), y), PAGE_BG)
        self._draw_slice(painter, self._after, 0, min(y1, y), 0, 1.0)
        self._draw_slice(painter, self._before, 0, min(y0, y), 0, 1.0 - p)
        painter.end()


class ProgressBalloon(QFrame):
    """O progresso solto na tela, arrastável. Clique duplo (ou a bolinha) volta."""

    restore = Signal()
    moved = Signal(QPoint)

    def __init__(self, bar_qss: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("NeonPanel")
        self.setFixedWidth(300)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._drag_from: QPoint | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 10)
        layout.setSpacing(6)
        head = QHBoxLayout()
        head.setSpacing(8)
        self.title = QLabel("Progresso")
        self.title.setObjectName("Kicker")
        head.addWidget(self.title, 1)
        self.dot = NeonDot("▼", "Voltar a mostrar o topo do guia")
        self.dot.clicked.connect(self.restore.emit)
        head.addWidget(self.dot, 0)
        layout.addLayout(head)
        self.bar = QProgressBar()
        self.bar.setStyleSheet(bar_qss)
        layout.addWidget(self.bar)
        self.pills = QLabel("")
        self.pills.setObjectName("Muted")
        self.pills.setWordWrap(True)
        layout.addWidget(self.pills)

        self._fx = QGraphicsOpacityEffect(self)
        self._fx.setOpacity(1.0)
        self.setGraphicsEffect(self._fx)
        self.hide()

    def sync(self, bar: QProgressBar, pill_texts: list[str]) -> None:
        self.bar.setRange(bar.minimum(), bar.maximum())
        self.bar.setValue(bar.value())
        self.bar.setFormat(bar.format())
        self.pills.setText("  •  ".join(t for t in pill_texts if t))

    def set_opacity(self, value: float) -> None:
        self._fx.setOpacity(value)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_from = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_from is not None and self.parentWidget() is not None:
            target = self.pos() + event.position().toPoint() - self._drag_from
            self.move(_clamp(target, self.size(), self.parentWidget().size()))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_from is not None:
            self._drag_from = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.moved.emit(self.pos())
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self.restore.emit()


class InfoCorner(QWidget):
    """O rodapé virou um "?": passa o mouse e lê; clica e a linha aparece."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.line = QLabel(text)
        self.line.setObjectName("Muted")
        self.line.setWordWrap(True)
        self.line.hide()
        self.button = QPushButton("?")
        self.button.setObjectName("StatusPill")
        self.button.setFixedSize(26, 26)
        self.button.setToolTip(text)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.clicked.connect(lambda: self.line.setVisible(self.line.isHidden()))
        row.addStretch(1)
        row.addWidget(self.line, 0)
        row.addWidget(self.button, 0)


def _clamp(pos: QPoint, size, bounds) -> QPoint:
    x = max(0, min(pos.x(), bounds.width() - size.width()))
    y = max(0, min(pos.y(), bounds.height() - size.height()))
    return QPoint(x, y)


# ── o regente ──────────────────────────────────────────────────────────────
class TopBar(QObject):
    """Rege os três níveis do topo de um guia.

    Recebe as quatro peças já montadas (título, cabeçalho recolhível, fileira
    do progresso e abas) e devolve `widget`, o topo inteiro, para a página pôr
    no layout logo acima do conteúdo.
    """

    def __init__(self, page: QWidget, *, title: QWidget, header: QWidget,
                 progress: QWidget, nav: QWidget, bar: QProgressBar,
                 pills: list[QLabel], load_ui: Callable[[], dict],
                 save_ui: Callable[[dict], None]) -> None:
        super().__init__(page)
        self._page = page
        self._header = header
        self._progress = progress
        self._bar = bar
        self._pills = pills
        self._load_ui, self._save_ui = load_ui, save_ui
        self.level = LEVEL_MIN
        self._busy = False

        self.rule = NeonRule()
        self.widget = QWidget()
        column = QVBoxLayout(self.widget)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        for piece in (title, header, progress, nav, self.rule):
            column.addWidget(piece)

        self.overlay = SlideOverlay(page)
        self.overlay.finished.connect(self._done)

        self.balloon = ProgressBalloon(bar.styleSheet(), page)
        self.balloon.restore.connect(lambda: self.set_level(LEVEL_MIN))
        self.balloon.moved.connect(self._remember_balloon)
        self._travel = QPropertyAnimation(self.balloon, b"pos", self)
        self._travel.setDuration(_TRAVEL_MS)
        self._travel.setEasingCurve(_EASE)
        self._fade = QVariantAnimation(self)
        self._fade.setDuration(_TRAVEL_MS)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.valueChanged.connect(lambda v: self.balloon.set_opacity(float(v)))
        page.installEventFilter(self)

        header.hide()
        self._apply_dots(LEVEL_MIN)

    # ------------------------------------------------------------- níveis
    def set_level(self, level: int) -> None:
        if self._busy or level == self.level:
            return
        previous, self.level = self.level, level
        self._busy = True
        if previous == LEVEL_BALLOON:
            self._return_from_balloon(level)
        elif level == LEVEL_BALLOON:
            self._go_to_balloon()
        else:
            self._transition(lambda: self._apply_level(level))

    def _done(self) -> None:
        self._busy = False

    def _apply_level(self, level: int) -> None:
        """Aplica o estado final de um nível, sem animar."""
        self._header.setVisible(level == LEVEL_FULL)
        self.widget.setVisible(level != LEVEL_BALLOON)
        self._apply_dots(level)

    def _apply_dots(self, level: int) -> None:
        if level == LEVEL_FULL:
            self.rule.set_dots([self._dot("▲", "Recolher o cabeçalho", LEVEL_MIN)])
        elif level == LEVEL_MIN:
            self.rule.set_dots([
                self._dot("▼", "Mostrar a abertura, os números, a busca e os botões", LEVEL_FULL),
                self._dot("▲", "Esconder o topo inteiro — o progresso vira um balão", LEVEL_BALLOON),
            ])
        else:
            self.rule.set_dots([])

    def _dot(self, arrow: str, tip: str, target: int) -> NeonDot:
        dot = NeonDot(arrow, tip)
        dot.clicked.connect(lambda: self.set_level(target))
        return dot

    # ------------------------------------------------------- a transição
    def _anchor(self) -> int:
        """O y (na página) de onde começa a parte que se move numa transição.

        É o topo da fileira do progresso: tudo dali para baixo desliza junto
        (progresso, abas, linha e conteúdo); o que fica acima — o título — é
        fixo, e o espaço entre os dois é a cortina onde o cabeçalho aparece ou
        some. Com o topo inteiro escondido (nível 3), é 0.
        """
        if self.widget.isHidden() or self._progress.isHidden():
            return 0
        return self._progress.mapTo(self._page, QPoint(0, 0)).y()

    def _transition(self, apply_final: Callable[[], None]) -> None:
        """Retrato antes → estado final aplicado às escuras → retrato depois →
        animação entre os dois. A página não repinta durante a troca, então o
        custo do layout fica invisível."""
        page = self._page
        before = page.grab()
        y0 = self._anchor()
        page.setUpdatesEnabled(False)
        try:
            apply_final()
            layout = page.layout()
            if layout is not None:
                layout.activate()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.LayoutRequest)
            y1 = self._anchor()
            after = page.grab()
        finally:
            page.setUpdatesEnabled(True)
        self.overlay.play(before, after, y0, y1)
        self.balloon.raise_()

    # ------------------------------------------------------------- balão
    def _bar_anchor(self) -> QPoint:
        """Onde o balão 'nasce' e 'morre': em cima da barra de progresso."""
        origin = self._progress.mapTo(self._page, QPoint(0, 0))
        x = origin.x() + max(0, self._progress.width() - self.balloon.width()) // 2
        return _clamp(QPoint(x, origin.y() - 8), self.balloon.size(), self._page.size())

    def _home(self) -> QPoint:
        saved = self._load_ui().get("balloon_pos")
        if isinstance(saved, list) and len(saved) == 2:
            pos = QPoint(int(saved[0]), int(saved[1]))
        else:
            pos = QPoint(self._page.width() - self.balloon.width() - 28, 12)
        return _clamp(pos, self.balloon.size(), self._page.size())

    def _go_to_balloon(self) -> None:
        # o balão nasce sobre a barra (medida ANTES de o topo sumir), o topo
        # se recolhe e o balão voa até o lugar dele
        self.sync()
        self.balloon.adjustSize()
        start = self._bar_anchor()
        home = self._home()
        self._transition(lambda: self._apply_level(LEVEL_BALLOON))
        self.balloon.move(start)
        self.balloon.set_opacity(0.0)
        self.balloon.show()
        self.balloon.raise_()
        self._animate_balloon(home, 0.0, 1.0)

    def _return_from_balloon(self, level: int) -> None:
        # o balão voa de volta até onde a barra vai reaparecer e some; aí o
        # topo se abre
        anchor = self._bar_anchor_when_open(level)

        def open_top() -> None:
            self.balloon.hide()
            self._transition(lambda: self._apply_level(level))

        self._animate_balloon(anchor, 1.0, 0.0)
        self._travel.finished.connect(open_top, Qt.ConnectionType.SingleShotConnection)

    def _bar_anchor_when_open(self, level: int) -> QPoint:
        # a barra está escondida; medimos onde ela vai ficar aplicando o nível
        # às escuras num layout ativado e desfazendo em seguida
        page = self._page
        page.setUpdatesEnabled(False)
        try:
            self._apply_level(level)
            layout = page.layout()
            if layout is not None:
                layout.activate()
            anchor = self._bar_anchor()
            self._apply_level(LEVEL_BALLOON)
            if layout is not None:
                layout.activate()
        finally:
            page.setUpdatesEnabled(True)
        return anchor

    def _animate_balloon(self, to: QPoint, opacity_from: float, opacity_to: float) -> None:
        self._travel.stop()
        self._fade.stop()
        self._travel.setStartValue(self.balloon.pos())
        self._travel.setEndValue(to)
        self._fade.setStartValue(opacity_from)
        self._fade.setEndValue(opacity_to)
        self._travel.start()
        self._fade.start()

    def sync(self) -> None:
        """Chame no fim do _update_progress da página."""
        self.balloon.sync(self._bar, [p.text() for p in self._pills])

    def _remember_balloon(self, pos: QPoint) -> None:
        ui = self._load_ui()
        ui["balloon_pos"] = [pos.x(), pos.y()]
        self._save_ui(ui)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self._page and event.type() == QEvent.Type.Resize:
            if self.overlay.isVisible():
                self.overlay.setGeometry(self._page.rect())
            if self.balloon.isVisible() and not self._busy:
                self.balloon.move(_clamp(self.balloon.pos(), self.balloon.size(), self._page.size()))
        return False
