from __future__ import annotations

import re, socket, time
import requests

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout, QWidget, QFrame, QComboBox,
    QPlainTextEdit, QTabWidget,
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

PROXY_PING_TIMEOUT = 10.0
PROXY_TEST_URL = "http://httpbin.org/ip"
PROXY_GEO_URL = (
    "http://ip-api.com/json/{ip}"
    "?fields=status,message,country,countryCode,regionName,city,isp,org,as,timezone,query"
)

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

def _split_batch_text(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[\n,;]+", text) if part.strip()]

def _parse_port_target(raw: str) -> tuple[str, str, int, str | None]:
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
        return raw, "", 0, "Invalid port number (1-65535)"

    if not host:
        return raw, "", 0, "Missing host"

    return f"{host}:{port}", host, port, None

def _check_tcp(host: str, port: int, timeout: float) -> tuple[bool, float, str, str]:
    t0 = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            elapsed = (time.monotonic() - t0) * 1000
            return True, elapsed, "", sock.getpeername()[0]
    except socket.timeout:
        return False, (time.monotonic() - t0) * 1000, "Timed out", ""
    except ConnectionRefusedError:
        return False, (time.monotonic() - t0) * 1000, "Connection refused", ""
    except OSError as exc:
        return False, (time.monotonic() - t0) * 1000, str(exc), ""
    except Exception as exc:
        return False, (time.monotonic() - t0) * 1000, str(exc), ""

def _proxy_url(proxy: ParsedProxy) -> str:
    auth = ""
    if proxy.username:
        auth = f"{proxy.username}:{proxy.password}@"
    return f"{proxy.protocol}://{auth}{proxy.host}:{proxy.port}"

def _origin_ip_from_response(resp: requests.Response) -> str:
    try:
        origin = str(resp.json().get("origin", "")).strip()
    except Exception:
        return ""
    if "," in origin:
        origin = origin.split(",", 1)[0].strip()
    return origin

def _lookup_ip_geo(ip: str) -> dict:
    if not ip:
        return {}
    try:
        resp = requests.get(PROXY_GEO_URL.format(ip=ip), timeout=PROXY_PING_TIMEOUT)
        if resp.status_code != 200:
            return {}
        geo = resp.json()
        if geo.get("status") != "success":
            return {"geo_error": geo.get("message", "Geo lookup failed")}
        return geo
    except Exception as exc:
        return {"geo_error": str(exc)}

def _probe_proxy(proxy: ParsedProxy) -> dict:
    url = _proxy_url(proxy)
    proxies = {"http": url, "https": url}
    t0 = time.monotonic()
    try:
        resp = requests.get(PROXY_TEST_URL, proxies=proxies, timeout=PROXY_PING_TIMEOUT)
        elapsed = (time.monotonic() - t0) * 1000
    except Exception as exc:
        return {
            "label": proxy.display,
            "alive": False,
            "elapsed_ms": (time.monotonic() - t0) * 1000,
            "error": str(exc),
        }

    if resp.status_code != 200:
        return {
            "label": proxy.display,
            "alive": False,
            "elapsed_ms": elapsed,
            "error": f"HTTP {resp.status_code}",
        }

    response_ip = _origin_ip_from_response(resp)
    if not response_ip:
        return {
            "label": proxy.display,
            "alive": False,
            "elapsed_ms": elapsed,
            "error": "No response IP",
        }

    geo = _lookup_ip_geo(response_ip)
    return {
        "label": proxy.display,
        "alive": True,
        "elapsed_ms": elapsed,
        "response_ip": response_ip,
        "country": geo.get("country", ""),
        "country_code": geo.get("countryCode", ""),
        "region": geo.get("regionName", ""),
        "city": geo.get("city", ""),
        "asn": geo.get("as", ""),
        "isp": geo.get("isp", ""),
        "org": geo.get("org", ""),
        "timezone": geo.get("timezone", ""),
        "info": geo.get("geo_error", "OK"),
    }

def _value_or_dash(value) -> str:
    text = str(value or "").strip()
    return text if text else "-"

def _proxy_location(result: dict) -> str:
    country = str(result.get("country", "")).strip()
    country_code = str(result.get("country_code", "")).strip()
    if country and country_code:
        country_label = f"{country} ({country_code})"
    else:
        country_label = country or country_code
    parts = [
        str(result.get("city", "")).strip(),
        str(result.get("region", "")).strip(),
        country_label,
    ]
    return ", ".join(part for part in parts if part) or "-"

def _format_proxy_result_line(result: dict) -> str:
    index = int(result.get("index", 0) or 0)
    prefix = f"{index:02d}" if index else "--"
    alive = bool(result.get("alive"))
    status = "✅ alive" if alive else "❌ dead"
    elapsed = result.get("elapsed_ms", 0.0) or 0.0
    speed = f"{elapsed:.0f} ms" if elapsed > 0 else "-"
    label = _value_or_dash(result.get("label"))
    response_ip = _value_or_dash(result.get("response_ip"))
    asn = _value_or_dash(result.get("asn"))
    isp = _value_or_dash(result.get("isp") or result.get("org"))
    timezone = _value_or_dash(result.get("timezone"))
    info = _value_or_dash(result.get("info") if alive else result.get("error"))
    return (
        f"{prefix} {status} | speed {speed} | {label} | "
        f"IP response {response_ip} | location {_proxy_location(result)} | "
        f"ASN {asn} | ISP {isp} | timezone {timezone} | info {info}"
    )

class PortBatchWorker(QObject):
    item_result = Signal(str, bool, float, str, str)  # target, ok, ms, error, peer_ip
    progress = Signal(int, int)
    finished = Signal()

    def __init__(self, targets: list[str], timeout: float = 5.0):
        super().__init__()
        self._targets = targets
        self._timeout = timeout

    def run(self):
        total = len(self._targets)
        for idx, raw in enumerate(self._targets, start=1):
            label, host, port, error = _parse_port_target(raw)
            if error:
                self.item_result.emit(label, False, 0.0, error, "")
            else:
                ok, elapsed, err, peer_ip = _check_tcp(host, port, self._timeout)
                self.item_result.emit(label, ok, elapsed, err, peer_ip)
            self.progress.emit(idx, total)
        self.finished.emit()

class ProxyPingBatchWorker(QObject):
    item_result = Signal(dict)
    progress = Signal(int, int)
    finished = Signal()

    def __init__(self, entries: list[str], default_protocol: str):
        super().__init__()
        self._entries = entries
        self._default_protocol = default_protocol

    def run(self):
        total = len(self._entries)
        for idx, raw in enumerate(self._entries, start=1):
            proxy = parse_proxy(raw, default_protocol=self._default_protocol)
            if proxy is None:
                self.item_result.emit({
                    "index": idx,
                    "label": raw,
                    "alive": False,
                    "elapsed_ms": 0.0,
                    "error": "Invalid proxy format",
                })
            else:
                result = _probe_proxy(proxy)
                result["index"] = idx
                self.item_result.emit(result)
            self.progress.emit(idx, total)
        self.finished.emit()

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
        f"border: 1px solid {border}; border-radius: 6px; "
        f"padding: 5px 12px; font-size: 8pt; font-weight: 700; }}"
        f"QPushButton:hover {{ background: {hv}; color: #fff; border-color: {hv}; }}"
        f"QPushButton:pressed {{ background: {PALETTE['accent']}; color: #fff; }}"
        f"QPushButton:disabled {{ opacity: 0.45; }}"
    )

