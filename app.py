import os, sys

from PySide6.QtCore import QEvent, QRect, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

from tabs import HostTab, ProxyTab
from tabs.cliproxy import CliProxyTabMixin, TimerPopover
from shared import PALETTE, STYLESHEET
from top_bar import CustomTopBar

def make_tab_icon(kind: str) -> QIcon:
    pix = QPixmap(18, 18)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    accent = QColor(PALETTE["accent"])
    accent2 = QColor(PALETTE["accent2"])
    panel = QColor(PALETTE["entry_bg"])
    pen = QPen(accent2 if kind != "cliproxy" else accent, 1.8)
    painter.setPen(pen)
    painter.setBrush(panel)

    if kind == "cliproxy":
        painter.drawRoundedRect(QRect(3, 4, 12, 10), 3, 3)
        painter.setBrush(accent)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(5, 7, 3, 3)
        painter.drawEllipse(10, 7, 3, 3)
    elif kind == "ping":
        painter.drawEllipse(4, 4, 10, 10)
        painter.drawLine(9, 2, 9, 5)
        painter.drawLine(9, 13, 9, 16)
        painter.drawLine(2, 9, 5, 9)
        painter.drawLine(13, 9, 16, 9)
    else:
        painter.drawLine(5, 3, 5, 11)
        painter.drawLine(13, 3, 13, 11)
        painter.drawLine(5, 8, 13, 8)
        painter.drawRoundedRect(QRect(6, 11, 6, 4), 2, 2)

    painter.end()
    return QIcon(pix)

if getattr(sys, 'frozen', False):
    _BUNDLE_DIR = sys._MEIPASS
else:
    _BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
# ─── Main window ───────────────────────────────────────────────────────────────
class ProxyApp(QMainWindow, CliProxyTabMixin):
    _status_sig = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proxer - Auto rotate proxies from CliProxy")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # self.setFixedSize(800, 744)
        self._status_sig.connect(self._apply_status)
        self._auto_check_enabled = False
        self._auto_check_interval = 60
        self._auto_check_timer = QTimer()
        self._auto_check_timer.setSingleShot(True)   # fire once; restarted manually after cycle
        self._auto_check_timer.timeout.connect(self._auto_check_all_proxies)
        self._countdown_timer = QTimer()
        self._initial_cliproxy_check_done = False
        self._countdown_timer.timeout.connect(self._update_countdown)
        self._countdown_remaining = self._auto_check_interval
        self._auto_check_pending = 0   # number of cards still being processed in current cycle
        self._pre_check_thread: QThread | None = None   # port pre-check thread
        self._pre_check_worker: "PortPreCheckWorker | None" = None
        self._build_ui()
        self._center()
        self._set_defaults()
        # Timer interval popover (created after _build_ui so C palette is available)
        self._timer_popover = TimerPopover(initial=self._auto_check_interval, parent=self)
        self._timer_popover.interval_changed.connect(self._on_interval_changed)
        self._toggle_auto_check()  # Enable auto-check by default

    def _center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_blur_overlay') and hasattr(self, '_content_widget'):
            if self._blur_overlay.isVisible():
                self._blur_overlay.setGeometry(self._content_widget.geometry())

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._apply_window_chrome()


    # ── Build UI ────────────────────────────────────────────────────────────
    def _add_main_tab(self, widget: QWidget, icon: QIcon, text: str) -> int:
        index = self._tabs.addTab(widget, icon, text)
        self._top_bar.add_tab(index, text, icon)
        return index

    def _apply_window_chrome(self):
        if not hasattr(self, "_root"):
            return
        maximized = self.isMaximized()
        maximized_value = "true" if maximized else "false"
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, not maximized)
        self._root.setProperty("maximized", maximized_value)
        if hasattr(self, "_window_layout"):
            margin = 0 if maximized else 1
            self._window_layout.setContentsMargins(margin, margin, margin, margin)
        self._root.style().unpolish(self._root)
        self._root.style().polish(self._root)
        if hasattr(self, "_top_bar"):
            self._top_bar.setProperty("maximized", maximized_value)
            self._top_bar.style().unpolish(self._top_bar)
            self._top_bar.style().polish(self._top_bar)

    def _build_ui(self):
        root = QWidget()
        self._root = root
        root.setObjectName("central")
        root.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        self._window_layout = main
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        app_icon = QApplication.instance().windowIcon() if QApplication.instance() else QIcon()
        self._top_bar = CustomTopBar("Stalive - Proxy Checker", app_icon, self)
        main.addWidget(self._top_bar, 0)

        body = QWidget()
        body.setObjectName("appBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(12, 0, 12, 0)
        body_layout.setSpacing(0)
        self._main_layout = body_layout
        main.addWidget(body, 1)

        self._build_cliproxy_tab(make_tab_icon)

        self._ping_tab = ProxyTab()
        self._add_main_tab(self._ping_tab, make_tab_icon("ping"), "Proxy")
        self._check_port_tab = HostTab()
        self._add_main_tab(self._check_port_tab, make_tab_icon("check_port"), "Host")

        # Load cached proxies on startup
        self._load_cached_proxies()

        # Initial Cliproxy check runs after overlay is ready.
        self._check_cliproxy_silent()
        self._apply_window_chrome()

    # ── Sort popover ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    icon_path = os.path.join(_BUNDLE_DIR, "icon.png")
    app.setWindowIcon(QIcon(icon_path))
    app.setFont(QFont("Segoe UI", 10))
    win = ProxyApp()
    win.show()
    sys.exit(app.exec())
