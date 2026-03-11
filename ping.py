from __future__ import annotations

import re, socket, time

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget, QFrame, QComboBox,
)

from shared import PALETTE
from utils import current_ipv4

class ParsedProxy:
    __slots__ = ("protocol", "host", "port", "username", "password")

    def __init__(self, protocol: str, host: str, port: int,
                 username: str = "", password: str = ""):
        self.protocol = protocol   # "http" | "https" | "socks4" | "socks5"
        self.host     = host
        self.port     = port
        self.username = username
        self.password = password

    @property
    def has_auth(self) -> bool:
        return bool(self.username)

    @property
    def display(self) -> str:
        auth = f"{self.username}:***@" if self.has_auth else ""
        return f"{self.protocol.upper()}  {auth}{self.host}:{self.port}"

# Support: [scheme://][user:pass@]host:port
_PROXY_RE = re.compile(
    r"^(?:(?P<proto>[a-zA-Z0-9+\-.]+)://)?"
    r"(?:(?P<user>[^:@\s]+):(?P<pwd>[^@\s]*)@)?"
    r"(?P<host>[a-zA-Z0-9._\-\[\]]+)"
    r":(?P<port>\d{1,5})$"
)

_PROTO_MAP = {
    "http":    "http",
    "https":   "https",
    "socks":   "socks5",
    "socks4":  "socks4",
    "socks4a": "socks4",
    "socks5":  "socks5",
    "socks5h": "socks5",
}

def parse_proxy(raw: str, default_protocol: str = "http") -> ParsedProxy | None:
    raw = raw.strip()
    m = _PROXY_RE.match(raw)
    if not m:
        return None

    proto_raw = (m.group("proto") or "").lower()
    proto     = _PROTO_MAP.get(proto_raw, default_protocol.lower())

    host = m.group("host")
    try:
        port = int(m.group("port"))
        if not (1 <= port <= 65535):
            return None
    except ValueError:
        return None

    return ParsedProxy(
        proto, host, port,
        username=m.group("user") or "",
        password=m.group("pwd")  or "",
    )

class PortCheckWorker(QObject):
    result = Signal(bool, float, str, str)  # ok, ms, error, peer_ip

    def __init__(self, host: str, port: int, timeout: float = 5.0):
        super().__init__()
        self._host    = host
        self._port    = port
        self._timeout = timeout

    def run(self):
        t0 = time.monotonic()
        try:
            with socket.create_connection((self._host, self._port),
                                          timeout=self._timeout) as sock:
                elapsed = (time.monotonic() - t0) * 1000
                peer_ip = sock.getpeername()[0]
                self.result.emit(True, elapsed, "", peer_ip)
        except socket.timeout:
            self.result.emit(False, (time.monotonic() - t0) * 1000, "Timed out", "")
        except ConnectionRefusedError:
            self.result.emit(False, (time.monotonic() - t0) * 1000, "Connection refused", "")
        except OSError as exc:
            self.result.emit(False, (time.monotonic() - t0) * 1000, str(exc), "")


class ProxyPingWorker(QObject):
    """
    Signal: ok, elapsed_ms, peer_ip, error

    Kiểm tra proxy bằng cách mở kết nối TCP trực tiếp tới host:port của proxy
    (không cần gọi bất kỳ URL bên ngoài như httpbin.org).
    Cách này hoạt động giống hệt proxy.py: dùng socket.create_connection để
    xác nhận proxy đang lắng nghe và chấp nhận kết nối.
    """
    result = Signal(bool, float, str, str)

    TIMEOUT = 10.0

    def __init__(self, proxy: ParsedProxy):
        super().__init__()
        self._proxy = proxy

    def _run_tcp(self, t0: float):
        """Kết nối TCP trực tiếp tới host:port của proxy (giống proxy.py)."""
        p = self._proxy
        try:
            with socket.create_connection((p.host, p.port), timeout=self.TIMEOUT) as sock:
                elapsed = (time.monotonic() - t0) * 1000
                peer_ip = sock.getpeername()[0]
                self.result.emit(True, elapsed, peer_ip, "")
        except socket.timeout:
            self.result.emit(False, (time.monotonic() - t0) * 1000, "", "Timed out")
        except ConnectionRefusedError:
            self.result.emit(False, (time.monotonic() - t0) * 1000, "", "Connection refused")
        except OSError as exc:
            self.result.emit(False, (time.monotonic() - t0) * 1000, "", str(exc))
        except Exception as exc:
            self.result.emit(False, (time.monotonic() - t0) * 1000, "", str(exc))

    def run(self):
        t0 = time.monotonic()
        self._run_tcp(t0)

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

class PingModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ping & Port Check")
        self.setModal(True)
        self.setFixedWidth(480)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._port_thread:  QThread | None = None
        self._port_worker:  PortCheckWorker | None = None
        self._proxy_thread: QThread | None = None
        self._proxy_worker: ProxyPingWorker | None = None

        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width()  // 2,
            screen.center().y() - self.height() // 2,
        )

    def _build_ui(self):
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
        layout.setSpacing(14)

        # ── Header ───────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("🏓  Ping & Port Check")
        title.setStyleSheet(
            f"color: {PALETTE['text']}; font-size: 11pt; font-weight: 700; background: transparent;"
        )
        hdr.addWidget(title)
        hdr.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {PALETTE['subtext']}; "
            f"border: none; font-size: 11pt; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {PALETTE['error']}; color: #fff; }}"
        )
        close_btn.clicked.connect(self.close)
        hdr.addWidget(close_btn)
        layout.addLayout(hdr)

        layout.addWidget(_separator())

        # ── Port check ───────────────────────────────────────────────────────
        layout.addWidget(self._section("🔌  TCP Port Check"))
        port_desc = QLabel(
            "Enter <b>host:port</b> (e.g., <code>8.8.8.8:53</code>) or just <b>port</b> "
            "to check direct TCP connection."
        )
        port_desc.setWordWrap(True)
        port_desc.setStyleSheet(f"color: {PALETTE['subtext']}; font-size: 8pt; background: transparent;")
        layout.addWidget(port_desc)

        port_row = QHBoxLayout()
        port_row.setSpacing(8)
        self._port_input = QLineEdit()
        self._port_input.setPlaceholderText("host:port hoặc port")
        self._port_input.setFixedHeight(34)
        self._port_input.returnPressed.connect(self._run_port_check)
        port_row.addWidget(self._port_input, 1)
        self._port_btn = QPushButton("Check")
        self._port_btn.setFixedHeight(34)
        self._port_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._port_btn.setStyleSheet(_small_btn_style(accent=True))
        self._port_btn.clicked.connect(self._run_port_check)
        port_row.addWidget(self._port_btn)
        layout.addLayout(port_row)

        self._port_result = QLabel("")
        self._port_result.setWordWrap(True)
        self._port_result.setMinimumHeight(20)
        self._port_result.setStyleSheet(f"color: {PALETTE['subtext']}; font-size: 9pt; background: transparent;")
        layout.addWidget(self._port_result)

        layout.addWidget(_separator())

        layout.addWidget(self._section("🌐  Ping Proxy"))

        proxy_desc = QLabel(
            "Enter a proxy in <b>any format</b>. "
            "Select the default protocol if the string does not have a scheme."
        )
        proxy_desc.setWordWrap(True)
        proxy_desc.setStyleSheet(f"color: {PALETTE['subtext']}; font-size: 8pt; background: transparent;")
        layout.addWidget(proxy_desc)

        fmt_hint = QLabel(
            "<code>host:port</code>  ·  "
            "<code>user:pass@host:port</code>  ·  "
            "<code>socks5://host:port</code>  ·  "
            "<code>socks5://user:pass@host:port</code>  ·  "
            "<code>http://user:pass@host:port</code>"
        )
        fmt_hint.setWordWrap(True)
        fmt_hint.setStyleSheet(f"color: {PALETTE['accent2']}; font-size: 7.5pt; background: transparent;")
        layout.addWidget(fmt_hint)

        proxy_row = QHBoxLayout()
        proxy_row.setSpacing(8)

        self._proto_combo = QComboBox()
        self._proto_combo.addItems(["HTTP", "HTTPS", "SOCKS5", "SOCKS4"])
        self._proto_combo.setFixedHeight(34)
        self._proto_combo.setFixedWidth(96)
        self._proto_combo.setToolTip(
            "Default protocol — only applies when the proxy string has no scheme"
        )
        proxy_row.addWidget(self._proto_combo)

        self._proxy_input = QLineEdit()
        self._proxy_input.setPlaceholderText(
            "host:port  /  user:pass@host:port  /  socks5://user:pass@host:port"
        )
        self._proxy_input.setFixedHeight(34)
        self._proxy_input.returnPressed.connect(self._run_proxy_ping)
        proxy_row.addWidget(self._proxy_input, 1)

        self._proxy_btn = QPushButton("Ping")
        self._proxy_btn.setFixedHeight(34)
        self._proxy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._proxy_btn.setStyleSheet(_small_btn_style(accent=True))
        self._proxy_btn.clicked.connect(self._run_proxy_ping)
        proxy_row.addWidget(self._proxy_btn)
        layout.addLayout(proxy_row)

        self._proxy_result = QLabel("")
        self._proxy_result.setWordWrap(True)
        self._proxy_result.setMinimumHeight(20)
        self._proxy_result.setStyleSheet(f"color: {PALETTE['subtext']}; font-size: 9pt; background: transparent;")
        layout.addWidget(self._proxy_result)

    @staticmethod
    def _section(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {PALETTE['accent2']}; font-size: 9pt; font-weight: 700; background: transparent;"
        )
        return lbl

    def _warn(self, label: QLabel, msg: str):
        label.setText(msg)
        label.setStyleSheet(f"color: {PALETTE['warning']}; font-size: 9pt; background: transparent;")

    def _run_port_check(self):
        raw = self._port_input.text().strip()
        if not raw:
            self._warn(self._port_result, "⚠ Please enter host:port or a port number.")
            return

        if ":" in raw:
            parts = raw.rsplit(":", 1)
            host, port_str = parts[0].strip(), parts[1].strip()
        else:
            host, port_str = current_ipv4(), raw

        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            self._warn(self._port_result, "⚠  Invalid port number (1–65535).")
            return

        self._port_btn.setEnabled(False)
        self._port_result.setStyleSheet(f"color: {PALETTE['subtext']}; font-size: 9pt; background: transparent;")
        self._port_result.setText(f"⏳ Checking {host}:{port} …")

        self._port_thread = QThread()
        self._port_worker = PortCheckWorker(host, port)
        self._port_worker.moveToThread(self._port_thread)
        self._port_thread.started.connect(self._port_worker.run)
        self._port_worker.result.connect(self._on_port_result)
        self._port_worker.result.connect(self._port_thread.quit)
        self._port_thread.finished.connect(self._port_thread.deleteLater)
        self._port_thread.start()

    def _on_port_result(self, connected: bool, elapsed_ms: float,
                        error: str, resolved_ip: str):
        self._port_btn.setEnabled(True)
        addr = self._port_input.text().strip()
        if connected:
            ip_part = f"IP: {resolved_ip}" if resolved_ip else ""
            self._port_result.setText(
                f"✅ Connected · {ip_part}({elapsed_ms:.0f} ms)"
            )
            self._port_result.setStyleSheet(_result_style(True))
        else:
            detail = f"  ({error})" if error else ""
            self._port_result.setText(f"❌ Cannot connect  —  {addr}{detail}")
            self._port_result.setStyleSheet(_result_style(False))

    def _run_proxy_ping(self):
        raw = self._proxy_input.text().strip()
        if not raw:
            self._warn(self._proxy_result, "⚠ Please enter a proxy address.")
            return

        default_proto = self._proto_combo.currentText().lower()
        proxy = parse_proxy(raw, default_protocol=default_proto)
        if proxy is None:
            self._warn(
                self._proxy_result,
                "⚠ Invalid format.\n"
                "Example:  1.2.3.4:8080  ·  user:pass@1.2.3.4:1080  ·  socks5://1.2.3.4:1080",
            )
            return

        self._proxy_btn.setEnabled(False)
        self._proxy_result.setStyleSheet(f"color: {PALETTE['subtext']}; font-size: 9pt; background: transparent;")
        self._proxy_result.setText(f"⏳ Pinging {proxy.display} …")

        self._proxy_thread = QThread()
        self._proxy_worker = ProxyPingWorker(proxy)
        self._proxy_worker.moveToThread(self._proxy_thread)
        self._proxy_thread.started.connect(self._proxy_worker.run)
        self._proxy_worker.result.connect(self._on_proxy_result)
        self._proxy_worker.result.connect(self._proxy_thread.quit)
        self._proxy_thread.finished.connect(self._proxy_thread.deleteLater)
        self._proxy_thread.start()

    def _on_proxy_result(self, alive: bool, elapsed_ms: float,
                         origin_ip: str, error: str):
        self._proxy_btn.setEnabled(True)
        raw   = self._proxy_input.text().strip()
        proto = self._proto_combo.currentText().lower()
        proxy = parse_proxy(raw, default_protocol=proto)
        label = proxy.display if proxy else raw

        if alive:
            ip_part = f"  ·  origin IP: {origin_ip}" if origin_ip else ""
            self._proxy_result.setText(
                f"✅ Alive  —  {label}  responded in {elapsed_ms:.0f} ms{ip_part}"
            )
            self._proxy_result.setStyleSheet(_result_style(True))
        else:
            detail = f"  ({error})" if error else ""
            timing = f"  (after {elapsed_ms:.0f} ms)" if elapsed_ms > 0 else ""
            self._proxy_result.setText(
                f"❌ Dead  —  {label}  no response{timing}{detail}"
            )
            self._proxy_result.setStyleSheet(_result_style(False))

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
