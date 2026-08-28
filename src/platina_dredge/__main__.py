"""Rodar standalone: set PYTHONPATH=src && python -m platina_dredge"""
import sys

from PySide6.QtWidgets import QApplication

from . import guide_data
from .page import GuidePage

_THEME = """
QWidget{background:#0A0B12;color:#F3F6FF;font-family:'Segoe UI';font-size:14px}
QLabel#PageTitle{font-size:30px;font-weight:700}
QLabel#CardTitle{font-size:22px;font-weight:700;font-family:'Bahnschrift'}
QLabel#SectionTitle{font-size:16px;font-weight:700}
QLabel#Muted{color:#A8B0BC}
QLabel#Kicker{color:#37F2FF;font-family:'Consolas';font-size:11px;font-weight:700}
QLabel#StatusPill{background:#0A0B12;border:1px solid #273140;border-radius:8px;padding:6px 10px;color:#C7D0DD;font-weight:600}
QFrame#NeonPanel{background:#0D121B;border:1px solid #273140;border-radius:10px}
QLineEdit{background:#0B111A;border:1px solid #273140;border-radius:8px;padding:8px 10px;color:#F3F6FF}
QComboBox{background:#0B111A;border:1px solid #273140;border-radius:8px;padding:7px 10px;color:#F3F6FF}
QPushButton{background:#0D121B;border:1px solid #273140;border-radius:8px;padding:8px 12px;color:#F3F6FF}
QPushButton:hover{border-color:#37F2FF}
QPushButton#PrimaryButton{border-color:#37F2FF}
QCheckBox::indicator{width:18px;height:18px;border-radius:5px;border:1px solid #596373;background:#0B111A}
QCheckBox::indicator:checked{background:#14383F;border-color:#37F2FF}
QScrollArea{border:0}
"""


def run() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(_THEME)
    page = GuidePage()
    page.setWindowTitle(f"{guide_data.GAME_NAME} — Guia de Platina")
    page.resize(980, 860)
    page.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
