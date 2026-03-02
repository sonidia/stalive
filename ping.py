"""
ping.py – Port connectivity check and proxy liveness ping helpers.

Exported symbols used by app.py:
  • PortCheckWorker  – QObject worker: checks if a TCP port is open on a host
  • ProxyPingWorker  – QObject worker: tests whether a proxy is alive and records RTT
  • PingModal        – QDialog: modal UI containing both checks
"""

from __future__ import annotations

import socket
import time

import requests

from PySide6.QtCore import QObject, QThread, Qt, Signal, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget, QFrame,
)

from shared import PALETTE
from utils import current_ipv4

# ─── Port Check Worker ────────────────────────────────────────────────────────

class PortCheckWorker(QObject):
    """
    Checks whether a TCP port is reachable on the given host.

    Emits:
        result(connected: bool, elapsed_ms: float, error_msg: str)
    """
    result = Signal(bool, float, str)

    def __init__(self, host: str, port: int, timeout: float = 5.0):
        super().__init__()
        self._host = host
        self._port = port
        self._timeout = timeout

    def run(self):
        t0 = time.monotonic()
        try:
            with socket.create_connection((self._host, self._port), timeout=self._timeout):
                elapsed = (time.monotonic() - t0) * 1000
                self.result.emit(True, elapsed, "")
        except socket.timeout:
            elapsed = (time.monotonic() - t0) * 1000
            self.result.emit(False, elapsed, "Timed out")
        except ConnectionRefusedError:
            elapsed = (time.monotonic() - t0) * 1000
            self.result.emit(False, elapsed, "Connection refused")
        except OSError as exc:
            elapsed = (time.monotonic() - t0) * 1000
            self.result.emit(False, elapsed, str(exc))


# ─── Proxy Ping Worker ────────────────────────────────────────────────────────

class ProxyPingWorker(QObject):
    """
    Tests whether an HTTP proxy is alive by making a request through it to
    httpbin.org/ip and measuring round-trip time.

    Emits:
        result(alive: bool, elapsed_ms: float, origin_ip: str, error_msg: str)
    """
    result = Signal(bool, float, str, str)

    TEST_URL = "http://httpbin.org/ip"
    TIMEOUT  = 10.0

    def __init__(self, proxy_str: str):
        """
        Args:
            proxy_str: proxy address in ``host:port`` format.
        """
        super().__init__()
        self._proxy = proxy_str.strip()

    def run(self):
        proxies = {
            "http":  f"http://{self._proxy}",
            "https": f"http://{self._proxy}",
        }
        t0 = time.monotonic()
        try:
            resp = requests.get(
                self.TEST_URL,
                proxies=proxies,
                timeout=self.TIMEOUT,
            )
            elapsed = (time.monotonic() - t0) * 1000
            if resp.status_code == 200:
                try:
                    origin = resp.json().get("origin", "")
                except Exception:
                    origin = ""
                self.result.emit(True, elapsed, origin, "")
            else:
                self.result.emit(False, elapsed, "", f"HTTP {resp.status_code}")
        except requests.exceptions.ProxyError as exc:
            elapsed = (time.monotonic() - t0) * 1000
            self.result.emit(False, elapsed, "", f"Proxy error: {exc}")
        except requests.exceptions.ConnectTimeout:
            elapsed = (time.monotonic() - t0) * 1000
            self.result.emit(False, elapsed, "", "Timed out")
        except requests.exceptions.ConnectionError as exc:
            elapsed = (time.monotonic() - t0) * 1000
            self.result.emit(False, elapsed, "", str(exc))
        except Exception as exc:
            elapsed = (time.monotonic() - t0) * 1000
            self.result.emit(False, elapsed, "", str(exc))


# ─── Shared style helpers ─────────────────────────────────────────────────────

def _small_btn_style(accent: bool = False, danger: bool = False) -> str:
    if accent:
        bg  = PALETTE["accent"]
        hv  = PALETTE["btn_hv"]
        col = "#fff"
        border = PALETTE["accent"]
    elif danger:
        bg  = PALETTE["entry_bg"]
        hv  = PALETTE["error"]
        col = PALETTE["error"]
        border = PALETTE["error"]
    else:
        bg  = PALETTE["entry_bg"]
        hv  = PALETTE["panel"]
        col = PALETTE["label"]
        border = PALETTE["border"]
    return (
        f"QPushButton {{ background: {bg}; color: {col}; "
        f"border: 1.5px solid {border}; border-radius: 8px; "
        f"padding: 6px 18px; font-size: 9pt; font-weight: 600; }}"
        f"QPushButton:hover {{ background: {hv}; color: #fff; border-color: {hv}; }}"
        f"QPushButton:pressed {{ background: {PALETTE['accent']}; color: #fff; }}"
        f"QPushButton:disabled {{ opacity: 0.45; }}"
    )