def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {PALETTE['border']}; margin: 6px 0;")
    return line

def _build_tool_shell(
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

    hdr = QHBoxLayout()
    title = QLabel(title_text)
    title.setObjectName("toolTitle")
    hdr.addWidget(title)
    hdr.addStretch()
    if show_close_button:
        close_btn = QPushButton("✕")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {PALETTE['subtext']}; "
            f"border: none; font-size: 10pt; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {PALETTE['error']}; color: #fff; }}"
        )
        close_btn.clicked.connect(close_handler or widget.close)
        hdr.addWidget(close_btn)
    outer.addLayout(hdr)
    outer.addWidget(_separator())
    return outer, outer

def _section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("toolSection")
    return lbl

class CheckPortTab(QWidget):
    def __init__(
        self,
        parent=None,
        show_close_button: bool = False,
        close_handler=None,
        outer_margins: tuple[int, int, int, int] = (2, 14, 2, 16),
    ):
        super().__init__(parent)
        self._show_close_button = show_close_button
        self._close_handler = close_handler
        self._outer_margins = outer_margins

        self._port_thread: QThread | None = None
        self._port_worker: PortBatchWorker | None = None

        self._build_ui()

    def _build_ui(self):
        outer, layout = _build_tool_shell(
            self,
            "Check port",
            self._show_close_button,
            self._close_handler,
            self._outer_margins,
        )
        layout.addWidget(_section("TCP connection"))

        port_desc = QLabel(
            "Enter one target per line. Use <b>host:port</b> or just <b>port</b> "
            "to check against this machine's current IPv4."
        )
        port_desc.setWordWrap(True)
        port_desc.setObjectName("toolHint")
        layout.addWidget(port_desc)

        self._port_input = QPlainTextEdit()
        self._port_input.setObjectName("toolTextArea")
        self._port_input.setPlaceholderText("8.8.8.8:53\n1.1.1.1:443\n2000")
        self._port_input.setMinimumHeight(92)
        self._port_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._port_input)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        action_row.addStretch()
        self._port_clear_btn = QPushButton("✕ Clear")
        self._port_clear_btn.setFixedHeight(26)
        self._port_clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._port_clear_btn.setStyleSheet(_small_btn_style())
        self._port_clear_btn.clicked.connect(self._clear_port_results)
        action_row.addWidget(self._port_clear_btn)

        self._port_btn = QPushButton("⚡ Check all")
        self._port_btn.setFixedHeight(26)
        self._port_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._port_btn.setStyleSheet(_small_btn_style(accent=True))
        self._port_btn.clicked.connect(self._run_port_check)
        action_row.addWidget(self._port_btn)
        layout.addLayout(action_row)

        self._port_summary = QLabel("Ready")
        self._port_summary.setObjectName("toolHint")
        layout.addWidget(self._port_summary)

        self._port_result = QPlainTextEdit()
        self._port_result.setObjectName("toolOutput")
        self._port_result.setReadOnly(True)
        self._port_result.setMinimumHeight(150)
        self._port_result.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._port_result.setPlaceholderText("Results will appear here.")
        layout.addWidget(self._port_result)
        if not self._show_close_button:
            outer.addStretch(1)

    def _clear_port_results(self):
        self._port_result.clear()
        self._port_summary.setText("Ready")

    def _run_port_check(self):
        targets = _split_batch_text(self._port_input.toPlainText())
        if not targets:
            self._port_result.setPlainText("⚠ Please enter host:port or a port number.")
            self._port_summary.setText("No targets")
            return

        self._port_result.clear()
        self._port_btn.setEnabled(False)
        self._port_clear_btn.setEnabled(False)
        self._port_summary.setText(f"Checking 0/{len(targets)} targets...")

        self._port_thread = QThread()
        self._port_worker = PortBatchWorker(targets)
        self._port_worker.moveToThread(self._port_thread)
        self._port_thread.started.connect(self._port_worker.run)
        self._port_worker.item_result.connect(self._on_port_item_result)
        self._port_worker.progress.connect(self._on_port_progress)
        self._port_worker.finished.connect(self._on_port_batch_finished)
        self._port_worker.finished.connect(self._port_thread.quit)
        self._port_worker.finished.connect(self._port_worker.deleteLater)
        self._port_thread.finished.connect(self._port_thread.deleteLater)
        self._port_thread.start()

    def _on_port_item_result(self, target: str, connected: bool, elapsed_ms: float,
                             error: str, resolved_ip: str):
        if connected:
            ip_part = f"IP: {resolved_ip}" if resolved_ip else ""
            self._port_result.appendPlainText(
                f"✅ {target} · connected · {ip_part} ({elapsed_ms:.0f} ms)"
            )
        else:
            detail = f"  ({error})" if error else ""
            self._port_result.appendPlainText(f"❌ {target} · cannot connect{detail}")

    def _on_port_progress(self, done: int, total: int):
        self._port_summary.setText(f"Checking {done}/{total} targets...")

    def _on_port_batch_finished(self):
        self._port_btn.setEnabled(True)
        self._port_clear_btn.setEnabled(True)
        self._port_summary.setText("Done")

