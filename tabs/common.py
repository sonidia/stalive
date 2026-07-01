from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextFormat
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from shared import PALETTE

COMPACT_CONTROL_HEIGHT = 32


class LinkedPlainTextEdit(QPlainTextEdit):
    line_hovered = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._highlight_line = -1
        self._suppress_hover_until_leave = False

    def mouseMoveEvent(self, event):
        if event.buttons() or self._suppress_hover_until_leave:
            self.set_highlight_line(-1)
            super().mouseMoveEvent(event)
            return

        cursor = self.cursorForPosition(event.position().toPoint())
        block = cursor.block()
        if not block.isValid() or not block.text().strip():
            self.line_hovered.emit(-1)
            super().mouseMoveEvent(event)
            return

        line = block.blockNumber()
        if line != self._highlight_line:
            self.line_hovered.emit(line)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        self._suppress_hover_until_leave = True
        self.line_hovered.emit(-1)
        super().mousePressEvent(event)

    def focusInEvent(self, event):
        self._suppress_hover_until_leave = True
        self.line_hovered.emit(-1)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._suppress_hover_until_leave = False
        self.line_hovered.emit(-1)
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        self._suppress_hover_until_leave = True
        self.line_hovered.emit(-1)
        super().keyPressEvent(event)

    def leaveEvent(self, event):
        self._suppress_hover_until_leave = False
        self.line_hovered.emit(-1)
        super().leaveEvent(event)

    def set_highlight_line(self, line: int):
        self._highlight_line = line
        selections = []
        if line >= 0:
            block = self.document().findBlockByNumber(line)
            if block.isValid():
                selection = QTextEdit.ExtraSelection()
                selection.cursor = QTextCursor(block)
                selection.cursor.clearSelection()
                fmt = QTextCharFormat()
                fmt.setBackground(QColor("#1f2a44"))
                fmt.setProperty(QTextFormat.Property.FullWidthSelection, True)
                selection.format = fmt
                selections.append(selection)
        self.setExtraSelections(selections)


def small_button_style(accent: bool = False, danger: bool = False) -> str:
    if accent:
        bg = PALETTE["accent"]
        hover = PALETTE["btn_hv"]
        color = "#fff"
        border = PALETTE["accent"]
    elif danger:
        bg = PALETTE["entry_bg"]
        hover = PALETTE["error"]
        color = PALETTE["error"]
        border = PALETTE["error"]
    else:
        bg = PALETTE["entry_bg"]
        hover = PALETTE["panel"]
        color = PALETTE["label"]
        border = PALETTE["border"]

    return (
        f"QPushButton {{ background: {bg}; color: {color}; "
        f"border: 1px solid {border}; border-radius: 6px; "
        f"padding: 5px 12px; font-size: 8pt; font-weight: 700; }}"
        f"QPushButton:hover {{ background: {hover}; color: #fff; border-color: {hover}; }}"
        f"QPushButton:pressed {{ background: {PALETTE['accent']}; color: #fff; }}"
        "QPushButton:disabled { opacity: 0.45; }"
    )


def make_tool_button(
    text: str,
    slot,
    *,
    accent: bool = False,
    danger: bool = False,
    tooltip: str = "",
) -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(COMPACT_CONTROL_HEIGHT)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(small_button_style(accent=accent, danger=danger))
    if tooltip:
        btn.setToolTip(tooltip)
    btn.clicked.connect(slot)
    return btn


def make_action_row(*widgets: QWidget, stretch_first: bool = True) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(8)
    if stretch_first:
        row.addStretch()
    for widget in widgets:
        row.addWidget(widget)
    return row


def make_section(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("toolSection")
    return label


def make_hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setObjectName("toolHint")
    return label


def make_text_area(
    placeholder: str,
    *,
    tooltip: str = "",
    minimum_height: int = 120,
    read_only: bool = False,
    output: bool = False,
) -> QPlainTextEdit:
    area = QPlainTextEdit()
    area.setObjectName("toolOutput" if output else "toolTextArea")
    area.setPlaceholderText(placeholder)
    area.setReadOnly(read_only)
    area.setMinimumHeight(minimum_height)
    area.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    if tooltip:
        area.setToolTip(tooltip)
    return area


def separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {PALETTE['border']}; margin: 6px 0;")
    return line


def build_tool_shell(
    widget: QWidget,
    title_text: str,
    show_close_button: bool,
    close_handler,
    outer_margins: tuple[int, int, int, int],
) -> tuple[QVBoxLayout, QVBoxLayout]:
    widget.setObjectName("toolPage")
    outer = QVBoxLayout(widget)
    outer.setContentsMargins(*outer_margins)
    outer.setSpacing(9)

    if show_close_button:
        header = QHBoxLayout()
        title = QLabel(title_text)
        title.setObjectName("toolTitle")
        header.addWidget(title)
        header.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedSize(24, 24)
        close_btn.setToolTip("Close")
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {PALETTE['subtext']}; "
            "border: none; font-size: 10pt; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {PALETTE['error']}; color: #fff; }}"
        )
        close_btn.clicked.connect(close_handler or widget.close)
        header.addWidget(close_btn)
        outer.addLayout(header)
        outer.addWidget(separator())

    return outer, outer