def _result_style(ok: bool) -> str:
    color = PALETTE["success"] if ok else PALETTE["error"]
    return (
        f"color: {color}; font-size: 9pt; font-weight: 600; background: transparent;"
    )

def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {PALETTE['border']}; margin: 4px 0;")
    return line

# ─── Ping Modal ───────────────────────────────────────────────────────────────

class PingModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ping & Port Check")
        self.setModal(True)
        self.setFixedWidth(460)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Worker/thread references – kept so we can clean up
        self._port_thread: QThread | None = None
        self._port_worker: PortCheckWorker | None = None
        self._proxy_thread: QThread | None = None
        self._proxy_worker: ProxyPingWorker | None = None

        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        # Center on screen after the widget has been shown (size is now accurate)
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2,
        )

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self):
        # Outer wrapper gives us the rounded card look
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("pingModalCard")
        card.setStyleSheet(
            f"QWidget#pingModalCard {{"
            f"  background: {PALETTE['panel']};"
            f"  border: 1.5px solid {PALETTE['border']};"
            f"  border-radius: 14px;"
            f"}}"
        )
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ── Header ──────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        title = QLabel("🏓 Ping & Port Check")
        title.setStyleSheet(
            f"color: {PALETTE['text']}; font-size: 11pt; font-weight: 700; background: transparent;"
        )
        header_row.addWidget(title)
        header_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {PALETTE['subtext']}; "
            f"border: none; font-size: 11pt; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {PALETTE['error']}; color: #fff; }}"
        )
        close_btn.clicked.connect(self.close)
        header_row.addWidget(close_btn)
        layout.addLayout(header_row)

        layout.addWidget(_separator())

        # ── Panel 1 – Port check ─────────────────────────────────────────────
        layout.addWidget(self._make_section_label("🔌  Port Connectivity Check"))

        port_desc = QLabel(
            "Enter <b>host:port</b> (e.g. <code>8.8.8.8:53</code>) or just <b>port</b> "
            "to verify TCP connectivity."
        )
        port_desc.setWordWrap(True)
        port_desc.setStyleSheet(
            f"color: {PALETTE['subtext']}; font-size: 8pt; background: transparent;"
        )
        layout.addWidget(port_desc)

        port_input_row = QHBoxLayout()
        port_input_row.setSpacing(8)

        self._port_input = QLineEdit()
        self._port_input.setPlaceholderText("host:port or port")
        self._port_input.setFixedHeight(34)
        self._port_input.returnPressed.connect(self._run_port_check)
        port_input_row.addWidget(self._port_input, 1)

        self._port_check_btn = QPushButton("Check Port")
        self._port_check_btn.setFixedHeight(34)
        self._port_check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._port_check_btn.setStyleSheet(_small_btn_style(accent=True))
        self._port_check_btn.clicked.connect(self._run_port_check)
        port_input_row.addWidget(self._port_check_btn)
        layout.addLayout(port_input_row)

        self._port_result = QLabel("")
        self._port_result.setWordWrap(True)
        self._port_result.setMinimumHeight(20)
        self._port_result.setStyleSheet(f"color: {PALETTE['subtext']}; font-size: 9pt; background: transparent;")
        layout.addWidget(self._port_result)

        layout.addWidget(_separator())

        # ── Panel 2 – Proxy ping ─────────────────────────────────────────────
        layout.addWidget(self._make_section_label("🌐  Proxy Liveness Ping"))

        proxy_desc = QLabel(
            "Enter proxy as <b>host:port</b> (e.g. <code>1.2.3.4:8080</code>) to test "
            "whether the proxy is alive and measure its response time."
        )
        proxy_desc.setWordWrap(True)
        proxy_desc.setStyleSheet(
            f"color: {PALETTE['subtext']}; font-size: 8pt; background: transparent;"
        )
        layout.addWidget(proxy_desc)

        proxy_input_row = QHBoxLayout()
        proxy_input_row.setSpacing(8)

        self._proxy_input = QLineEdit()
        self._proxy_input.setPlaceholderText("host:port")
        self._proxy_input.setFixedHeight(34)
        self._proxy_input.returnPressed.connect(self._run_proxy_ping)
        proxy_input_row.addWidget(self._proxy_input, 1)

        self._proxy_ping_btn = QPushButton("Ping Proxy")
        self._proxy_ping_btn.setFixedHeight(34)
        self._proxy_ping_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._proxy_ping_btn.setStyleSheet(_small_btn_style(accent=True))
        self._proxy_ping_btn.clicked.connect(self._run_proxy_ping)
        proxy_input_row.addWidget(self._proxy_ping_btn)
        layout.addLayout(proxy_input_row)

        self._proxy_result = QLabel("")
        self._proxy_result.setWordWrap(True)
        self._proxy_result.setMinimumHeight(20)
        self._proxy_result.setStyleSheet(f"color: {PALETTE['subtext']}; font-size: 9pt; background: transparent;")
        layout.addWidget(self._proxy_result)

    # ── Section label ──────────────────────────────────────────────────────

    @staticmethod
    def _make_section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {PALETTE['accent2']}; font-size: 9pt; font-weight: 700; background: transparent;"
        )
        return lbl

    # ── Port check logic ───────────────────────────────────────────────────

    def _run_port_check(self):
        raw = self._port_input.text().strip()
        if not raw:
            self._port_result.setText("⚠  Please enter a host:port or port number.")
            self._port_result.setStyleSheet(
                f"color: {PALETTE['warning']}; font-size: 9pt; background: transparent;"
            )
            return

        # Parse input
        if ":" in raw:
            parts = raw.rsplit(":", 1)
            host, port_str = parts[0].strip(), parts[1].strip()
        else:
            host, port_str = current_ipv4(), raw

        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError("Out of range")
        except ValueError:
            self._port_result.setText("⚠  Invalid port number (must be 1–65535).")
            self._port_result.setStyleSheet(
                f"color: {PALETTE['warning']}; font-size: 9pt; background: transparent;"
            )
            return

        self._port_check_btn.setEnabled(False)
        self._port_result.setStyleSheet(
            f"color: {PALETTE['subtext']}; font-size: 9pt; background: transparent;"
        )
        self._port_result.setText(f"⏳  Checking {host}:{port} …")

        self._port_thread = QThread()
        self._port_worker = PortCheckWorker(host, port)
        self._port_worker.moveToThread(self._port_thread)
        self._port_thread.started.connect(self._port_worker.run)
        self._port_worker.result.connect(self._on_port_result)
        self._port_worker.result.connect(self._port_thread.quit)
        self._port_thread.finished.connect(self._port_thread.deleteLater)
        self._port_thread.start()

    def _on_port_result(self, connected: bool, elapsed_ms: float, error: str):
        self._port_check_btn.setEnabled(True)
        host_port = self._port_input.text().strip()

        if connected:
            self._port_result.setText(
                f"✅  Connected  —  {host_port}  is reachable  ({elapsed_ms:.0f} ms)"
            )
            self._port_result.setStyleSheet(_result_style(True))
        else:
            detail = f"  ({error})" if error else ""
            self._port_result.setText(
                f"❌  Not connected  —  {host_port}  is unreachable{detail}"
            )
            self._port_result.setStyleSheet(_result_style(False))

    # ── Proxy ping logic ───────────────────────────────────────────────────

    def _run_proxy_ping(self):
        raw = self._proxy_input.text().strip()
        if not raw:
            self._proxy_result.setText("⚠  Please enter a proxy address (host:port).")
            self._proxy_result.setStyleSheet(
                f"color: {PALETTE['warning']}; font-size: 9pt; background: transparent;"
            )
            return

        if ":" not in raw:
            self._proxy_result.setText("⚠  Invalid format – use  host:port  (e.g. 1.2.3.4:8080).")
            self._proxy_result.setStyleSheet(
                f"color: {PALETTE['warning']}; font-size: 9pt; background: transparent;"
            )
            return

        self._proxy_ping_btn.setEnabled(False)
        self._proxy_result.setStyleSheet(
            f"color: {PALETTE['subtext']}; font-size: 9pt; background: transparent;"
        )
        self._proxy_result.setText(f"⏳  Pinging proxy {raw} …")

        self._proxy_thread = QThread()
        self._proxy_worker = ProxyPingWorker(raw)
        self._proxy_worker.moveToThread(self._proxy_thread)
        self._proxy_thread.started.connect(self._proxy_worker.run)
        self._proxy_worker.result.connect(self._on_proxy_result)
        self._proxy_worker.result.connect(self._proxy_thread.quit)
        self._proxy_thread.finished.connect(self._proxy_thread.deleteLater)
        self._proxy_thread.start()

    def _on_proxy_result(self, alive: bool, elapsed_ms: float, origin_ip: str, error: str):
        self._proxy_ping_btn.setEnabled(True)
        proxy_addr = self._proxy_input.text().strip()

        if alive:
            origin_part = f"  ·  origin IP: {origin_ip}" if origin_ip else ""
            self._proxy_result.setText(
                f"✅  Alive  —  {proxy_addr}  responded in {elapsed_ms:.0f} ms{origin_part}"
            )
            self._proxy_result.setStyleSheet(_result_style(True))
        else:
            detail = f"  ({error})" if error else ""
            if elapsed_ms >= 0:
                timing = f"  (after {elapsed_ms:.0f} ms)"
            else:
                timing = ""
            self._proxy_result.setText(
                f"❌  Dead  —  {proxy_addr}  did not respond{timing}{detail}"
            )
            self._proxy_result.setStyleSheet(_result_style(False))

    # ── Drag-to-move (frameless window) ───────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
