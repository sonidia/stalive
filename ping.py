from __future__ import annotations

import re, socket, time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextFormat
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget, QFrame, QComboBox,
    QPlainTextEdit, QTabWidget, QTextEdit,
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

def _parse_port_range(raw: str) -> list[int]:
    ports: set[int] = set()
    for part in re.split(r"[,;\s]+", raw):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start, end = int(start_str), int(end_str)
            if start > end:
                start, end = end, start
            ports.update(range(max(1, start), min(65535, end) + 1))
        else:
            port = int(part)
            if 1 <= port <= 65535:
                ports.add(port)
    return sorted(ports)

class LinkedPlainTextEdit(QPlainTextEdit):
    line_hovered = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._highlight_line = -1

    def mouseMoveEvent(self, event):
        cursor = self.cursorForPosition(event.position().toPoint())
        line = cursor.blockNumber()
        if line != self._highlight_line:
            self.line_hovered.emit(line)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
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
    alive = result.get("alive")
    if alive is None:
        status = "⏳ pending"
    else:
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

def _format_port_result_line(result: dict) -> str:
    index = int(result.get("index", 0) or 0)
    prefix = f"{index:02d}" if index else "--"
    target = _value_or_dash(result.get("target"))
    elapsed = result.get("elapsed_ms", 0.0) or 0.0
    speed = f"{elapsed:.0f} ms" if elapsed > 0 else "-"
    if result.get("alive"):
        peer = _value_or_dash(result.get("peer_ip"))
        return f"{prefix} ✅ open | speed {speed} | {target} | peer {peer}"
    return f"{prefix} ❌ closed | speed {speed} | {target} | info {_value_or_dash(result.get('error'))}"

class PortBatchWorker(QObject):
    item_result = Signal(dict)
    progress = Signal(int, int)
    finished = Signal()

    def __init__(
        self,
        targets: list[str],
        timeout: float = 5.0,
        max_workers: int = 64,
        emit_closed: bool = True,
    ):
        super().__init__()
        self._targets = targets
        self._timeout = timeout
        self._max_workers = max(1, max_workers)
        self._emit_closed = emit_closed

    def _check_one(self, idx: int, raw: str) -> dict:
        label, host, port, error = _parse_port_target(raw)
        if error:
            return {
                "index": idx,
                "target": label,
                "alive": False,
                "elapsed_ms": 0.0,
                "error": error,
                "peer_ip": "",
            }
        ok, elapsed, err, peer_ip = _check_tcp(host, port, self._timeout)
        return {
            "index": idx,
            "target": label,
            "alive": ok,
            "elapsed_ms": elapsed,
            "error": err,
            "peer_ip": peer_ip,
        }

    def run(self):
        total = len(self._targets)
        done = 0
        with ThreadPoolExecutor(max_workers=min(self._max_workers, max(1, total))) as executor:
            futures = [
                executor.submit(self._check_one, idx, raw)
                for idx, raw in enumerate(self._targets, start=1)
            ]
            for future in as_completed(futures):
                result = future.result()
                done += 1
                if self._emit_closed or result.get("alive"):
                    self.item_result.emit(result)
                self.progress.emit(done, total)
        self.finished.emit()

