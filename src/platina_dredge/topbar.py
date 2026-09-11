"""O topo recolhível do guia: três níveis, uma linha neon e bolinhas.

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
volta para o 2) — e o clique duplo no balão faz o mesmo, para quem preferir.

O nível não é lembrado entre aberturas (abre sempre no 2); a posição do balão é.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QMouseEvent, QPainter, QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QSizePolicy, QVBoxLayout, QWidget,
)

CYAN = "#37F2FF"
MAGENTA = "#FF4FD8"
LIME = "#B9FF43"

LEVEL_FULL = 1
LEVEL_MIN = 2
LEVEL_BALLOON = 3


class NeonDot(QWidget):
    """Um ponto neon que cresce ao passar o mouse e mostra a seta do que faz."""

    clicked = Signal()

    def __init__(self, arrow: str, tip: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._arrow = arrow      # "▲" ou "▼"
        self._hover = False
        self.setToolTip(tip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(30, 30)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = 10.0 if self._hover else 6.5

        # halo
        halo = QRadialGradient(center, radius * 2.2)
        halo.setColorAt(0.0, QColor(55, 242, 255, 110 if self._hover else 70))
        halo.setColorAt(1.0, QColor(55, 242, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(halo))
        painter.drawEllipse(center, radius * 2.2, radius * 2.2)

        # o ponto, no gradiente ciano → magenta do design system
        fill = QLinearGradient(center.x() - radius, center.y() - radius,
                               center.x() + radius, center.y() + radius)
        fill.setColorAt(0.0, QColor(CYAN))
        fill.setColorAt(1.0, QColor(MAGENTA))
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(QColor(10, 11, 18), 1.2))
        painter.drawEllipse(center, radius, radius)

        if self._hover:
            font = QFont(self.font())
            font.setPointSizeF(8.5)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(10, 11, 18))
            painter.drawText(QRectF(0, 0, self.width(), self.height() - 1),
                             Qt.AlignmentFlag.AlignCenter, self._arrow)
        painter.end()


class NeonRule(QWidget):
    """A linha que separa o topo do conteúdo, com as bolinhas no meio."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(30)
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(10)
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
            # widget novo num pai já visível nasce escondido — precisa do show()
            dot.show()

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
        layout.setContentsMargins(12, 8, 12, 10)
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
        self.hide()

    def sync(self, bar: QProgressBar, pill_texts: list[str]) -> None:
        self.bar.setRange(bar.minimum(), bar.maximum())
        self.bar.setValue(bar.value())
        self.bar.setFormat(bar.format())
        self.pills.setText("  •  ".join(t for t in pill_texts if t))

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


def _clamp(pos: QPoint, size, bounds) -> QPoint:
    x = max(0, min(pos.x(), bounds.width() - size.width()))
    y = max(0, min(pos.y(), bounds.height() - size.height()))
    return QPoint(x, y)


class TopBar(QObject):
    """Rege os três níveis do topo de um guia.

    `blocks` são os widgets do topo, na ordem: título, cabeçalho recolhível
    (abertura + números + busca + botões), progresso e abas. `rule` deve ser
    inserido no layout logo abaixo deles, antes do conteúdo.
    """

    def __init__(self, page: QWidget, *, title: QWidget, header: QWidget,
                 progress: QWidget, nav: QWidget, bar: QProgressBar,
                 pills: list[QLabel], load_ui: Callable[[], dict],
                 save_ui: Callable[[dict], None]) -> None:
        super().__init__(page)
        self._page = page
        self._title, self._header, self._progress, self._nav = title, header, progress, nav
        self._bar = bar
        self._pills = pills
        self._load_ui, self._save_ui = load_ui, save_ui
        self.level = LEVEL_MIN

        self.rule = NeonRule()
        self.balloon = ProgressBalloon(bar.styleSheet(), page)
        self.balloon.restore.connect(lambda: self.set_level(LEVEL_MIN))
        self.balloon.moved.connect(self._remember_balloon)
        page.installEventFilter(self)
        self.set_level(LEVEL_MIN)

    # ------------------------------------------------------------- níveis
    def set_level(self, level: int) -> None:
        self.level = level
        full, minimal, balloon = (level == LEVEL_FULL), (level == LEVEL_MIN), (level == LEVEL_BALLOON)
        self._header.setVisible(full)
        for widget in (self._title, self._progress, self._nav, self.rule):
            widget.setVisible(not balloon)

        if full:
            self.rule.set_dots([self._dot("▲", "Recolher o cabeçalho", LEVEL_MIN)])
        elif minimal:
            self.rule.set_dots([
                self._dot("▼", "Mostrar a abertura, os números, a busca e os botões", LEVEL_FULL),
                self._dot("▲", "Esconder o topo inteiro — o progresso vira um balão", LEVEL_BALLOON),
            ])
        else:
            self.rule.set_dots([])

        if balloon:
            self.sync()
            self._place_balloon()
            self.balloon.show()
            self.balloon.raise_()
        else:
            self.balloon.hide()

    def _dot(self, arrow: str, tip: str, target: int) -> NeonDot:
        dot = NeonDot(arrow, tip)
        dot.clicked.connect(lambda: self.set_level(target))
        return dot

    # ------------------------------------------------------------- balão
    def sync(self) -> None:
        """Chame no fim do _update_progress da página."""
        self.balloon.sync(self._bar, [p.text() for p in self._pills])

    def _place_balloon(self) -> None:
        self.balloon.adjustSize()
        saved = self._load_ui().get("balloon_pos")
        if isinstance(saved, list) and len(saved) == 2:
            pos = QPoint(int(saved[0]), int(saved[1]))
        else:
            pos = QPoint(self._page.width() - self.balloon.width() - 28, 12)
        self.balloon.move(_clamp(pos, self.balloon.size(), self._page.size()))

    def _remember_balloon(self, pos: QPoint) -> None:
        ui = self._load_ui()
        ui["balloon_pos"] = [pos.x(), pos.y()]
        self._save_ui(ui)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self._page and event.type() == QEvent.Type.Resize and self.balloon.isVisible():
            self.balloon.move(_clamp(self.balloon.pos(), self.balloon.size(), self._page.size()))
        return False