class PingTab(QWidget):
    def __init__(
        self,
        parent=None,
        show_close_button: bool = False,
        close_handler=None,
        outer_margins: tuple[int, int, int, int] = (2, 14, 2, 16),
    ):
        super().__init__(parent)
        self._show_close_button = show_close_button
        self._close_handler = close_handler
        self._outer_margins = outer_margins

        self._proxy_thread: QThread | None = None
        self._proxy_worker: ProxyPingBatchWorker | None = None

        self._build_ui()

    def _build_ui(self):
        outer, layout = _build_tool_shell(
            self,
            "Ping",
            self._show_close_button,
            self._close_handler,
            self._outer_margins,
        )
        layout.addWidget(_section("Proxy TCP ping"))

        proxy_desc = QLabel(
            "Enter one proxy per line in <b>any format</b>. "
            "Select the default protocol if the string does not have a scheme."
        )
        proxy_desc.setWordWrap(True)
        proxy_desc.setObjectName("toolHint")
        layout.addWidget(proxy_desc)

        fmt_hint = QLabel(
            "<code>host:port</code>  ·  "
            "<code>user:pass@host:port</code>  ·  "
            "<code>socks5://host:port</code>  ·  "
            "<code>socks5://user:pass@host:port</code>  ·  "
            "<code>http://user:pass@host:port</code>"
        )
        fmt_hint.setWordWrap(True)
        fmt_hint.setObjectName("toolFormatHint")
        layout.addWidget(fmt_hint)
        self._proxy_input = QPlainTextEdit()
        self._proxy_input.setObjectName("toolTextArea")
        self._proxy_input.setPlaceholderText(
            "host:port\nuser:pass@host:port\nsocks5://user:pass@host:port"
        )
        self._proxy_input.setMinimumHeight(250)
        self._proxy_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self._proxy_result = QPlainTextEdit()
        self._proxy_result.setObjectName("toolOutput")
        self._proxy_result.setReadOnly(True)
        self._proxy_result.setMinimumHeight(250)
        self._proxy_result.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._proxy_result.setPlaceholderText("Line-by-line results will appear here.")

        io_row = QHBoxLayout()
        io_row.setSpacing(10)
        io_row.addWidget(self._proxy_input, 1)
        io_row.addWidget(self._proxy_result, 1)
        layout.addLayout(io_row, 1)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self._proto_combo = QComboBox()
        self._proto_combo.addItems(["HTTP", "HTTPS", "SOCKS5", "SOCKS4"])
        self._proto_combo.setFixedHeight(26)
        self._proto_combo.setFixedWidth(92)
        self._proto_combo.setToolTip(
            "Default protocol — only applies when the proxy string has no scheme"
        )
        action_row.addWidget(self._proto_combo)
        action_row.addStretch()

        self._proxy_clear_btn = QPushButton("✕ Clear")
        self._proxy_clear_btn.setFixedHeight(26)
        self._proxy_clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._proxy_clear_btn.setStyleSheet(_small_btn_style())
        self._proxy_clear_btn.clicked.connect(self._clear_proxy_results)
        action_row.addWidget(self._proxy_clear_btn)

        self._proxy_btn = QPushButton("📡 Ping all")
        self._proxy_btn.setFixedHeight(26)
        self._proxy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._proxy_btn.setStyleSheet(_small_btn_style(accent=True))
        self._proxy_btn.clicked.connect(self._run_proxy_ping)
        action_row.addWidget(self._proxy_btn)
        layout.addLayout(action_row)

        self._proxy_summary = QLabel("Ready")
        self._proxy_summary.setObjectName("toolHint")
        layout.addWidget(self._proxy_summary)
        if not self._show_close_button:
            outer.addStretch(1)

    def _clear_proxy_results(self):
        self._proxy_result.clear()
        self._proxy_summary.setText("Ready")

    def _run_proxy_ping(self):
        entries = _split_batch_text(self._proxy_input.toPlainText())
        if not entries:
            self._proxy_result.setPlainText("⚠ Please enter at least one proxy address.")
            self._proxy_summary.setText("No proxies")
            return

        default_proto = self._proto_combo.currentText().lower()
        self._proxy_result.clear()
        self._proxy_btn.setEnabled(False)
        self._proxy_clear_btn.setEnabled(False)
        self._proxy_summary.setText(f"Pinging 0/{len(entries)} proxies...")

        self._proxy_thread = QThread()
        self._proxy_worker = ProxyPingBatchWorker(entries, default_proto)
        self._proxy_worker.moveToThread(self._proxy_thread)
        self._proxy_thread.started.connect(self._proxy_worker.run)
        self._proxy_worker.item_result.connect(self._on_proxy_item_result)
        self._proxy_worker.progress.connect(self._on_proxy_progress)
        self._proxy_worker.finished.connect(self._on_proxy_batch_finished)
        self._proxy_worker.finished.connect(self._proxy_thread.quit)
        self._proxy_worker.finished.connect(self._proxy_worker.deleteLater)
        self._proxy_thread.finished.connect(self._proxy_thread.deleteLater)
        self._proxy_thread.start()

    def _on_proxy_item_result(self, result: dict):
        self._proxy_result.appendPlainText(_format_proxy_result_line(result))

    def _on_proxy_progress(self, done: int, total: int):
        self._proxy_summary.setText(f"Pinging {done}/{total} proxies...")

    def _on_proxy_batch_finished(self):
        self._proxy_btn.setEnabled(True)
        self._proxy_clear_btn.setEnabled(True)
        self._proxy_summary.setText("Done")

class PingModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ping & Port Check")
        self.setModal(True)
        self.setFixedWidth(480)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        tabs = QTabWidget()
        tabs.setObjectName("mainTabs")
        tabs.addTab(
            PingTab(
                parent=tabs,
                show_close_button=True,
                close_handler=self.close,
                outer_margins=(0, 8, 0, 0),
            ),
            "Ping",
        )
        tabs.addTab(
            CheckPortTab(
                parent=tabs,
                show_close_button=True,
                close_handler=self.close,
                outer_margins=(0, 8, 0, 0),
            ),
            "Check port",
        )
        layout.addWidget(tabs)

    def showEvent(self, event):
        super().showEvent(event)
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width()  // 2,
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