class ProxyPingBatchWorker(QObject):
    item_result = Signal(dict)
    progress = Signal(int, int)
    finished = Signal()

    def __init__(self, entries: list[str], default_protocol: str, max_workers: int = 16):
        super().__init__()
        self._entries = entries
        self._default_protocol = default_protocol
        self._max_workers = max(1, max_workers)

    def _probe_one(self, idx: int, raw: str) -> dict:
        proxy = parse_proxy(raw, default_protocol=self._default_protocol)
        if proxy is None:
            return {
                "index": idx,
                "label": raw,
                "alive": False,
                "elapsed_ms": 0.0,
                "error": "Invalid proxy format",
            }
        result = _probe_proxy(proxy)
        result["index"] = idx
        return result

    def run(self):
        total = len(self._entries)
        done = 0
        with ThreadPoolExecutor(max_workers=min(self._max_workers, max(1, total))) as executor:
            futures = [
                executor.submit(self._probe_one, idx, raw)
                for idx, raw in enumerate(self._entries, start=1)
            ]
            for future in as_completed(futures):
                done += 1
                self.item_result.emit(future.result())
                self.progress.emit(done, total)
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

    if show_close_button:
        hdr = QHBoxLayout()
        title = QLabel(title_text)
        title.setObjectName("toolTitle")
        hdr.addWidget(title)
        hdr.addStretch()
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
        self._port_mode = "check"
        self._scan_found_count = 0

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

        scan_row = QHBoxLayout()
        scan_row.setSpacing(8)
        self._scan_range_edit = QLineEdit("1-1024")
        self._scan_range_edit.setPlaceholderText("Port range: 1-1024,2000,3000-3010")
        self._scan_range_edit.setFixedHeight(26)
        scan_row.addWidget(self._scan_range_edit, 1)
        self._scan_btn = QPushButton("🔎 Scan host ports")
        self._scan_btn.setFixedHeight(26)
        self._scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._scan_btn.setStyleSheet(_small_btn_style(accent=True))
        self._scan_btn.clicked.connect(self._run_host_scan)
        scan_row.addWidget(self._scan_btn)
        layout.addLayout(scan_row)

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
        self._port_mode = "check"
        self._scan_found_count = 0
        self._port_btn.setEnabled(False)
        self._scan_btn.setEnabled(False)
        self._port_clear_btn.setEnabled(False)
        self._port_summary.setText(f"Checking 0/{len(targets)} targets...")

        self._port_thread = QThread()
        self._port_worker = PortBatchWorker(targets, timeout=5.0, max_workers=64)
        self._port_worker.moveToThread(self._port_thread)
        self._port_thread.started.connect(self._port_worker.run)
        self._port_worker.item_result.connect(self._on_port_item_result)
        self._port_worker.progress.connect(self._on_port_progress)
        self._port_worker.finished.connect(self._on_port_batch_finished)
        self._port_worker.finished.connect(self._port_thread.quit)
        self._port_worker.finished.connect(self._port_worker.deleteLater)
        self._port_thread.finished.connect(self._port_thread.deleteLater)
        self._port_thread.start()

    def _run_host_scan(self):
        try:
            ports = _parse_port_range(self._scan_range_edit.text() or "1-1024")
        except ValueError:
            self._port_result.setPlainText("⚠ Invalid port range.")
            self._port_summary.setText("Invalid scan range")
            return

        if not ports:
            self._port_result.setPlainText("⚠ No ports to scan.")
            self._port_summary.setText("No ports")
            return

        host = current_ipv4() or "127.0.0.1"
        targets = [f"{host}:{port}" for port in ports]
        self._port_result.clear()
        self._port_mode = "scan"
        self._scan_found_count = 0
        self._port_btn.setEnabled(False)
        self._scan_btn.setEnabled(False)
        self._port_clear_btn.setEnabled(False)
        self._port_summary.setText(f"Scanning {host} · 0/{len(targets)} ports...")

        self._port_thread = QThread()
        self._port_worker = PortBatchWorker(
            targets,
            timeout=0.25,
            max_workers=256,
            emit_closed=False,
        )
        self._port_worker.moveToThread(self._port_thread)
        self._port_thread.started.connect(self._port_worker.run)
        self._port_worker.item_result.connect(self._on_port_item_result)
        self._port_worker.progress.connect(self._on_port_progress)
        self._port_worker.finished.connect(self._on_port_batch_finished)
        self._port_worker.finished.connect(self._port_thread.quit)
        self._port_worker.finished.connect(self._port_worker.deleteLater)
        self._port_thread.finished.connect(self._port_thread.deleteLater)
        self._port_thread.start()

    def _on_port_item_result(self, result: dict):
        if self._port_mode == "scan" and result.get("alive"):
            self._scan_found_count += 1
        self._port_result.appendPlainText(_format_port_result_line(result))

    def _on_port_progress(self, done: int, total: int):
        if self._port_mode == "scan":
            self._port_summary.setText(
                f"Scanning {done}/{total} ports · open {self._scan_found_count}"
            )
        else:
            self._port_summary.setText(f"Checking {done}/{total} targets...")

    def _on_port_batch_finished(self):
        self._port_btn.setEnabled(True)
        self._scan_btn.setEnabled(True)
        self._port_clear_btn.setEnabled(True)
        if self._port_mode == "scan":
            if self._scan_found_count == 0:
                self._port_result.appendPlainText("No open ports found.")
            self._port_summary.setText(f"Done · open {self._scan_found_count}")
        else:
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
        self._proxy_entries: list[str] = []
        self._proxy_results: dict[int, dict] = {}
        self._proxy_visible_indexes: list[int] = []

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
        self._proxy_input = LinkedPlainTextEdit()
        self._proxy_input.setObjectName("toolTextArea")
        self._proxy_input.setPlaceholderText(
            "host:port\nuser:pass@host:port\nsocks5://user:pass@host:port"
        )
        self._proxy_input.setMinimumHeight(250)
        self._proxy_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self._proxy_result = LinkedPlainTextEdit()
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
        self._proxy_input.line_hovered.connect(self._on_proxy_input_hover)
        self._proxy_result.line_hovered.connect(self._on_proxy_result_hover)

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

        self._proxy_paste_btn = QPushButton("📋 Paste")
        self._proxy_paste_btn.setFixedHeight(26)
        self._proxy_paste_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._proxy_paste_btn.setStyleSheet(_small_btn_style())
        self._proxy_paste_btn.clicked.connect(self._paste_proxy_clipboard)
        action_row.addWidget(self._proxy_paste_btn)

        self._proxy_import_btn = QPushButton("📄 Import .txt")
        self._proxy_import_btn.setFixedHeight(26)
        self._proxy_import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._proxy_import_btn.setStyleSheet(_small_btn_style())
        self._proxy_import_btn.clicked.connect(self._import_proxy_file)
        action_row.addWidget(self._proxy_import_btn)

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

        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self._proxy_stats_lbl = QLabel("Stats: total 0 · done 0 · alive 0 · dead 0")
        self._proxy_stats_lbl.setObjectName("toolHint")
        stats_row.addWidget(self._proxy_stats_lbl, 1)

        self._proxy_filter_combo = QComboBox()
        self._proxy_filter_combo.addItems(["All", "Alive", "Dead"])
        self._proxy_filter_combo.setFixedHeight(26)
        self._proxy_filter_combo.currentTextChanged.connect(lambda _text: self._refresh_proxy_results_view())
        stats_row.addWidget(self._proxy_filter_combo)

        self._proxy_sort_combo = QComboBox()
        self._proxy_sort_combo.addItems(["Input order", "Speed ↑", "Speed ↓", "Status", "Location"])
        self._proxy_sort_combo.setFixedHeight(26)
        self._proxy_sort_combo.currentTextChanged.connect(lambda _text: self._refresh_proxy_results_view())
        stats_row.addWidget(self._proxy_sort_combo)
        layout.addLayout(stats_row)
        if not self._show_close_button:
            outer.addStretch(1)

    def _paste_proxy_clipboard(self):
        text = QApplication.clipboard().text().strip()
        if not text:
            return
        if self._proxy_input.toPlainText().strip():
            self._proxy_input.insertPlainText("\n" + text)
        else:
            self._proxy_input.setPlainText(text)

    def _import_proxy_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import proxy list",
            "",
            "Text files (*.txt);;All files (*.*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
                text = fh.read()
        if text.strip():
            self._proxy_input.setPlainText(text.strip())

    def _clear_proxy_results(self):
        self._proxy_result.clear()
        self._proxy_results.clear()
        self._proxy_visible_indexes.clear()
        self._proxy_summary.setText("Ready")
        self._update_proxy_stats()

    def _run_proxy_ping(self):
        entries = _split_batch_text(self._proxy_input.toPlainText())
        if not entries:
            self._proxy_result.setPlainText("⚠ Please enter at least one proxy address.")
            self._proxy_summary.setText("No proxies")
            return

        default_proto = self._proto_combo.currentText().lower()
        self._proxy_entries = entries
        self._proxy_results = {
            idx: {
                "index": idx,
                "label": raw,
                "alive": None,
                "elapsed_ms": 0.0,
                "info": "Waiting",
            }
            for idx, raw in enumerate(entries, start=1)
        }
        self._refresh_proxy_results_view()
        self._proxy_btn.setEnabled(False)
        self._proxy_clear_btn.setEnabled(False)
        self._proxy_paste_btn.setEnabled(False)
        self._proxy_import_btn.setEnabled(False)
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
        idx = int(result.get("index", 0) or 0)
        if idx:
            self._proxy_results[idx] = result
        self._refresh_proxy_results_view()

    def _on_proxy_progress(self, done: int, total: int):
        self._proxy_summary.setText(f"Pinging {done}/{total} proxies...")

    def _on_proxy_batch_finished(self):
        self._proxy_btn.setEnabled(True)
        self._proxy_clear_btn.setEnabled(True)
        self._proxy_paste_btn.setEnabled(True)
        self._proxy_import_btn.setEnabled(True)
        self._proxy_summary.setText("Done")
        self._refresh_proxy_results_view()

    def _filtered_proxy_results(self) -> list[dict]:
        results = list(self._proxy_results.values())
        filter_mode = self._proxy_filter_combo.currentText()
        if filter_mode == "Alive":
            results = [item for item in results if item.get("alive") is True]
        elif filter_mode == "Dead":
            results = [item for item in results if item.get("alive") is False]

        sort_mode = self._proxy_sort_combo.currentText()
        if sort_mode == "Speed ↑":
            results.sort(key=lambda item: item.get("elapsed_ms", 0.0) or 10**9)
        elif sort_mode == "Speed ↓":
            results.sort(key=lambda item: item.get("elapsed_ms", 0.0) or -1, reverse=True)
        elif sort_mode == "Status":
            results.sort(key=lambda item: (item.get("alive") is not True, item.get("index", 0)))
        elif sort_mode == "Location":
            results.sort(key=lambda item: (_proxy_location(item), item.get("index", 0)))
        else:
            results.sort(key=lambda item: item.get("index", 0))
        return results

    def _refresh_proxy_results_view(self):
        results = self._filtered_proxy_results()
        self._proxy_visible_indexes = [int(item.get("index", 0) or 0) for item in results]
        self._proxy_result.setPlainText("\n".join(_format_proxy_result_line(item) for item in results))
        self._update_proxy_stats()

    def _update_proxy_stats(self):
        total = len(self._proxy_results)
        done = sum(1 for item in self._proxy_results.values() if item.get("alive") is not None)
        alive = sum(1 for item in self._proxy_results.values() if item.get("alive") is True)
        dead = sum(1 for item in self._proxy_results.values() if item.get("alive") is False)
        speeds = [
            item.get("elapsed_ms", 0.0)
            for item in self._proxy_results.values()
            if item.get("alive") is True and item.get("elapsed_ms", 0.0) > 0
        ]
        avg = sum(speeds) / len(speeds) if speeds else 0.0
        avg_text = f" · avg {avg:.0f} ms" if avg else ""
        visible = len(self._proxy_visible_indexes)
        self._proxy_stats_lbl.setText(
            f"Stats: total {total} · done {done} · alive {alive} · dead {dead} · visible {visible}{avg_text}"
        )

    def _on_proxy_input_hover(self, input_line: int):
        self._proxy_input.set_highlight_line(input_line)
        result_line = -1
        input_index = input_line + 1
        if input_index in self._proxy_visible_indexes:
            result_line = self._proxy_visible_indexes.index(input_index)
        self._proxy_result.set_highlight_line(result_line)

    def _on_proxy_result_hover(self, result_line: int):
        self._proxy_result.set_highlight_line(result_line)
        input_line = -1
        if 0 <= result_line < len(self._proxy_visible_indexes):
            input_line = self._proxy_visible_indexes[result_line] - 1
        self._proxy_input.set_highlight_line(input_line)

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
