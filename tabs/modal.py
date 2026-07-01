from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout

from shared import SlidingTabWidget

from .host import HostTab
from .proxy import ProxyTab


class PingModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Proxy & Host")
        self.setModal(True)
        self.setFixedWidth(560)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = SlidingTabWidget()
        tabs.setObjectName("mainTabs")
        tabs.addTab(
            ProxyTab(
                parent=tabs,
                show_close_button=True,
                close_handler=self.close,
                outer_margins=(0, 8, 0, 0),
            ),
            "Proxy",
        )
        tabs.addTab(
            HostTab(
                parent=tabs,
                show_close_button=True,
                close_handler=self.close,
                outer_margins=(0, 8, 0, 0),
            ),
            "Host",
        )
        layout.addWidget(tabs)

    def showEvent(self, event):
        super().showEvent(event)
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2,
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
