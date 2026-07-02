from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

class CustomTopBar(QWidget):
    tab_changed = Signal(int)

    def __init__(self, title: str, icon: QIcon | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("customTopBar")
        self.setFixedHeight(30)

        self._drag_pos: QPoint | None = None
        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        self._tab_group.idClicked.connect(self.tab_changed.emit)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(6)

        if icon is not None and not icon.isNull():
            icon_label = QLabel()
            icon_label.setObjectName("topBarIcon")
            icon_label.setPixmap(icon.pixmap(QSize(16, 16)))
            icon_label.setFixedSize(18, 18)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setObjectName("topBarTitle")
        layout.addWidget(title_label)
        layout.addStretch(1)

        self._tab_strip = QWidget()
        self._tab_strip.setObjectName("topBarTabStrip")
        self._tab_layout = QHBoxLayout(self._tab_strip)
        self._tab_layout.setContentsMargins(1, 1, 1, 1)
        self._tab_layout.setSpacing(2)
        layout.addWidget(self._tab_strip, 0)

        self._minimize_btn = self._make_window_button("-", "Minimize")
        self._maximize_btn = self._make_window_button("[]", "Maximize")
        self._close_btn = self._make_window_button("x", "Close", close=True)

        self._minimize_btn.clicked.connect(lambda: self.window().showMinimized())
        self._maximize_btn.clicked.connect(self._toggle_maximized)
        self._close_btn.clicked.connect(lambda: self.window().close())

        layout.addWidget(self._minimize_btn)
        layout.addWidget(self._maximize_btn)
        layout.addWidget(self._close_btn)

    def add_tab(self, index: int, text: str, icon: QIcon):
        button = QPushButton(icon, text)
        button.setObjectName("topBarTabButton")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedHeight(26)
        button.setMinimumWidth(86)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._tab_group.addButton(button, index)
        self._tab_layout.addWidget(button)
        if index == 0:
            button.setChecked(True)

    def set_current_index(self, index: int):
        button = self._tab_group.button(index)
        if button is not None:
            button.setChecked(True)

    def _make_window_button(self, text: str, tooltip: str, *, close: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("topBarCloseButton" if close else "topBarWindowButton")
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(30, 30)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    def _toggle_maximized(self):
        window = self.window()
        if window.isMaximized():
            window.showNormal()
            self._maximize_btn.setText("[]")
        else:
            window.showMaximized()
            self._maximize_btn.setText("[]")

    def _is_control_at(self, pos) -> bool:
        widget = self.childAt(pos)
        return isinstance(widget, QPushButton)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._is_control_at(event.position().toPoint()):
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            window = self.window()
            if window.isMaximized():
                return
            window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._is_control_at(event.position().toPoint()):
            self._toggle_maximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
