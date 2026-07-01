import sys, json, requests, time, os, csv, socket, uuid, threading

from PySide6.QtCore    import Qt, Signal, QObject, QStringListModel, QThread, QRect, QPoint, QTimer
from stats import stats_collector, StatsModal
from ping import CheckPortTab, PingTab
from PySide6.QtGui     import QColor, QFont, QIcon, QTextCursor, QPainter, QTextDocument, QAbstractTextDocumentLayout, QPainterPath, QBrush, QPixmap, QPolygon, QPen
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QComboBox, QPushButton,
    QTextEdit, QFrame, QSizePolicy, QCompleter, QMessageBox,
    QScrollArea, QStyledItemDelegate, QStyleOptionViewItem, QStyle, QGraphicsBlurEffect,
    QSlider, QFileDialog, QTabWidget
)

from shared import (
    COUNTRY_DATA,
    PALETTE,
    STYLESHEET,
    toolbar_button_style,
    toolbar_search_style,
)
from utils import current_ipv4

ALL_NETWORKS = sorted({n for d in COUNTRY_DATA.values() for n in d["networks"]})
API_BASE     = "http://localhost:1998/api"

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
    _DATA_DIR = os.path.dirname(sys.executable)
else:
    _BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    _DATA_DIR   = os.path.dirname(os.path.abspath(__file__))

APP_DATA_FILE = os.path.join(_DATA_DIR, "data.json")

if getattr(sys, 'frozen', False) and not os.path.exists(APP_DATA_FILE):
    _bundled = os.path.join(sys._MEIPASS, "data.json")
    if os.path.exists(_bundled):
        import shutil
        try:
            shutil.copy2(_bundled, APP_DATA_FILE)
        except Exception:
            pass

def _load_app_data() -> dict:
    """Load the unified data file. Returns dict with keys: api_base, proxies."""
    try:
        if os.path.exists(APP_DATA_FILE):
            with open(APP_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception as e:
        print(f"Error loading app data: {e}")
    return {}

def _save_app_data(data: dict):
    """Overwrite the unified data file."""
    try:
        with open(APP_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving app data: {e}")

def load_proxies_from_file() -> list:
    """Load proxy list from unified data file. Assigns _id to any entry that lacks one."""
    try:
        data = _load_app_data()
        proxies = list(data.get("proxies", []))
        dirty = False
        for p in proxies:
            if "_id" not in p:
                p["_id"] = str(uuid.uuid4())
                dirty = True
        if dirty:
            data["proxies"] = proxies
            _save_app_data(data)
        return proxies
    except Exception as e:
        print(f"Error loading proxies: {e}")
    return []

def save_proxies_to_file(new_proxies: list):
    """Append new proxies to unified data file, avoiding duplicates."""
    try:
        data = _load_app_data()
        existing: list = data.get("proxies", [])

        existing_keys = set()
        for p in existing:
            ip   = p.get("ip", p.get("host", ""))
            port = p.get("port", "")
            existing_keys.add(f"{ip}:{port}")

        added = 0
        for p in new_proxies:
            ip   = p.get("ip", p.get("host", ""))
            port = p.get("port", "")
            key  = f"{ip}:{port}"
            if key not in existing_keys:
                # Assign a stable unique ID so delete/update can target this exact entry
                if "_id" not in p:
                    p["_id"] = str(uuid.uuid4())
                existing.append(p)
                existing_keys.add(key)
                added += 1

        data["proxies"] = existing
        _save_app_data(data)
        print(f"[Cache] Saved {added} new proxy(ies). Total: {len(existing)}. File: {APP_DATA_FILE}")
    except Exception as e:
        print(f"Error saving proxies: {e}")

def delete_proxy_from_file(proxy_id: str = "", ip: str = "", port: str = ""):
    """Remove a proxy from the unified data file.
    Matches by _id first (exact), falls back to ip:port key.
    """
    try:
        data = _load_app_data()
        proxies = data.get("proxies", [])
        if proxy_id:
            data["proxies"] = [p for p in proxies if p.get("_id", "") != proxy_id]
        else:
            key = f"{ip}:{port}"
            data["proxies"] = [
                p for p in proxies
                if f"{p.get('ip', p.get('host', ''))}:{p.get('port', '')}" != key
            ]
        _save_app_data(data)
    except Exception as e:
        print(f"Error deleting proxy: {e}")

def update_proxy_in_file(proxy_id: str = "", ip: str = "", port: str = "", updates: dict = None):
    """Update specific fields of an existing proxy entry.
    Matches by _id first (exact), falls back to ip:port key.
    """
    if updates is None:
        updates = {}
    try:
        data = _load_app_data()
        proxies = data.get("proxies", [])
        for p in proxies:
            if proxy_id and p.get("_id", "") == proxy_id:
                p.update(updates)
                break
            elif not proxy_id:
                key = f"{ip}:{port}"
                if f"{p.get('ip', p.get('host', ''))}:{p.get('port', '')}" == key:
                    p.update(updates)
                    break
        data["proxies"] = proxies
        _save_app_data(data)
    except Exception as e:
        print(f"Error updating proxy: {e}")

# ─── Country Flags ─────────────────────────────────────────────────────────────
def flag_emoji(code: str) -> str:
    """Convert a 2-letter ISO country code to its flag emoji (e.g. 'US' → '🇺🇸')."""
    code = str(code).upper().strip()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord('A')) for c in code)


def make_flag_pixmap(country_code: str, width: int = 22, height: int = 14) -> QPixmap:
    """Render a country flag as a QPixmap using the built-in painter logic."""
    pix = QPixmap(width, height)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    r = QRect(0, 0, width, height)

    if country_code == "US":
        painter.fillRect(r, QColor("#B22234"))
        stripe_h = max(1, height // 13)
        for i in range(7):
            painter.fillRect(QRect(0, i * 2 * stripe_h, width, stripe_h), QColor("#FFFFFF"))
        painter.fillRect(QRect(0, 0, width * 2 // 5, height * 7 // 13), QColor("#3C3B6E"))

    elif country_code == "GB":
        painter.fillRect(r, QColor("#012169"))
        bw, bh = width // 2 - 2, height // 2 - 2
        painter.fillRect(QRect(width // 2 - 2, 0, 4, height), QColor("#FFFFFF"))
        painter.fillRect(QRect(0, height // 2 - 2, width, 4), QColor("#FFFFFF"))
        painter.fillRect(QRect(width // 2 - 1, 0, 2, height), QColor("#C8102E"))
        painter.fillRect(QRect(0, height // 2 - 1, width, 2), QColor("#C8102E"))

    elif country_code == "DE":
        h3 = height // 3
        painter.fillRect(QRect(0, 0,      width, h3     ), QColor("#000000"))
        painter.fillRect(QRect(0, h3,     width, h3     ), QColor("#DD0000"))
        painter.fillRect(QRect(0, h3 * 2, width, height - h3 * 2), QColor("#FFCC00"))

    elif country_code == "FR":
        w3 = width // 3
        painter.fillRect(QRect(0,       0, w3,              height), QColor("#002654"))
        painter.fillRect(QRect(w3,      0, w3,              height), QColor("#FFFFFF"))
        painter.fillRect(QRect(w3 * 2,  0, width - w3 * 2, height), QColor("#ED2939"))

    elif country_code == "JP":
        painter.fillRect(r, QColor("#FFFFFF"))
        painter.setBrush(QColor("#BC002D"))
        cx, cy = width // 2, height // 2
        painter.drawEllipse(cx - 4, cy - 4, 8, 8)

    elif country_code == "CA":
        w3 = width // 4
        painter.fillRect(QRect(0,          0, w3,              height), QColor("#FF0000"))
        painter.fillRect(QRect(w3,         0, width - w3 * 2, height), QColor("#FFFFFF"))
        painter.fillRect(QRect(width - w3, 0, w3,              height), QColor("#FF0000"))

    elif country_code == "AU":
        painter.fillRect(r, QColor("#012169"))
        painter.fillRect(QRect(width // 2 - 2, 0, 4, height), QColor("#FFFFFF"))
        painter.fillRect(QRect(0, height // 2 - 2, width, 4), QColor("#FFFFFF"))
        painter.fillRect(QRect(width // 2 - 1, 0, 2, height), QColor("#C8102E"))
        painter.fillRect(QRect(0, height // 2 - 1, width, 2), QColor("#C8102E"))

    elif country_code == "SG":
        painter.fillRect(QRect(0, 0,          width, height // 2), QColor("#ED2939"))
        painter.fillRect(QRect(0, height // 2, width, height // 2), QColor("#FFFFFF"))

    elif country_code == "IN":
        h3 = height // 3
        painter.fillRect(QRect(0, 0,      width, h3),              QColor("#FF9933"))
        painter.fillRect(QRect(0, h3,     width, h3),              QColor("#FFFFFF"))
        painter.fillRect(QRect(0, h3 * 2, width, height - h3 * 2), QColor("#128807"))

    elif country_code == "BR":
        painter.fillRect(r, QColor("#009739"))
        cx, cy = width // 2, height // 2
        points = [
            QPoint(cx, 2), QPoint(width - 2, cy),
            QPoint(cx, height - 2), QPoint(2, cy),
        ]
        painter.setBrush(QColor("#FFDF00"))
        painter.drawPolygon(QPolygon(points))

    elif country_code == "KR":
        painter.fillRect(r, QColor("#FFFFFF"))
        painter.setBrush(QColor("#CD2E3A"))
        painter.drawEllipse(width // 2 - 4, height // 2 - 4, 8, 8)

    elif country_code == "CN":
        painter.fillRect(r, QColor("#DE2910"))
        painter.setBrush(QColor("#FFDE00"))
        painter.drawEllipse(2, 2, 6, 6)

    elif country_code == "RU":
        h3 = height // 3
        painter.fillRect(QRect(0, 0,      width, h3),              QColor("#FFFFFF"))
        painter.fillRect(QRect(0, h3,     width, h3),              QColor("#0039A6"))
        painter.fillRect(QRect(0, h3 * 2, width, height - h3 * 2), QColor("#D52B1E"))

    elif country_code == "NL":
        h3 = height // 3
        painter.fillRect(QRect(0, 0,      width, h3),              QColor("#AE1C28"))
        painter.fillRect(QRect(0, h3,     width, h3),              QColor("#FFFFFF"))
        painter.fillRect(QRect(0, h3 * 2, width, height - h3 * 2), QColor("#21468B"))

    elif country_code == "IT":
        w3 = width // 3
        painter.fillRect(QRect(0,       0, w3,              height), QColor("#009246"))
        painter.fillRect(QRect(w3,      0, w3,              height), QColor("#FFFFFF"))
        painter.fillRect(QRect(w3 * 2,  0, width - w3 * 2, height), QColor("#CE2B37"))

    elif country_code == "ES":
        h4 = height // 4
        painter.fillRect(QRect(0, 0,       width, h4              ), QColor("#AA151B"))
        painter.fillRect(QRect(0, h4,      width, height - h4 * 2  ), QColor("#F1BF00"))
        painter.fillRect(QRect(0, height - h4, width, h4          ), QColor("#AA151B"))

    elif country_code == "SE":
        painter.fillRect(r, QColor("#006AA7"))
        painter.fillRect(QRect(0, height // 2 - 2, width, 4), QColor("#FECC02"))
        painter.fillRect(QRect(width // 3 - 2, 0, 4, height), QColor("#FECC02"))

    elif country_code == "NO":
        painter.fillRect(r, QColor("#EF2B2D"))
        painter.fillRect(QRect(0, height // 2 - 2, width, 4), QColor("#FFFFFF"))
        painter.fillRect(QRect(width // 3 - 2, 0, 4, height), QColor("#FFFFFF"))
        painter.fillRect(QRect(0, height // 2 - 1, width, 2), QColor("#002868"))
        painter.fillRect(QRect(width // 3 - 1, 0, 2, height), QColor("#002868"))

    elif country_code == "NZ":
        painter.fillRect(r, QColor("#012169"))
        painter.fillRect(QRect(width // 2 - 2, 0, 4, height), QColor("#FFFFFF"))
        painter.fillRect(QRect(0, height // 2 - 2, width, 4), QColor("#FFFFFF"))
        painter.fillRect(QRect(width // 2 - 1, 0, 2, height), QColor("#C8102E"))
        painter.fillRect(QRect(0, height // 2 - 1, width, 2), QColor("#C8102E"))

    elif country_code == "MX":
        w3 = width // 3
        painter.fillRect(QRect(0,       0, w3,              height), QColor("#006847"))
        painter.fillRect(QRect(w3,      0, w3,              height), QColor("#FFFFFF"))
        painter.fillRect(QRect(w3 * 2,  0, width - w3 * 2, height), QColor("#CE1126"))

    else:  # Generic: show a grey box with first 2 letters
        painter.fillRect(r, QColor("#44475a"))
        painter.setPen(QColor("#e2e8f0"))
        font = painter.font()
        font.setPointSizeF(5.5)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(r, Qt.AlignmentFlag.AlignCenter, country_code[:2])

    painter.end()
    return pix

def draw_country_flag(painter: QPainter, country_code: str, rect: QRect):
    """Draw a simple flag icon for the given country code into rect using painter."""
    # Flag dimensions
    flag_width = 20
    flag_height = 14
    flag_rect = QRect(rect.left() + 5, rect.top() + (rect.height() - flag_height) // 2,
                     flag_width, flag_height)

    if country_code == "US":  # Stars and stripes
        # Red and white stripes
        painter.fillRect(flag_rect, QColor("#B22234"))  # Red background
        for i in range(7):
            if i % 2 == 0:
                painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + i * 2, flag_width, 2),
                               QColor("#FFFFFF"))

        # Blue canton
        canton_rect = QRect(flag_rect.left(), flag_rect.top(), flag_width * 2 // 3, flag_height * 7 // 13)
        painter.fillRect(canton_rect, QColor("#3C3B6E"))

    elif country_code == "GB":  # Union Jack
        painter.fillRect(flag_rect, QColor("#012169"))  # Dark blue background
        # Simple cross
        painter.fillRect(QRect(flag_rect.left() + 8, flag_rect.top(), 4, flag_height), QColor("#FFFFFF"))
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + 5, flag_width, 4), QColor("#FFFFFF"))
        painter.fillRect(QRect(flag_rect.left() + 8, flag_rect.top(), 4, flag_height), QColor("#C8102E"))
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + 5, flag_width, 4), QColor("#C8102E"))

    elif country_code == "DE":  # German flag
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top(), flag_width, flag_height // 3), QColor("#000000"))
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + flag_height // 3, flag_width, flag_height // 3), QColor("#DD0000"))
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + 2 * flag_height // 3, flag_width, flag_height // 3), QColor("#FFCC00"))

    elif country_code == "FR":  # French flag
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top(), flag_width // 3, flag_height), QColor("#002654"))
        painter.fillRect(QRect(flag_rect.left() + flag_width // 3, flag_rect.top(), flag_width // 3, flag_height), QColor("#FFFFFF"))
        painter.fillRect(QRect(flag_rect.left() + 2 * flag_width // 3, flag_rect.top(), flag_width // 3, flag_height), QColor("#ED2939"))

    elif country_code == "JP":  # Japanese flag
        painter.fillRect(flag_rect, QColor("#FFFFFF"))
        painter.setBrush(QColor("#BC002D"))
        painter.drawEllipse(flag_rect.center(), 5, 5)

    elif country_code == "CA":  # Canadian flag (simplified)
        painter.fillRect(flag_rect, QColor("#FF0000"))
        painter.fillRect(QRect(flag_rect.left() + 8, flag_rect.top(), 4, flag_height), QColor("#FFFFFF"))

    elif country_code == "AU":  # Australian flag (simplified)
        painter.fillRect(flag_rect, QColor("#012169"))
        # Cross
        painter.fillRect(QRect(flag_rect.left() + 8, flag_rect.top(), 4, flag_height), QColor("#FFFFFF"))
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + 5, flag_width, 4), QColor("#FFFFFF"))

    elif country_code == "SG":  # Singapore flag (simplified)
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top(), flag_width, flag_height // 2), QColor("#ED2939"))
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + flag_height // 2, flag_width, flag_height // 2), QColor("#FFFFFF"))

    elif country_code == "IN":  # Indian flag (simplified)
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top(), flag_width, flag_height // 3), QColor("#FF9933"))
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + flag_height // 3, flag_width, flag_height // 3), QColor("#FFFFFF"))
        painter.fillRect(QRect(flag_rect.left(), flag_rect.top() + 2 * flag_height // 3, flag_width, flag_height // 3), QColor("#128807"))

    elif country_code == "BR":  # Brazilian flag (simplified)
        painter.fillRect(flag_rect, QColor("#009739"))
        # Yellow diamond
        points = [
            QPoint(flag_rect.center().x(), flag_rect.top() + 2),
            QPoint(flag_rect.right() - 2, flag_rect.center().y()),
            QPoint(flag_rect.center().x(), flag_rect.bottom() - 2),
            QPoint(flag_rect.left() + 2, flag_rect.center().y())
        ]
        painter.setBrush(QColor("#FFDF00"))
        painter.drawPolygon(points)

    else:  # Default flag pattern
        painter.fillRect(flag_rect, QColor("#CCCCCC"))
        painter.setPen(QColor("#666666"))
        painter.drawText(flag_rect, Qt.AlignmentFlag.AlignCenter, "?")

# ─── Worker thread ──────────────────────────────────────────────────────────────
class FetchWorker(QObject):
    finished = Signal(object)
    error    = Signal(str)

    def __init__(self, params: dict, api_base: str):
        super().__init__()
        self._params   = params
        self._api_base = api_base

    def run(self):
        try:
            resp = requests.get(self._api_base, params=self._params, timeout=15)
            self.finished.emit(resp)
        except requests.exceptions.ConnectionError:
            self.error.emit("Connection refused – check API server.")
        except requests.exceptions.Timeout:
            self.error.emit("Request timed out.")
        except Exception as exc:
            self.error.emit(str(exc))

# ─── Proxy check worker ────────────────────────────────────────────────────────
PROXY_CHECK_TIMEOUT    = 8.0    # seconds — TCP connect timeout per proxy
PROXY_CHECK_CONCURRENCY = 500   # max simultaneous TCP check threads (mirrors proxy.py)
_check_semaphore = threading.Semaphore(PROXY_CHECK_CONCURRENCY)

class ProxyCheckWorker(QObject):
    result = Signal(bool, float, str)   # alive, elapsed_ms (-1 if failed), peer_ip

    def __init__(self, proxy_str: str):
        super().__init__()
        self._proxy = proxy_str   # "ip:port"

    def run(self):
        try:
            host, port_str = self._proxy.rsplit(":", 1)
            port = int(port_str)
        except (ValueError, AttributeError):
            self.result.emit(False, -1.0, "")
            return

        with _check_semaphore:
            t0 = time.monotonic()
            try:
                with socket.create_connection((host, port),
                                              timeout=PROXY_CHECK_TIMEOUT) as sock:
                    elapsed = (time.monotonic() - t0) * 1000
                    peer_ip = sock.getpeername()[0]
                    self.result.emit(True, elapsed, peer_ip)
            except socket.timeout:
                self.result.emit(False, (time.monotonic() - t0) * 1000, "")
            except ConnectionRefusedError:
                self.result.emit(False, (time.monotonic() - t0) * 1000, "")
            except OSError:
                self.result.emit(False, (time.monotonic() - t0) * 1000, "")
            except Exception:
                self.result.emit(False, -1.0, "")

# ─── Refresh worker (re-fetch one proxy slot by its original params) ───────────
class RefreshWorker(QObject):
    finished = Signal(object)   # requests.Response
    error    = Signal(str)

    def __init__(self, params: dict, api_base: str):
        super().__init__()
        self._params   = params
        self._api_base = api_base

    def run(self):
        try:
            resp = requests.get(self._api_base, params=self._params, timeout=15)
            self.finished.emit(resp)
        except requests.exceptions.ConnectionError:
            self.error.emit("Connection refused – check API server.")
        except requests.exceptions.Timeout:
            self.error.emit("Request timed out.")
        except Exception as exc:
            self.error.emit(str(exc))

# ─── Port pre-check worker (ping TCP before fetching from API) ─────────────────
class PortPreCheckWorker(QObject):
    """Check whether a TCP port is alive before fetching from the API.

    Signals:
        result(alive: bool, elapsed_ms: float, peer_ip: str, host: str, port: int)
    """
    result = Signal(bool, float, str, str, int)

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
                elapsed  = (time.monotonic() - t0) * 1000
                peer_ip  = sock.getpeername()[0]
                self.result.emit(True, elapsed, peer_ip, self._host, self._port)
        except Exception:
            elapsed = (time.monotonic() - t0) * 1000
            self.result.emit(False, elapsed, "", self._host, self._port)

# ─── Geo-check worker: Ping proxy then query ip-api.com ──────────────────
class GeoCheckWorker(QObject):
    """
    1. Ping proxy by sending request through it to httpbin.org/ip
    2. Extract origin IP (public IP of the proxy) from response
    3. Call http://ip-api.com/json/<IP> to retrieve geo info.

    Signals
    -------
    result(alive, elapsed_ms, origin_ip, country, country_code,
           region_name, city, isp, error)
    """
    result = Signal(bool, float, str, str, str, str, str, str, str)

    TEST_URL = "http://httpbin.org/ip"
    GEO_URL  = "http://ip-api.com/json/{ip}?fields=status,country,countryCode,regionName,city,isp,query"
    TIMEOUT  = 10.0

    def __init__(self, proxy_str: str):
        super().__init__()
        self._proxy = proxy_str   # "ip:port"

    def run(self):
        # ── Step 1: Ping proxy to get its public IP ────────────────────────
        try:
            proxies = {
                "http":  f"http://{self._proxy}",
                "https": f"http://{self._proxy}",
            }
            t0 = time.monotonic()
            resp = requests.get(self.TEST_URL, proxies=proxies, timeout=self.TIMEOUT)
            elapsed = (time.monotonic() - t0) * 1000
            if resp.status_code == 200:
                try:
                    origin = resp.json().get("origin", "")
                except Exception:
                    origin = ""
                if not origin:
                    self.result.emit(False, elapsed, "", "", "", "", "", "", "No origin IP in response")
                    return
            else:
                self.result.emit(False, elapsed, "", "", "", "", "", "", f"HTTP {resp.status_code}")
                return
        except Exception as exc:
            elapsed = (time.monotonic() - t0) * 1000 if 't0' in locals() else 0.0
            self.result.emit(False, elapsed, "", "", "", "", "", "", str(exc))
            return

        # ── Step 2: Geo lookup using public proxy IP ───────────────────────
        try:
            geo_resp = requests.get(
                self.GEO_URL.format(ip=origin),
                timeout=self.TIMEOUT,
            )
            geo = geo_resp.json() if geo_resp.status_code == 200 else {}
        except Exception:
            geo = {}

        country      = geo.get("country",     "")
        country_code = geo.get("countryCode", "")
        region_name  = geo.get("regionName",  "")
        city         = geo.get("city",        "")
        isp          = geo.get("isp",         "")

        self.result.emit(
            True, elapsed, origin,
            country, country_code, region_name, city, isp, "",
        )

# ─── Proxy Card widget ─────────────────────────────────────────────────────────
class ProxyCard(QWidget):
    """A rich card widget representing one cached proxy entry."""

    deleted         = Signal(object)        # emits self when user deletes
    refreshed       = Signal(object, dict)   # emits (self, new_proxy_dict) after refresh
    auto_check_done = Signal(object)         # emits self when auto-check cycle finished (alive or refresh done)

    def __init__(self, proxy_dict: dict, api_base_fn, parent=None):
        super().__init__(parent)
        self.setObjectName("proxyCard")
        self._proxy_dict  = dict(proxy_dict)
        self._api_base_fn = api_base_fn   # callable → current api base url
        self._refresh_thread = None
        self._refresh_worker = None
        self._check_thread   = None
        self._check_worker   = None
        self._auto_check_triggered  = False
        self._auto_refresh_pending  = False
        self._local_ip = current_ipv4() or "127.0.0.1"
        self._build()

    # ── accessors ──
    @property
    def proxy_dict(self) -> dict:
        return self._proxy_dict

    def _proxy_id(self) -> str:
        return self._proxy_dict.get("_id", "")

    def _ip_port(self) -> tuple:
        ip   = self._proxy_dict.get("ip",   self._proxy_dict.get("host", ""))
        port = self._proxy_dict.get("port", "")
        return ip, str(port)

    def _build(self):
        ip, port = self._ip_port()
        # Use response_ip if available (machine's actual proxy IP), otherwise use configured IP
        display_ip = current_ipv4()
        proxy_str = f"{display_ip}:{port}" if display_ip else "unknown"

        # ── Outer: single HBox — left info col | stretch | status col | buttons ──
        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(10)

        # ── Left column: ip:port+copy on top, tags below ──
        left_col = QVBoxLayout()
        left_col.setSpacing(4)
        left_col.setContentsMargins(0, 0, 0, 0)

        ip_copy_layout = QHBoxLayout()
        ip_copy_layout.setSpacing(4)
        ip_copy_layout.setContentsMargins(0, 0, 0, 0)

        self._ip_lbl = QLabel(proxy_str)
        self._ip_lbl.setObjectName("proxyIp")
        self._ip_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        ip_copy_layout.addWidget(self._ip_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        self._copy_btn = QPushButton("⧉")
        self._copy_btn.setObjectName("cardCopyBtn")
        self._copy_btn.setToolTip("Copy proxy")
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.setFixedHeight(24)
        ip_copy_layout.addWidget(self._copy_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self._response_ip_lbl = QLabel()
        self._response_ip_lbl.setObjectName("responseIp")
        self._response_ip_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        response_ip = self._proxy_dict.get("response_ip")
        if response_ip:
            self._response_ip_lbl.setText(f" → {response_ip}")
        ip_copy_layout.addWidget(self._response_ip_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        # No longer need the response IP label since main label now shows the actual proxy IP
        ip_copy_layout.addStretch()

        left_col.addLayout(ip_copy_layout)

        # Tags row
        tags_layout = QHBoxLayout()
        tags_layout.setSpacing(6)
        tags_layout.setContentsMargins(0, 0, 0, 0)

        meta_fields = [
            ("country", "🌍"),
            ("state",   "- 📍"),
            ("city",    "- 🏙️"),
            ("isp",     "- 📡"),
        ]
        has_tag = False
        for key, icon in meta_fields:
            val = self._proxy_dict.get(key, "")
            if val and str(val).strip():
                if key == "country":
                    # Wrap flag image + country code in a single container tag
                    country_container = QWidget()
                    country_container.setObjectName("tagLabel")
                    c_layout = QHBoxLayout(country_container)
                    c_layout.setContentsMargins(0, 0, 0, 0)
                    c_layout.setSpacing(4)
                    flag_lbl = QLabel()
                    flag_lbl.setPixmap(make_flag_pixmap(str(val).upper()))
                    flag_lbl.setFixedSize(19, 11)
                    flag_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    c_layout.addWidget(flag_lbl)
                    code_lbl = QLabel(val)
                    c_layout.addWidget(code_lbl)
                    tags_layout.addWidget(country_container, 0, Qt.AlignmentFlag.AlignVCenter)
                else:
                    tag = QLabel(f"{icon} {val}")
                    tag.setObjectName("tagLabel")
                    tags_layout.addWidget(tag)
                has_tag = True

        if not has_tag:
            for k, v in self._proxy_dict.items():
                if k in ("ip", "host") or not v:
                    continue
                tag = QLabel(f"{k}: {v}")
                tag.setObjectName("tagLabel")
                tags_layout.addWidget(tag)

        tags_layout.addStretch()
        left_col.addLayout(tags_layout)

        outer.addLayout(left_col, 1)

        # ── Status + ping column (right-aligned, aligned to left col rows) ──
        status_widget = QWidget()
        status_widget.setStyleSheet("background: transparent;")
        status_col = QVBoxLayout(status_widget)
        status_col.setSpacing(4)
        status_col.setContentsMargins(0, 0, 0, 0)

        # Determine initial status based on available data
        saved_ping = self._proxy_dict.get("ping_ms", None)
        has_response_ip = bool(self._proxy_dict.get("response_ip", ""))

        if saved_ping is not None:
            status_text = "● Alive"
            status_object_name = "statusAlive"
        elif has_response_ip:
            status_text = "● Checked"
            status_object_name = "statusAlive"
        else:
            status_text = "● Unknown"
            status_object_name = "statusUnknown"

        self._status_lbl = QLabel(status_text)
        self._status_lbl.setObjectName(status_object_name)
        status_col.addWidget(self._status_lbl, 0, Qt.AlignmentFlag.AlignRight)

        saved_ping = self._proxy_dict.get("ping_ms", None)
        self._ping_lbl = QLabel(f"{saved_ping:.0f} ms" if saved_ping is not None else "")
        self._ping_lbl.setObjectName("pingLabel")
        status_col.addWidget(self._ping_lbl, 0, Qt.AlignmentFlag.AlignRight)

        outer.addWidget(status_widget, 0, Qt.AlignmentFlag.AlignVCenter)

        # ── Action buttons (centered vertically across both rows) ──
        self._refresh_btn = QPushButton("↻ Refresh")
        self._refresh_btn.setObjectName("cardRefreshBtn")
        self._refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_btn.setFixedHeight(28)

        self._check_btn = QPushButton("⚡Check")
        self._check_btn.setObjectName("cardCheckBtn")
        self._check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._check_btn.setFixedHeight(28)

        self._delete_btn = QPushButton("❌")
        self._delete_btn.setObjectName("cardDeleteBtn")
        self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_btn.setFixedHeight(28)

        outer.addWidget(self._refresh_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        outer.addWidget(self._check_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        outer.addWidget(self._delete_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        # ── Wire signals ──
        self._check_btn.clicked.connect(self._do_check)
        self._refresh_btn.clicked.connect(self._do_refresh)
        self._delete_btn.clicked.connect(self._do_delete)
        self._copy_btn.clicked.connect(self._do_copy)

    def update_button_visibility(self, auto_check_enabled: bool):
        """Update visibility of check and refresh buttons based on auto-check state."""
        # Hide check and refresh buttons when auto-check is enabled
        self._check_btn.setVisible(not auto_check_enabled)
        self._refresh_btn.setVisible(not auto_check_enabled)

    def update_geo_data(
        self,
        elapsed_ms: float,
        origin_ip: str,
        country_code: str,
        region_name: str,
        city: str,
        isp: str,
    ):
        """Update this card's geo data and refresh the UI display."""
        # Update proxy dict in memory
        if origin_ip:
            self._proxy_dict["response_ip"] = origin_ip
            # Update response IP label
            self._response_ip_lbl.setText(f" → {origin_ip}")
        if country_code:
            self._proxy_dict["country"] = country_code
        if region_name:
            self._proxy_dict["state"] = region_name
        if city:
            self._proxy_dict["city"] = city
            self._proxy_dict["_city"] = city
        if isp:
            self._proxy_dict["isp"] = isp
        self._proxy_dict["ping_ms"] = round(elapsed_ms, 1)

        # Update status and ping display
        self._status_lbl.setObjectName("statusAlive")
        self._status_lbl.setText("● Alive")
        self._ping_lbl.setText(f"{elapsed_ms:.0f} ms")

        self._status_lbl.style().unpolish(self._status_lbl)
        self._status_lbl.style().polish(self._status_lbl)

    def _rebuild_tags(self):
        """Rebuild the tags row widget from current _proxy_dict values."""
        # Find the tags layout (second item in left_col, which is in outer layout[0])
        outer_layout = self.layout()
        left_col_layout = outer_layout.itemAt(0).layout()
        if not left_col_layout:
            return
        tags_layout_item = left_col_layout.itemAt(1)
        if not tags_layout_item:
            return
        tags_layout = tags_layout_item.layout()
        if not tags_layout:
            return

        # Clear existing tag widgets
        while tags_layout.count() > 0:
            item = tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Re-add tags
        meta_fields = [
            ("country", "🌍"),
            ("state",   "- 📍"),
            ("city",    "- 🏙️"),
            ("isp",     "- 📡"),
        ]
        has_tag = False
        for key, icon in meta_fields:
            val = self._proxy_dict.get(key, "")
            if val and str(val).strip():
                if key == "country":
                    # Wrap flag image + country code in a single container tag
                    country_container = QWidget()
                    country_container.setObjectName("tagLabel")
                    c_layout = QHBoxLayout(country_container)
                    c_layout.setContentsMargins(0, 0, 0, 0)
                    c_layout.setSpacing(4)
                    flag_lbl = QLabel()
                    flag_lbl.setPixmap(make_flag_pixmap(str(val).upper()))
                    flag_lbl.setFixedSize(19, 11)
                    flag_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    c_layout.addWidget(flag_lbl)
                    code_lbl = QLabel(val)
                    c_layout.addWidget(code_lbl)
                    tags_layout.addWidget(country_container, 0, Qt.AlignmentFlag.AlignVCenter)
                else:
                    tag = QLabel(f"{icon} {val}")
                    tag.setObjectName("tagLabel")
                    tags_layout.addWidget(tag)
                has_tag = True

        if not has_tag:
            for k, v in self._proxy_dict.items():
                if k in ("ip", "host") or not v:
                    continue
                tag = QLabel(f"{k}: {v}")
                tag.setObjectName("tagLabel")
                tags_layout.addWidget(tag)

        tags_layout.addStretch()

    # ── Copy ──
    def _do_copy(self):
        ip, port = self._ip_port()
        proxy_str = f"{ip}:{port}" if ip else "unknown"
        QApplication.clipboard().setText(proxy_str)
        self._copy_btn.setText("✓")
        QTimer.singleShot(1500, lambda: self._copy_btn.setText("⧉"))

    # ── Delete ──
    def _do_delete(self):
        ip, port = self._ip_port()
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete proxy {ip or '?'}:{port}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        delete_proxy_from_file(proxy_id=self._proxy_id(), ip=ip, port=port)
        self.deleted.emit(self)

    # ── TCP port check (fast, used after refresh to confirm port is open) ──
    def _do_tcp_check(self):
        """Quick TCP connect to 127.0.0.1:{port} — does NOT go through httpbin."""
        if self._check_thread is not None and self._check_thread.isRunning():
            return

        _, port = self._ip_port()
        if not port:
            return
        try:
            port_int = int(port)
        except (ValueError, TypeError):
            return

        self._check_btn.setEnabled(False)
        self._refresh_btn.setEnabled(False)
        self._status_lbl.setObjectName("statusChecking")
        self._status_lbl.setText("… checking")
        self._status_lbl.setStyleSheet("")
        self._ping_lbl.setText("")

        thread = QThread()
        worker = PortPreCheckWorker("127.0.0.1", port_int, timeout=5.0)
        worker.moveToThread(thread)

        self._check_thread = thread
        self._check_worker = worker

        thread.started.connect(worker.run)
        worker.result.connect(self._on_tcp_check_result)
        worker.result.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_check_thread_finished)
        thread.start()

    def _on_tcp_check_result(self, alive: bool, elapsed_ms: float, peer_ip: str, host: str, port: int):
        self._check_btn.setEnabled(True)
        self._refresh_btn.setEnabled(True)
        if alive:
            self._status_lbl.setObjectName("statusAlive")
            self._status_lbl.setText("● Alive")
            self._ping_lbl.setText(f"{elapsed_ms:.0f} ms")
            self._proxy_dict["ping_ms"] = round(elapsed_ms, 1)
            stats_collector.record_ping(elapsed_ms)
            ip, p = self._ip_port()
            update_proxy_in_file(
                proxy_id=self._proxy_id(), ip=ip, port=p,
                updates={"ping_ms": round(elapsed_ms, 1)},
            )
        else:
            self._status_lbl.setObjectName("statusDead")
            self._status_lbl.setText("✕ Dead")
            self._ping_lbl.setText("")
        self._status_lbl.style().unpolish(self._status_lbl)
        self._status_lbl.style().polish(self._status_lbl)

    # ── Check ──
    def _do_check(self):
        # Prevent starting a new check while one is already running
        if self._check_thread is not None and self._check_thread.isRunning():
            return

        _, port = self._ip_port()
        if not port:
            return

        # Re-fetch local IP before every check to detect network changes
        fresh_ip = current_ipv4() or "127.0.0.1"
        if fresh_ip != self._local_ip:
            print(f"[ProxyCard] Local IP changed: {self._local_ip} → {fresh_ip}")
            self._local_ip = fresh_ip

        proxy_str = f"{self._local_ip}:{port}"
        self._check_btn.setEnabled(False)
        self._refresh_btn.setEnabled(False)
        self._status_lbl.setObjectName("statusChecking")
        self._status_lbl.setText("… checking")
        self._status_lbl.setStyleSheet("")
        self._ping_lbl.setText("")

        thread = QThread()
        worker = ProxyCheckWorker(proxy_str)
        worker.moveToThread(thread)

        # Keep hard references so Qt doesn't GC them before the thread finishes
        self._check_thread = thread
        self._check_worker = worker

        thread.started.connect(worker.run)
        worker.result.connect(self._on_check_result)
        # quit the thread loop after result, then clean up
        worker.result.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        # Clear our refs only after the thread is truly done
        thread.finished.connect(self._on_check_thread_finished)
        thread.start()

    def _on_check_thread_finished(self):
        self._check_thread = None
        self._check_worker = None

    def _on_check_result(self, alive: bool, elapsed: float, response_ip: str = ""):
        # NOTE: do NOT null _check_thread/_check_worker here — they are cleared by
        # _on_check_thread_finished which fires after thread.finished, ensuring
        # Qt's deleteLater can still reach the C++ objects safely.
        self._check_btn.setEnabled(True)
        self._refresh_btn.setEnabled(True)
        if alive:
            self._status_lbl.setObjectName("statusAlive")
            self._status_lbl.setText("● Alive")
            if elapsed >= 0:
                self._ping_lbl.setText(f"{elapsed:.0f} ms")
                self._proxy_dict["ping_ms"] = elapsed
                stats_collector.record_ping(elapsed)
            # Update response IP label and persist to data.json
            ip, port = self._ip_port()
            updates: dict = {}
            if elapsed >= 0:
                updates["ping_ms"] = elapsed
            # NOTE: Do NOT update response_ip from TCP check result — the peer_ip here
            # is the local proxy port's peer (127.0.0.1 / LAN IP), not the proxy's
            # public IP. The public IP is set by geo-check (update_geo_data) and
            # should not be overwritten by a plain TCP port-open check.
            if updates:
                update_proxy_in_file(proxy_id=self._proxy_id(), ip=ip, port=port, updates=updates)
            was_auto = self._auto_check_triggered
            self._auto_check_triggered = False  # Reset flag
            if was_auto:
                self.auto_check_done.emit(self)  # Notify: cycle done, proxy is alive
        else:
            self._status_lbl.setObjectName("statusDead")
            self._status_lbl.setText("✕ Dead")
            self._ping_lbl.setText("")
            # Auto-refresh if this check was triggered automatically
            if self._auto_check_triggered:
                self._auto_check_triggered = False  # Reset flag
                # Small delay before auto-refresh to avoid overwhelming the API
                self._auto_refresh_pending = True
                QTimer.singleShot(1000, self._do_refresh)
                # auto_check_done will be emitted after refresh finishes
        # Force QSS re-evaluation after objectName change
        self._status_lbl.style().unpolish(self._status_lbl)
        self._status_lbl.style().polish(self._status_lbl)

    # ── Refresh ──
    def _do_refresh(self):
        # Prevent starting a new refresh while one is already running
        if self._refresh_thread is not None and self._refresh_thread.isRunning():
            return
        # Also prevent refresh while a check is running
        if self._check_thread is not None and self._check_thread.isRunning():
            return

        # Build API params from metadata stored in proxy_dict
        port = self._proxy_dict.get("port", "")

        params = {
            "country": self._proxy_dict.get("country", ""),
            "state":   self._proxy_dict.get("state",   ""),
            "city":    self._proxy_dict.get("_city",   ""),
            "postal":  self._proxy_dict.get("postal",  ""),
            "isp":     self._proxy_dict.get("isp",     ""),
            "start":   str(port) if port else "40000",
            "num":     "1",
            "ip":      "",
        }

        self._refresh_btn.setEnabled(False)
        self._check_btn.setEnabled(False)
        self._status_lbl.setObjectName("statusChecking")
        self._status_lbl.setText("… fetching")
        self._status_lbl.style().unpolish(self._status_lbl)
        self._status_lbl.style().polish(self._status_lbl)

        thread = QThread()
        worker = RefreshWorker(params, self._api_base_fn())
        worker.moveToThread(thread)

        self._refresh_thread = thread
        self._refresh_worker = worker

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_refresh_done)
        worker.error.connect(self._on_refresh_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_refresh_thread_finished)
        thread.start()

    def _on_refresh_thread_finished(self):
        self._refresh_thread = None
        self._refresh_worker = None

    def _on_refresh_done(self, resp):
        self._refresh_btn.setEnabled(True)
        self._check_btn.setEnabled(True)
        was_auto = self._auto_refresh_pending
        self._auto_refresh_pending = False
        if resp.status_code != 200:
            stats_collector.record_refresh_fail()
            self._status_lbl.setObjectName("statusDead")
            self._status_lbl.setText(f"✕ HTTP {resp.status_code}")
            self._status_lbl.style().unpolish(self._status_lbl)
            self._status_lbl.style().polish(self._status_lbl)
            if was_auto:
                self.auto_check_done.emit(self)
            return

        try:
            text = resp.text.strip()
            data = None

            # Always try JSON first (regardless of content-type header)
            try:
                data = resp.json()
                # If the JSON is a plain "ip:port" string
                if isinstance(data, str):
                    if ':' in data:
                        ip, port = data.split(':', 1)
                        data = {"ip": ip.strip(), "port": port.strip()}
                    else:
                        data = None  # not usable
            except Exception:
                data = None  # not JSON — fall through to plain-text parse

            # Plain text fallback → try "ip:port" format (possibly multi-line)
            if data is None:
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                proxies_from_text = []
                for line in lines:
                    if ':' in line:
                        ip, port = line.split(':', 1)
                        proxies_from_text.append({"ip": ip.strip(), "port": port.strip()})
                if proxies_from_text:
                    data = proxies_from_text
                else:
                    print(f"[DEBUG] Refresh – unrecognised format. body={text[:300]!r}")
                    stats_collector.record_refresh_fail()
                    self._status_lbl.setObjectName("statusDead")
                    self._status_lbl.setText("✕ Bad format")
                    self._status_lbl.style().unpolish(self._status_lbl)
                    self._status_lbl.style().polish(self._status_lbl)
                    if was_auto:
                        self.auto_check_done.emit(self)
                    return
        except Exception as e:
            print(f"[DEBUG] Refresh parse error: {e}")
            print(f"[DEBUG] Refresh response text: {resp.text[:500]}...")
            stats_collector.record_refresh_fail()
            self._status_lbl.setObjectName("statusDead")
            self._status_lbl.setText("✕ Bad JSON")
            self._status_lbl.style().unpolish(self._status_lbl)
            self._status_lbl.style().polish(self._status_lbl)
            if was_auto:
                self.auto_check_done.emit(self)
            return

        # Extract first proxy from response
        new_proxy: dict | None = None
        if isinstance(data, list) and data:
            new_proxy = data[0] if isinstance(data[0], dict) else None
        elif isinstance(data, dict):
            new_proxy = data

        if not new_proxy:
            stats_collector.record_refresh_fail()
            self._status_lbl.setObjectName("statusDead")
            self._status_lbl.setText("✕ No result")
            self._status_lbl.style().unpolish(self._status_lbl)
            self._status_lbl.style().polish(self._status_lbl)
            if was_auto:
                self.auto_check_done.emit(self)
            return

        # Preserve metadata from old entry
        for meta_key in ("country", "state", "city", "postal", "isp", "_city"):
            if meta_key not in new_proxy and meta_key in self._proxy_dict:
                new_proxy[meta_key] = self._proxy_dict[meta_key]

        # Delete old proxy from cache, save new one
        old_ip, old_port = self._ip_port()
        delete_proxy_from_file(proxy_id=self._proxy_id(), ip=old_ip, port=old_port)
        save_proxies_to_file([new_proxy])

        # Notify auto-check cycle before emitting refreshed (card will be destroyed)
        if was_auto:
            self.auto_check_done.emit(self)
        self.refreshed.emit(self, new_proxy)

    def _on_refresh_error(self, msg: str):
        # NOTE: thread/worker refs are cleared by _on_refresh_thread_finished
        stats_collector.record_refresh_fail()
        self._refresh_btn.setEnabled(True)
        self._check_btn.setEnabled(True)
        was_auto = self._auto_refresh_pending
        self._auto_refresh_pending = False
        self._status_lbl.setObjectName("statusDead")
        self._status_lbl.setText("✕ Error")
        self._status_lbl.style().unpolish(self._status_lbl)
        self._status_lbl.style().polish(self._status_lbl)
        if was_auto:
            self.auto_check_done.emit(self)

# ─── Autocomplete ComboBox ──────────────────────────────────────────────────────
class HighlightDelegate(QStyledItemDelegate):
    """Custom delegate to highlight matching text in dropdown items."""

    def __init__(self, combo_box, parent=None):
        super().__init__(parent)
        self.combo_box = combo_box
        self.highlight_color = QColor(PALETTE['accent'])
        self.match_text = ""

    def set_match_text(self, text: str):
        self.match_text = text.lower()

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        # Get the text
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not text:
            return super().paint(painter, option, index)

        # Check if this is the currently selected item
        is_selected = (index.row() == self.combo_box.currentIndex())

        # Check if this is area code combo box
        is_area_combo = self.combo_box.objectName() == "area_cb"

        # For area combo, show text with flag icon
        display_text = text
        if is_area_combo:
            display_text = f"  {text}"  # Add space for flag icon

        # Check if we need to highlight
        if self.match_text and self.match_text in text.lower():
            # Draw highlighted background for the entire item
            painter.fillRect(option.rect, self.highlight_color)

            # Draw border radius
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.highlight_color)
            painter.drawRoundedRect(option.rect.adjusted(2, 2, -2, -2), 4, 4)

            # Draw flag icon if area combo
            if is_area_combo and text:
                draw_country_flag(painter, text, option.rect)

            # Draw text in white
            painter.setPen(QColor("#ffffff"))
            text_rect = option.rect.adjusted(35, 0, -30, 0)  # Leave space for flag and check mark
            painter.drawText(text_rect,
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                           display_text)

            # Draw check mark if selected
            if is_selected:
                painter.setPen(QColor("#ffffff"))
                painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
                painter.drawText(option.rect.adjusted(0, 0, -10, 0),
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                               "✓")
        else:
            # No highlighting needed, use default painting but add check mark if selected
            # Draw default background
            super().paint(painter, option, index)

            # Draw flag icon if area combo
            if is_area_combo and text:
                draw_country_flag(painter, text, option.rect)

            # Override text with spacing if area combo
            if is_area_combo:
                # Clear the original text area and redraw
                painter.setPen(option.palette.color(option.palette.ColorRole.Text))
                text_rect = option.rect.adjusted(35, 0, -30, 0)  # Leave space for flag and check mark
                painter.fillRect(text_rect, option.backgroundBrush)  # Clear background
                painter.drawText(text_rect,
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                               display_text)

            if is_selected:
                # Draw check mark on default background
                painter.setPen(QColor(PALETTE['accent']))
                painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
                painter.drawText(option.rect.adjusted(0, 0, -10, 0),
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                               "✓")
class AutoComboBox(QComboBox):
    """Editable QComboBox with live contains-filtering via QCompleter."""

    POPUP_STYLE = f"""
        QAbstractItemView {{
            background: {PALETTE['panel']};
            color: {PALETTE['text']};
            border: 1px solid {PALETTE['border_focus']};
            border-radius: 7px;
            selection-background-color: {PALETTE['accent']};
            selection-color: #fff;
            padding: 4px;
            outline: none;
        }}
        QAbstractItemView::item {{
            min-height: 28px;
            padding: 2px 10px;
            border-radius: 4px;
        }}
        QAbstractItemView::item:hover {{
            background: {PALETTE['accent']};
            color: #fff;
        }}
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setMaxVisibleItems(12)

        self._model = QStringListModel(self)
        self.setModel(self._model)

        self._completer = QCompleter(self._model, self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self._completer.setMaxVisibleItems(12)
        self.setCompleter(self._completer)

        # Create and set custom delegate for highlighting
        self._highlight_delegate = HighlightDelegate(self)
        self._completer.popup().setItemDelegate(self._highlight_delegate)
        self.view().setItemDelegate(self._highlight_delegate)  # Also set for combo box dropdown
        self._completer.popup().setStyleSheet(self.POPUP_STYLE)

        # Connect text changes to update highlighting
        self.editTextChanged.connect(self._update_highlight)

        # Custom arrow label
        self._arrow = QLabel("▼", self)
        self._arrow.setStyleSheet(f"""
            color: {PALETTE['text']};
            font-size: 12pt;
            font-weight: bold;
            background: transparent;
            padding: 0px;
        """)
        self._arrow.setFixedSize(20, 20)
        self._arrow.move(self.width() - 30, (self.height() - 20) // 2)
        self._arrow.show()

        # Update arrow position on resize
        self.resizeEvent = self._on_resize

    def _on_resize(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_arrow'):
            self._arrow.move(self.width() - 30, (self.height() - 20) // 2)

    def _update_highlight(self, text: str):
        """Update the highlight text for the delegate."""
        current_match = self._highlight_delegate.match_text
        new_match = text.strip().lower()
        if current_match != new_match:
            self._highlight_delegate.set_match_text(new_match)
            # Force repaint of the popup
            if self._completer.popup().isVisible():
                self._completer.popup().viewport().update()

    def set_items(self, items: list):
        self._model.setStringList(list(items))

    def current_value(self) -> str:
        return self.currentText().strip()

    def focusInEvent(self, event):
        """Show popup when focusing on combo box."""
        super().focusInEvent(event)
        if not self.view().isVisible():
            self.showPopup()

# ─── Blur Overlay ─────────────────────────────────────────────────────────────
class BlurOverlay(QWidget):
    """Semi-transparent overlay that blocks mouse events on the content beneath it."""

    btn_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setObjectName("blurOverlay")
        self.hide()

        # ── Centered content: warning label + Open CliProxy button ────────────
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        self._lbl = QLabel(
            "⚠ CliProxy is not running\nPlease open CliProxy to use the app"
        )
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl.setStyleSheet(
            "color: rgba(148,163,184,200); font-family: 'Segoe UI'; "
            "font-size: 10pt; background: transparent;"
        )
        layout.addWidget(self._lbl)

        self.btn = QPushButton("Open CliProxy")
        self.btn.setObjectName("cliproxyBtn")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.setFixedSize(120, 36)
        self.btn.clicked.connect(self.btn_clicked)
        layout.addWidget(self.btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Dark semi-transparent overlay
        painter.fillRect(self.rect(), QColor(15, 17, 23, 170))
        painter.end()

    def mousePressEvent(self, event):
        event.accept()   # eat all clicks

    def mouseReleaseEvent(self, event):
        event.accept()

    def mouseMoveEvent(self, event):
        event.accept()

# ─── Timer interval popover ────────────────────────────────────────────────────
class TimerPopover(QWidget):
    interval_changed = Signal(int)

    def __init__(self, initial: int = 30, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("timerPopover")
        self.setFixedWidth(230)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        lbl = QLabel("Check interval")
        lbl.setObjectName("timerPopoverLbl")
        self._val_lbl = QLabel(f"{initial}s")
        self._val_lbl.setObjectName("timerPopoverVal")
        header.addWidget(lbl)
        header.addStretch()
        header.addWidget(self._val_lbl)
        layout.addLayout(header)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(5, 300)
        self._slider.setSingleStep(5)
        self._slider.setPageStep(15)
        self._slider.setValue(initial)
        self._slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self._slider)

        range_row = QHBoxLayout()
        r1 = QLabel("5s"); r1.setObjectName("timerPopoverRange")
        r2 = QLabel("300s"); r2.setObjectName("timerPopoverRange")
        range_row.addWidget(r1)
        range_row.addStretch()
        range_row.addWidget(r2)
        layout.addLayout(range_row)

        self.setStyleSheet(f"""
            QWidget#timerPopover {{
                background: {PALETTE['card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 8px;
            }}
            QLabel#timerPopoverLbl {{
                color: {PALETTE['label']};
                font-size: 9pt;
                font-weight: 700;
                background: transparent;
            }}
            QLabel#timerPopoverVal {{
                color: {PALETTE['accent']};
                font-size: 9pt;
                font-weight: 700;
                background: transparent;
            }}
            QLabel#timerPopoverRange {{
                color: {PALETTE['subtext']};
                font-size: 7pt;
                background: transparent;
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: #30394e;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {PALETTE['accent2']};
                border: none;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::sub-page:horizontal {{
                background: {PALETTE['accent2']};
                border-radius: 2px;
            }}
        """)

    def set_value(self, val: int):
        self._slider.blockSignals(True)
        self._slider.setValue(val)
        self._slider.blockSignals(False)
        self._val_lbl.setText(f"{val}s")

    def _on_value_changed(self, val: int):
        self._val_lbl.setText(f"{val}s")
        self.interval_changed.emit(val)

# ─── Main window ───────────────────────────────────────────────────────────────
class ProxyApp(QMainWindow):
    _status_sig = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proxer - Auto rotate proxies from CliProxy")
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

    def _set_defaults(self):
        # Set default values: Area Code = US, State = Florida, Network = ATT
        self._area_cb.setCurrentText("US")
        self._on_country_change("US")  # Manually trigger to populate state dropdown
        self._state_cb.setCurrentText("Florida")
        self._on_state_change("Florida")  # Manually trigger to populate city dropdown
        self._network_cb.setCurrentText("ATT")
        self._port_edit.setText("2000")
        self._fetch_btn.setFocus()

    # ── Build UI ────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget()
        root.setObjectName("central")
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(16, 16, 14, 10)
        main.setSpacing(0)

        # ── Cliproxy status auto-refresh timer ───────────────────────────────
        self._cliproxy_timer = QTimer(self)
        self._cliproxy_timer.setInterval(3000)
        self._cliproxy_timer.timeout.connect(self._check_cliproxy_silent)
        self._cliproxy_timer.start()

        self._tabs = QTabWidget()
        self._tabs.setObjectName("mainTabs")
        main.addWidget(self._tabs, 1)

        self._cliproxy_tab = QWidget()
        self._cliproxy_tab.setObjectName("cliproxyTab")
        self._tabs.addTab(self._cliproxy_tab, make_tab_icon("cliproxy"), "CliProxy")

        cliproxy_layout = QVBoxLayout(self._cliproxy_tab)
        cliproxy_layout.setContentsMargins(0, 10, 0, 0)
        cliproxy_layout.setSpacing(0)
        # NOTE: initial check is deferred to after blur overlay is created (end of _build_ui)

        # ── Content widget (everything below API bar) — will be blurred ──────
        self._content_widget = QWidget()
        self._content_widget.setObjectName("contentWidget")
        content_layout = QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # ── Form card (full width) ──────────────────────────────────────────────
        card = QWidget(); card.setObjectName("card")
        card_v = QVBoxLayout(card)
        card_v.setContentsMargins(20, 18, 20, 18)
        card_v.setSpacing(0)

        # Grid 1 — Location (3 cols)
        g1 = QGridLayout()
        g1.setHorizontalSpacing(12); g1.setVerticalSpacing(6)
        for i in range(3): g1.setColumnStretch(i, 1)

        self._fld_lbl(g1, "AREA CODE",        0, 1)
        self._fld_lbl(g1, "STATE / PROVINCE", 1, 1)
        self._fld_lbl(g1, "NETWORK / ISP",    2, 1)

        self._area_cb = AutoComboBox()
        self._area_cb.setObjectName("area_cb")
        self._area_cb.set_items(list(COUNTRY_DATA.keys()))
        self._area_cb.setPlaceholderText("e.g. US")
        self._area_cb.currentTextChanged.connect(self._on_country_change)
        g1.addWidget(self._area_cb, 2, 0)

        self._state_cb = AutoComboBox()
        self._state_cb.setPlaceholderText("Any")
        self._state_cb.currentTextChanged.connect(self._on_state_change)
        g1.addWidget(self._state_cb, 2, 1)

        self._network_cb = AutoComboBox()
        self._network_cb.set_items(ALL_NETWORKS)
        self._network_cb.setPlaceholderText("Any")
        g1.addWidget(self._network_cb, 2, 2)

        card_v.addLayout(g1)
        card_v.addSpacing(14)

        # Grid 2 — Query Options (3 cols)
        g2 = QGridLayout()
        g2.setHorizontalSpacing(12); g2.setVerticalSpacing(6)
        for i in range(3): g2.setColumnStretch(i, 1)

        # sec2 = QLabel("⚙️  Query Options"); sec2.setObjectName("section")
        # g2.addWidget(sec2, 0, 0, 1, 3)
        self._fld_lbl(g2, "PORT",              0, 1)
        self._fld_lbl(g2, "NUMBER OF RESULTS", 1, 1)
        self._fld_lbl(g2, "CITY",      2, 1)

        self._port_edit = QLineEdit()
        self._port_edit.setPlaceholderText("e.g. 2000")
        g2.addWidget(self._port_edit, 2, 0)

        self._number_edit = QLineEdit("1")
        g2.addWidget(self._number_edit, 2, 1)

        self._city_cb = AutoComboBox()
        self._city_cb.setPlaceholderText("Any")
        g2.addWidget(self._city_cb, 2, 2)

        card_v.addLayout(g2)
        content_layout.addWidget(card)
        content_layout.addSpacing(12)

        # ── Action bar (full width, 2 buttons) ───────────────────────────────
        act = QHBoxLayout(); act.setSpacing(10)

        self._geo_check_btn = QPushButton("🌐 Lookup")
        self._geo_check_btn.setObjectName("geoCheckBtn")
        self._geo_check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._geo_check_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._geo_check_btn.setFixedHeight(34)
        # self._geo_check_btn.setStyleSheet("QPushButton {  }")
        self._geo_check_btn.setToolTip(
            "Ping by target port"
        )
        self._geo_check_btn.clicked.connect(self._do_geo_check)

        self._fetch_btn = QPushButton("🔍 Retrieve")
        self._fetch_btn.setObjectName("fetchBtn")
        self._fetch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fetch_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._fetch_btn.setFixedHeight(33)
        self._fetch_btn.setStyleSheet("QPushButton { padding-left: 6px; padding-right: 6px; }")
        self._fetch_btn.setToolTip(
            "Fetch new proxy for the selected options"
        )
        self._fetch_btn.clicked.connect(self._fetch)

        self._clear_cache_btn = QPushButton("🗑 Reset")
        self._clear_cache_btn.setObjectName("clearBtn")
        self._clear_cache_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_cache_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._clear_cache_btn.setFixedHeight(34)
        self._clear_cache_btn.setToolTip(
            "Clear all saved proxies and stats"
        )
        self._clear_cache_btn.clicked.connect(self._clear_cache)

        self._auto_check_btn = QPushButton()
        self._auto_check_btn.setObjectName("autoCheckBtn")
        self._auto_check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._auto_check_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._auto_check_btn.setFixedHeight(34)
        self._auto_check_btn.setFixedWidth(140)
        auto_check_layout = QHBoxLayout(self._auto_check_btn)
        auto_check_layout.setContentsMargins(10, 0, 0, 0)
        auto_check_layout.setSpacing(0)
        self._auto_check_label = QLabel("⏰ Auto rotate:")
        self._auto_check_label.setStyleSheet(f"color: {PALETTE['label']}; background: transparent;")
        self._auto_check_status = QLabel("OFF")
        self._auto_check_status.setStyleSheet(f"color: {PALETTE['subtext']}; background: transparent;")
        auto_check_layout.addWidget(self._auto_check_label)
        auto_check_layout.addSpacing(3)
        auto_check_layout.addWidget(self._auto_check_status)
        self._auto_check_btn.clicked.connect(self._toggle_auto_check)

        self._timer_interval_btn = QPushButton("⏱")
        self._timer_interval_btn.setObjectName("timerIntervalBtn")
        self._timer_interval_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._timer_interval_btn.setFixedSize(34, 34)
        self._timer_interval_btn.setEnabled(False)
        self._timer_interval_btn.clicked.connect(self._show_timer_popover)

        self._bulk_check_btn = QPushButton("⚡Bulk check")
        self._bulk_check_btn.setObjectName("bulkCheckBtn")
        self._bulk_check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._bulk_check_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._bulk_check_btn.setFixedHeight(34)
        self._bulk_check_btn.setEnabled(False)
        self._bulk_check_btn.setToolTip(
            "Check status of all proxies"
        )
        self._bulk_check_btn.clicked.connect(self._bulk_check)

        self._bulk_refresh_btn = QPushButton("🔄️ Bulk refresh")
        self._bulk_refresh_btn.setObjectName("bulkRefreshBtn")
        self._bulk_refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._bulk_refresh_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._bulk_refresh_btn.setFixedHeight(34)
        self._bulk_refresh_btn.setEnabled(False)
        self._bulk_refresh_btn.setToolTip(
            "Refresh new ones for all proxies"
        )
        self._bulk_refresh_btn.clicked.connect(self._bulk_refresh)

        self._bulk_widget = QWidget()
        self._bulk_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        bulk_layout = QHBoxLayout(self._bulk_widget)
        bulk_layout.setSpacing(0)
        bulk_layout.setContentsMargins(0, 0, 0, 0)
        bulk_layout.addWidget(self._bulk_check_btn)
        bulk_layout.addWidget(self._bulk_refresh_btn)

        geo_fetch_widget = QWidget()
        geo_fetch_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        geo_fetch_layout = QHBoxLayout(geo_fetch_widget)
        geo_fetch_layout.setSpacing(0)
        geo_fetch_layout.setContentsMargins(0, 0, 0, 0)
        geo_fetch_layout.addWidget(self._geo_check_btn, 1)
        geo_fetch_layout.addWidget(self._fetch_btn, 2)
        act.addWidget(geo_fetch_widget, 3)
        act.addWidget(self._clear_cache_btn, 1)
        act.addWidget(self._bulk_widget, 2)

        self._auto_check_container = QWidget()
        self._auto_check_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        auto_check_group = QHBoxLayout(self._auto_check_container)
        auto_check_group.setSpacing(0)
        auto_check_group.setContentsMargins(0, 0, 0, 0)
        auto_check_group.addWidget(self._auto_check_btn)
        auto_check_group.addWidget(self._timer_interval_btn)
        act.addWidget(self._auto_check_container, 0)

        content_layout.addLayout(act)
        content_layout.addSpacing(12)

        # ── Result section ────────────────────────────────────────────────────
        self._proxy_search = QLineEdit()
        self._proxy_search.setPlaceholderText("🔍 Search proxies...")
        self._proxy_search.setFixedHeight(26)
        self._proxy_search.setMaximumWidth(200)
        self._proxy_search.setStyleSheet(toolbar_search_style())
        self._proxy_search.textChanged.connect(self._apply_proxy_filter)

        self._sort_btn = QPushButton("📐 Sort")
        self._sort_btn.setObjectName("sortBtn")
        self._sort_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sort_btn.setFixedHeight(26)
        self._sort_btn.setFixedWidth(68)
        self._sort_btn.setStyleSheet(toolbar_button_style())
        self._sort_btn.clicked.connect(self._show_sort_popover)
        self._current_sort = None   # None | 'country' | 'port' | 'ping'

        self._export_btn = QPushButton("⬇ Export")
        self._export_btn.setObjectName("exportBtn")
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_btn.setFixedHeight(26)
        self._export_btn.setFixedWidth(74)
        self._export_btn.setStyleSheet(toolbar_button_style())
        self._export_btn.clicked.connect(self._show_export_popover)
        self._export_popover = self._make_export_popover()

        self._stats_btn = QPushButton("📊 Stats")
        self._stats_btn.setObjectName("statsBtn")
        self._stats_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stats_btn.setFixedHeight(26)
        self._stats_btn.setFixedWidth(74)
        self._stats_btn.setStyleSheet(toolbar_button_style(accent=True))
        self._stats_btn.clicked.connect(self._show_stats_modal)
        self._stats_modal: StatsModal | None = None

        res_bar = QHBoxLayout()
        res_bar.setSpacing(6)
        self._res_count_lbl = QLabel("Total: 0 proxies")
        self._res_count_lbl.setStyleSheet(
            f"color: {PALETTE['accent2']}; font-size: 8pt; font-weight: 700; background: transparent;")

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(
            f"color: {PALETTE['subtext']}; font-size: 8pt; background: transparent;")

        res_bar.addWidget(self._proxy_search)
        res_bar.addWidget(self._sort_btn)
        res_bar.addWidget(self._export_btn)
        res_bar.addWidget(self._stats_btn)
        res_bar.addStretch()
        res_bar.addWidget(self._res_count_lbl)
        content_layout.addLayout(res_bar)
        content_layout.addSpacing(4)

        # Scroll area containing a VBox of proxy cards
        self._scroll = QScrollArea()
        self._scroll.setObjectName("resultScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._result_container = QWidget()
        self._result_container.setStyleSheet(f"background: {PALETTE['entry_bg']};")
        self._result_layout = QVBoxLayout(self._result_container)
        self._result_layout.setContentsMargins(10, 10, 10, 10)
        self._result_layout.setSpacing(8)
        self._result_layout.addStretch()

        self._scroll.setWidget(self._result_container)
        content_layout.addWidget(self._scroll, 1)

        cliproxy_layout.addWidget(self._content_widget, 1)

        # ── Footer status bar ─────────────────────────────────────────────────
        footer = QHBoxLayout()
        footer.setContentsMargins(4, 0, 4, 0)
        footer.addWidget(self._status_lbl)
        footer.addStretch()
        cliproxy_layout.addLayout(footer)

        # Blur overlay stays inside the CliProxy tab so the Ping tab remains usable.
        self._ping_tab = PingTab()
        self._tabs.addTab(self._ping_tab, make_tab_icon("ping"), "Proxy")
        self._check_port_tab = CheckPortTab()
        self._tabs.addTab(self._check_port_tab, make_tab_icon("check_port"), "Host")

        self._blur_overlay = BlurOverlay(self._cliproxy_tab)
        self._cliproxy_btn = self._blur_overlay.btn
        self._blur_overlay.btn_clicked.connect(self._cliproxy_btn_clicked)
        self._blur_effect = QGraphicsBlurEffect()
        self._blur_effect.setBlurRadius(8)
        self._content_widget.setGraphicsEffect(self._blur_effect)
        self._blur_effect.setEnabled(False)   # start unblurred

        # Sort popover (created after _build_ui palette is ready)
        self._sort_popover = self._make_sort_popover()

        # Load cached proxies on startup
        self._load_cached_proxies()

        # Initial Cliproxy check — runs immediately now that overlay is ready
        self._check_cliproxy_silent()

    # ── Sort popover ─────────────────────────────────────────────────────────
    def _make_sort_popover(self) -> QWidget:
        pop = QWidget(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        pop.setObjectName("sortPopover")
        pop.setFixedWidth(210)
        layout = QVBoxLayout(pop)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        options = [
            ("country", "🌍  Sort by Country"),
            ("port",    "🔢  Sort by Proxy Number"),
            ("ping",    "⚡  Sort by Response Time"),
        ]
        self._sort_action_btns = {}
        for key, label in options:
            btn = QPushButton(label)
            btn.setObjectName("sortOptionBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.setCheckable(True)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {PALETTE['text']}; "
                f"border: none; border-radius: 6px; padding: 0 10px; "
                f"font-size: 9pt; text-align: left; }}"
                f"QPushButton:hover {{ background: {PALETTE['panel']}; color: #fff; }}"
                f"QPushButton:checked {{ background: {PALETTE['accent']}; color: #fff; }}"
            )
            btn.clicked.connect(lambda checked, k=key: self._apply_sort(k))
            layout.addWidget(btn)
            self._sort_action_btns[key] = btn

        # Divider + clear option
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {PALETTE['border']}; margin: 2px 4px;")
        layout.addWidget(line)

        clear_btn = QPushButton("✕  Clear sort")
        clear_btn.setObjectName("sortOptionBtn")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setFixedHeight(28)
        clear_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {PALETTE['subtext']}; "
            f"border: none; border-radius: 6px; padding: 0 10px; "
            f"font-size: 9pt; text-align: left; }}"
            f"QPushButton:hover {{ background: {PALETTE['border']}; color: {PALETTE['text']}; }}"
        )
        clear_btn.clicked.connect(self._clear_sort)
        layout.addWidget(clear_btn)

        pop.setStyleSheet(
            f"QWidget#sortPopover {{ background: {PALETTE['card']}; "
            f"border: 1px solid {PALETTE['border']}; border-radius: 8px; }}"
        )
        return pop

    def _show_sort_popover(self):
        btn = self._sort_btn
        pos = btn.mapToGlobal(QPoint(0, btn.height() + 4))
        self._sort_popover.move(pos)
        self._sort_popover.show()

    def _apply_sort(self, key: str):
        self._sort_popover.hide()
        self._current_sort = key
        # Update checked state on buttons
        for k, b in self._sort_action_btns.items():
            b.setChecked(k == key)
        # Update sort button label to show active sort
        labels = {"country": "🌍 Sort", "port": "🔢 Sort", "ping": "⚡ Sort"}
        self._sort_btn.setText(labels.get(key, "⇅ Sort"))
        self._sort_btn.setStyleSheet(toolbar_button_style(active=True))
        self._rebuild_sorted_cards()

    def _clear_sort(self):
        self._sort_popover.hide()
        self._current_sort = None
        for b in self._sort_action_btns.values():
            b.setChecked(False)
        self._sort_btn.setText("📐 Sort")
        self._sort_btn.setStyleSheet(toolbar_button_style())
        self._rebuild_sorted_cards()

    # ── Export popover ───────────────────────────────────────────────────────
    def _make_export_popover(self) -> QWidget:
        pop = QWidget(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        pop.setObjectName("sortPopover")
        pop.setFixedWidth(210)
        layout = QVBoxLayout(pop)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        formats = [
            ("json", "📄 Export as JSON"),
            ("csv",  "📊 Export as CSV"),
            ("txt",  "📝 Export as TXT"),
        ]
        for fmt, label in formats:
            btn = QPushButton(label)
            btn.setObjectName("sortOptionBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {PALETTE['text']}; "
                f"border: none; border-radius: 6px; padding: 0 10px; "
                f"font-size: 9pt; text-align: left; }}"
                f"QPushButton:hover {{ background: {PALETTE['panel']}; color: #fff; }}"
            )
            btn.clicked.connect(lambda checked, f=fmt: self._export_proxies(f))
            layout.addWidget(btn)

        pop.setStyleSheet(
            f"QWidget#sortPopover {{ background: {PALETTE['card']}; "
            f"border: 1px solid {PALETTE['border']}; border-radius: 8px; }}"
        )
        return pop

    def _show_export_popover(self):
        btn = self._export_btn
        pos = btn.mapToGlobal(QPoint(0, btn.height() + 4))
        self._export_popover.move(pos)
        self._export_popover.show()

    # ── Stats modal ──────────────────────────────────────────────────────────
    def _get_all_proxy_cards(self) -> list:
        """Return all ProxyCard widgets currently in the result layout."""
        cards = []
        for i in range(self._result_layout.count() - 1):
            item = self._result_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), ProxyCard):
                cards.append(item.widget())
        return cards

    def _show_stats_modal(self):
        if self._stats_modal is None or not self._stats_modal.isVisible():
            self._stats_modal = StatsModal(
                get_cards_fn=self._get_all_proxy_cards,
                parent=self,
            )
        self._stats_modal.show()
        self._stats_modal.raise_()
        self._stats_modal.activateWindow()

    def _get_visible_proxy_dicts(self) -> list:
        """Return proxy dicts for all currently visible proxy cards."""
        proxies = []
        for i in range(self._result_layout.count() - 1):
            widget = self._result_layout.itemAt(i).widget()
            if widget and isinstance(widget, ProxyCard) and widget.isVisible():
                proxies.append(dict(widget.proxy_dict))
        return proxies

    def _export_proxies(self, fmt: str):
        self._export_popover.hide()
        proxies = self._get_visible_proxy_dicts()
        if not proxies:
            QMessageBox.information(self, "Export", "No proxies to export.")
            return

        filters = {
            "json": "JSON Files (*.json)",
            "csv":  "CSV Files (*.csv)",
            "txt":  "Text Files (*.txt)",
        }
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Proxy List", f"proxies.{fmt}", filters[fmt]
        )
        if not path:
            return

        try:
            if fmt == "json":
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(proxies, f, indent=2, ensure_ascii=False)

            elif fmt == "csv":
                # Collect all keys across all proxies for header
                all_keys = []
                seen = set()
                for p in proxies:
                    for k in p:
                        if k not in seen:
                            all_keys.append(k)
                            seen.add(k)
                with open(path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
                    writer.writeheader()
                    writer.writerows(proxies)

            elif fmt == "txt":
                with open(path, "w", encoding="utf-8") as f:
                    for p in proxies:
                        ip   = p.get("ip", p.get("host", ""))
                        port = p.get("port", "")
                        f.write(f"{ip}:{port}\n")

            QMessageBox.information(
                self, "Export",
                f"Exported {len(proxies)} proxy(ies) to:\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def _sort_key(self, proxy_dict: dict):
        """Return a sort key for the given proxy dict based on current sort mode."""
        if self._current_sort == "country":
            return (proxy_dict.get("country", "") or "").upper()
        elif self._current_sort == "port":
            try:
                return int(proxy_dict.get("port", 0) or 0)
            except (ValueError, TypeError):
                return 0
        elif self._current_sort == "ping":
            val = proxy_dict.get("ping_ms", None)
            if val is None:
                return float("inf")   # no ping goes to end
            try:
                return float(val)
            except (ValueError, TypeError):
                return float("inf")
        return 0

    def _rebuild_sorted_cards(self):
        """Re-order existing proxy cards in the layout according to current sort."""
        # Collect all proxy card widgets
        cards: list[ProxyCard] = []
        for i in range(self._result_layout.count() - 1):  # exclude stretch
            widget = self._result_layout.itemAt(i).widget()
            if widget and isinstance(widget, ProxyCard):
                cards.append(widget)

        if not cards:
            return

        if self._current_sort is not None:
            cards.sort(key=lambda c: self._sort_key(c.proxy_dict))

        # Remove all card widgets from layout (keep stretch)
        for card in cards:
            self._result_layout.removeWidget(card)

        # Re-insert in sorted order before the stretch
        stretch_idx = self._result_layout.count() - 1
        for i, card in enumerate(cards):
            self._result_layout.insertWidget(stretch_idx + i, card)

        # Re-apply current search filter so visibility is preserved
        self._apply_proxy_filter(self._proxy_search.text())

    # ── Helper label factories ───────────────────────────────────────────────
    def _sec_lbl(self, grid, text, col, row, span=1):
        lbl = QLabel(text); lbl.setObjectName("section")
        grid.addWidget(lbl, row, col, 1, span)

    def _fld_lbl(self, grid, text, col, row):
        lbl = QLabel(text); lbl.setObjectName("field")
        grid.addWidget(lbl, row, col)

    # ── Country cascade ──────────────────────────────────────────────────────
    def _on_country_change(self, text: str):
        data     = COUNTRY_DATA.get(text.strip().upper(), {})
        states   = data.get("states",   [])
        networks = data.get("networks", ALL_NETWORKS)
        self._state_cb.set_items(states)
        self._network_cb.set_items(networks)
        # Reset city when country changes
        self._city_cb.set_items([])

    def _on_state_change(self, text: str):
        country  = self._area_cb.current_value().strip().upper()
        data     = COUNTRY_DATA.get(country, {})
        cities_map = data.get("cities", {})
        cities   = cities_map.get(text.strip(), [])
        self._city_cb.set_items(cities)

    def _is_cliproxy_running(self) -> bool:
        """Return True if Cliproxy.exe process is running."""
        import subprocess
        try:
            output = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq Cliproxy.exe"],
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            ).decode(errors="ignore")
            return "cliproxy" in output.lower()
        except Exception:
            return False

    def _update_cliproxy_btn(self, running: bool):
        """Update button label + border color based on Cliproxy running state."""
        if running:
            self._cliproxy_btn.setText("CliProxy: On")
            self._cliproxy_btn.setToolTip("CliProxy is running ✔")
        else:
            self._cliproxy_btn.setText("Open CliProxy")
            self._cliproxy_btn.setToolTip("CliProxy is not running — click to open")
        self._cliproxy_btn.setProperty("running", "true" if running else "false")
        self._cliproxy_btn.style().unpolish(self._cliproxy_btn)
        self._cliproxy_btn.style().polish(self._cliproxy_btn)
        self._apply_cliproxy_lock(running)

        # Auto-enable auto check on initial check if CliProxy is running
        if running and not self._initial_cliproxy_check_done:
            self._initial_cliproxy_check_done = True
            self._auto_check_enabled = True
            self._auto_check_pending = 0
            self._auto_check_status.setText("ON")
            self._auto_check_status.setStyleSheet(f"color: {PALETTE['success']}; background: transparent;")
            self._auto_check_btn.setProperty("checked", True)
            self._auto_check_btn.style().unpolish(self._auto_check_btn)
            self._auto_check_btn.style().polish(self._auto_check_btn)
            self._update_all_proxy_cards_visibility()
            # Start the auto check timer if there are proxies
            if self._result_layout.count() > 1:  # exclude stretch
                self._auto_check_timer.start(self._auto_check_interval * 1000)
                self._countdown_remaining = self._auto_check_interval
                self._countdown_timer.start(1000)  # Update every second
                self._update_countdown_display()

        # Update auto check button state based on Cliproxy status
        self._update_auto_check_btn_state()

    def _apply_cliproxy_lock(self, running: bool):
        """Blur + disable content area when Cliproxy is not running."""
        if not hasattr(self, '_blur_overlay'):
            return
        if running:
            # Remove blur and overlay
            self._blur_effect.setEnabled(False)
            self._blur_overlay.hide()
        else:
            # Apply blur and show overlay
            self._blur_effect.setEnabled(True)
            # Resize overlay to cover only the content widget area
            cw = self._content_widget
            self._blur_overlay.setGeometry(cw.geometry())
            self._blur_overlay.raise_()
            self._blur_overlay.show()
            # Defer geometry update to ensure proper sizing after layout
            QTimer.singleShot(0, lambda: self._blur_overlay.setGeometry(cw.geometry()))

    def _check_cliproxy_silent(self):
        """Auto-check called by timer — updates button only, no status bar."""
        self._update_cliproxy_btn(self._is_cliproxy_running())

    def _open_cliproxy(self):
        """Launch Cliproxy.exe via cmd in background."""
        import subprocess
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "", "Cliproxy.exe"],
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                shell=False,
            )
            self._set_status("⏳ Opening CliProxy...", PALETTE['label'])
            # Check status after 3 seconds to see if CliProxy started successfully
            QTimer.singleShot(3000, self._check_cliproxy_status_after_open)
        except Exception as e:
            self._set_status(f"✖ Cannot open CliProxy: {e}", "#e05252")

    def _cliproxy_btn_clicked(self):
        """Called when user clicks the CliProxy button."""
        if self._is_cliproxy_running():
            # Already running — just update status bar info
            self._set_status("✔ CliProxy is already running", PALETTE['success'])
        else:
            # Not running — try to open it
            self._open_cliproxy()

    def _check_cliproxy_status_after_open(self):
        """Check CliProxy status after attempting to open it and update status bar."""
        if self._is_cliproxy_running():
            self._set_status("✔ CliProxy opened successfully", PALETTE['success'])
        else:
            self._set_status("✖ CliProxy failed to open or is not responding", "#e05252")

    # ── Geo Check (action-bar button) ────────────────────────────────────────
    def _do_geo_check(self):
        """Ping the port in the PORT input, then query ip-api.com for geo info."""
        port_str = self._port_edit.text().strip()
        if not port_str:
            self._set_status("⚠ Enter a port number first.", PALETTE['warning'])
            return
        try:
            port_int = int(port_str)
            if not (1 <= port_int <= 65535):
                raise ValueError
        except ValueError:
            self._set_status("⚠ Invalid port number (1–65535).", PALETTE['warning'])
            return

        self._geo_check_btn.setEnabled(False)
        self._set_status(f"🌐 Lookup port {port_int}…", PALETTE['subtext'])

        self._geo_thread = QThread()
        self._geo_worker = GeoCheckWorker(f"{current_ipv4()}:{port_int}")
        self._geo_worker.moveToThread(self._geo_thread)
        self._geo_thread.started.connect(self._geo_worker.run)
        self._geo_worker.result.connect(self._on_geo_result)
        self._geo_worker.result.connect(self._geo_thread.quit)
        self._geo_thread.finished.connect(self._geo_thread.deleteLater)
        self._geo_thread.start()

    def _on_geo_result(
        self,
        alive: bool,
        elapsed_ms: float,
        origin_ip: str,
        country: str,
        country_code: str,
        region_name: str,
        city: str,
        isp: str,
        error: str,
    ):
        self._geo_check_btn.setEnabled(True)
        port_str = self._port_edit.text().strip()

        if not alive:
            detail = f"  ({error})" if error else ""
            self._set_status(
                f"❌ Port {port_str} dead", PALETTE['error']
            )
            return

        # ── Port is alive: update the matching card (by port) ──────────────
        self._set_status(
            f"✅ Port {port_str} live",
            PALETTE['success'],
        )

        # Build geo update dict
        updates = {
            "country":     country_code,
            "state":       region_name,
            "city":        city,
            "isp":         isp,
            "response_ip": origin_ip,
            "ping_ms":     round(elapsed_ms, 1),
        }

        # Persist to data file and refresh the matching card's UI.
        # Use port-only match since geo-check cards may not have an ip field.
        update_proxy_in_file(ip=origin_ip, port=port_str, updates=updates)
        # Also try host-based key (127.0.0.1:port) and empty-ip key
        update_proxy_in_file(ip="127.0.0.1", port=port_str, updates=updates)
        update_proxy_in_file(ip="", port=port_str, updates=updates)

        # Update every card whose port matches
        found = False
        for i in range(self._result_layout.count() - 1):
            item = self._result_layout.itemAt(i)
            if not item:
                continue
            card = item.widget()
            if not isinstance(card, ProxyCard):
                continue
            _, card_port = card._ip_port()
            if card_port == port_str:
                card.update_geo_data(
                    elapsed_ms=elapsed_ms,
                    origin_ip=origin_ip,
                    country_code=country_code,
                    region_name=region_name,
                    city=city,
                    isp=isp,
                )
                found = True

        if not found:
            # No existing card — create a new one
            proxy_dict = {
                "port":    port_str,
                "country": country_code,
                "state":   region_name,
                "city":    city,
                "isp":     isp,
                "_city":   city,
                "ping_ms": round(elapsed_ms, 1),
                "response_ip": origin_ip,
            }
            save_proxies_to_file([proxy_dict])
            self._load_cached_proxies()

    def _fetch(self):
        country = self._area_cb.current_value().upper()
        if not country:
            QMessageBox.warning(self, "Missing field",
                                "Please enter an Area Code (country).")
            return

        port_str = self._port_edit.text().strip()

        params = {
            "country": country,
            "state":   self._state_cb.current_value(),
            "city":    self._city_cb.current_value() or "",
            "postal":  "",
            "isp":     self._network_cb.current_value(),
            "start":   port_str or "2000",
            "num":     self._number_edit.text().strip() or "1",
            "ip":      "",
        }

        # Stash form params so they can be embedded into the saved proxy dict
        self._last_fetch_params = params

        # ── Pre-check: ping the port first ────────────────────────────────────
        if port_str:
            try:
                port_int = int(port_str)
                if 1 <= port_int <= 65535:
                    self._set_status(f"⏳ Checking port {port_int}…", PALETTE['subtext'])
                    self._fetch_btn.setEnabled(False)
                    self._pre_check_thread = QThread()
                    self._pre_check_worker = PortPreCheckWorker("127.0.0.1", port_int)
                    self._pre_check_worker.moveToThread(self._pre_check_thread)
                    self._pre_check_thread.started.connect(self._pre_check_worker.run)
                    self._pre_check_worker.result.connect(self._on_port_pre_check)
                    self._pre_check_worker.result.connect(self._pre_check_thread.quit)
                    self._pre_check_thread.finished.connect(self._pre_check_thread.deleteLater)
                    self._pre_check_thread.start()
                    return
            except ValueError:
                pass  # invalid port — fall through to API fetch

        # No valid port entered → go straight to API
        self._do_api_fetch(params)

    def _on_port_pre_check(self, alive: bool, elapsed_ms: float, peer_ip: str, host: str, port: int):
        """Called after TCP pre-check of the port entered in the form."""
        params = self._last_fetch_params

        if alive:
            # Port is alive → build a proxy dict from form metadata + the live port
            self._set_status(f"✅ Port {port} alive ({elapsed_ms:.0f} ms) — added to list", PALETTE['success'])
            proxy_dict = {
                "ip":      peer_ip or host,
                "port":    str(port),
                "country": params.get("country", ""),
                "state":   params.get("state",   ""),
                "city":    params.get("city",    ""),
                "isp":     params.get("isp",     ""),
                "_city":   params.get("city",    ""),
                "ping_ms": round(elapsed_ms, 1),
            }
            save_proxies_to_file([proxy_dict])
            self._load_cached_proxies()
            if self._current_sort is not None:
                self._rebuild_sorted_cards()
            self._fetch_btn.setEnabled(True)
        else:
            # Port is dead → fetch from API as usual
            self._set_status(f"⚠ Port {port} dead — fetching from API…", PALETTE['subtext'])
            self._do_api_fetch(params)

    def _do_api_fetch(self, params: dict):
        """Start the actual API network request."""
        self._fetch_btn.setEnabled(False)
        self._set_status("⏳ Fetching…", PALETTE['subtext'])

        self._thread = QThread()
        self._worker = FetchWorker(params, API_BASE)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._handle_response)
        self._worker.error.connect(self._show_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _handle_response(self, resp):
        self._fetch_btn.setEnabled(True)
        code = resp.status_code
        content_type = resp.headers.get('content-type', '').lower()

        if code == 200:
            self._set_status(f"✓  {code} OK", PALETTE['success'])
            try:
                text = resp.text.strip()
                data = None

                # Try JSON parse first
                if 'json' in content_type:
                    try:
                        data = resp.json()
                        if isinstance(data, str):
                            # JSON string containing "ip:port"
                            ip, port = data.split(':', 1) if ':' in data else (data, '')
                            data = [{"ip": ip, "port": port}]
                    except Exception:
                        data = None  # fallback to plain text

                # Plain text / JSON parse failed → try "ip:port" format
                if data is None:
                    if ':' in text:
                        # Could be multiple lines of ip:port
                        proxies = []
                        for line in text.splitlines():
                            line = line.strip()
                            if ':' in line:
                                ip, port = line.split(':', 1)
                                proxies.append({"ip": ip.strip(), "port": port.strip()})
                        data = proxies if proxies else None

                if data is None:
                    self._add_info_row(f"Unexpected response: {text[:200]}")
                    self._set_status("⚠  Unexpected format", PALETTE['subtext'])
                    return

                self._render_json(data, resp.url)
            except Exception as e:
                print(f"[DEBUG] Parse error: {e}")
                print(f"[DEBUG] Response text: {resp.text[:500]}...")
                self._add_info_row(f"Parse error: {str(e)[:100]}...")
                self._set_status("✗  Parse error", PALETTE['error'])
        else:
            print(f"[DEBUG] HTTP {code} error: {resp.text[:500]}...")
            self._add_info_row(f"HTTP {code}: {resp.text[:200]}...", is_error=True)
            self._set_status(f"✗  HTTP {code}", PALETTE['error'])

    def _show_error(self, msg: str):
        self._fetch_btn.setEnabled(True)
        self._set_status(f"✗ {msg}", PALETTE['error'])

    # ── Result rendering ─────────────────────────────────────────────────────
    def _clear_rows(self):
        """Remove all proxy cards from the result layout (keep trailing stretch)."""
        while self._result_layout.count() > 1:
            item = self._result_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._result_container.update()

    def _render_json(self, data, url: str):
        proxies_to_save = []
        params = getattr(self, "_last_fetch_params", {})

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    proxies_to_save.append(item)
        elif isinstance(data, dict):
            proxies_to_save.append(data)

        if not proxies_to_save:
            self._set_status("⚠  No proxy in response", PALETTE['subtext'])
            return

        # Embed form params as metadata into each proxy dict before saving
        for p in proxies_to_save:
            p.setdefault("country", params.get("country", ""))
            p.setdefault("state",   params.get("state",   ""))
            p.setdefault("city",    params.get("city",    ""))
            p.setdefault("isp",     params.get("isp",     ""))
            p["_city"] = params.get("city", "")

        save_proxies_to_file(proxies_to_save)
        # Reload full list so UI is consistent with cache
        self._load_cached_proxies()
        # Re-apply sort if one is active
        if self._current_sort is not None:
            self._rebuild_sorted_cards()
        self._set_status(f"✓ Added {len(proxies_to_save)} proxy(ies)", PALETTE['success'])

    def _apply_proxy_filter(self, text: str = ""):
        """Show/hide proxy cards based on search text."""
        q = text.strip().lower()
        visible = 0
        total = 0
        for i in range(self._result_layout.count() - 1):  # exclude trailing stretch
            widget = self._result_layout.itemAt(i).widget()
            if widget is None or not isinstance(widget, ProxyCard):
                continue
            total += 1
            if not q:
                widget.show()
                visible += 1
            else:
                d = widget.proxy_dict
                haystack = " ".join(str(v) for v in [
                    d.get("ip", d.get("host", "")),
                    d.get("port", ""),
                    d.get("country", ""),
                    d.get("state", ""),
                    d.get("city", ""),
                    d.get("isp", d.get("network", "")),
                ]).lower()
                match = q in haystack
                widget.setVisible(match)
                if match:
                    visible += 1
        if q and total:
            self._res_count_lbl.setText(f"Total: {visible}/{total} proxies")
        else:
            self._res_count_lbl.setText(f"Total: {total} proxies")

    def _load_cached_proxies(self):
        """Load and display cached proxies."""
        cached = load_proxies_from_file()
        self._clear_rows()
        if cached:
            for proxy in cached:
                self._add_proxy_card(proxy, auto_check=False)  # never auto-check on load
        # Re-apply current search filter (also updates count label)
        self._apply_proxy_filter(self._proxy_search.text())
        self._update_auto_check_btn_state(len(cached))

    def _add_info_row(self, text: str, color: str = None, is_error: bool = False):
        lbl = QLabel(text)
        lbl.setObjectName("proxyText")
        lbl.setWordWrap(True)
        c = color or (PALETTE['error'] if is_error else PALETTE['subtext'])
        lbl.setStyleSheet(f"color: {c}; font-size: 9pt; background: transparent; padding: 4px 8px;")
        self._result_layout.insertWidget(self._result_layout.count() - 1, lbl)

    def _add_proxy_card(self, proxy_dict: dict, auto_check: bool = False):
        card = ProxyCard(proxy_dict, lambda: API_BASE)
        card.deleted.connect(self._on_card_deleted)
        card.refreshed.connect(self._on_card_refreshed)
        card.auto_check_done.connect(self._on_auto_check_card_done)
        card.update_button_visibility(self._auto_check_enabled)  # Set initial visibility
        self._result_layout.insertWidget(self._result_layout.count() - 1, card)
        count = self._result_layout.count() - 1  # exclude stretch
        self._update_auto_check_btn_state(count)
        # Only auto-check if explicitly requested (new proxy fetched, not loaded from file)
        if auto_check and not proxy_dict.get("ping_ms"):
            card._do_check()

    def _on_card_deleted(self, card: ProxyCard):
        self._result_layout.removeWidget(card)
        card.deleteLater()
        # Update count via filter (keeps search active)
        count = self._result_layout.count() - 1  # exclude stretch
        self._apply_proxy_filter(self._proxy_search.text())
        self._update_auto_check_btn_state(count)

    def _on_card_refreshed(self, old_card: ProxyCard, new_proxy: dict):
        """Replace old card in-place with a new one after refresh."""
        stats_collector.record_refresh_success()
        idx = self._result_layout.indexOf(old_card)
        self._result_layout.removeWidget(old_card)
        old_card.deleteLater()

        new_card = ProxyCard(new_proxy, lambda: API_BASE)
        new_card.deleted.connect(self._on_card_deleted)
        new_card.refreshed.connect(self._on_card_refreshed)
        new_card.auto_check_done.connect(self._on_auto_check_card_done)
        new_card.update_button_visibility(self._auto_check_enabled)
        self._result_layout.insertWidget(idx, new_card)

        # After a refresh, do a fast TCP port check instead of a full httpbin tunnel
        # check, so we confirm the port is open without depending on an external site.
        # If auto-check is active, a failed TCP check will trigger another refresh cycle.
        if self._auto_check_enabled:
            new_card._auto_check_triggered = True
            new_card._do_check()   # auto-check mode: full check so failed → refresh again
        else:
            new_card._do_tcp_check()   # manual refresh: just verify the port is open

    # ── Status (thread-safe) ─────────────────────────────────────────────────
    def _set_status(self, msg: str, color: str):
        self._status_sig.emit(msg, color)

    def _apply_status(self, msg: str, color: str):
        # Don't override countdown display when auto-check is enabled
        if not self._auto_check_enabled:
            self._status_lbl.setText(msg)
            self._status_lbl.setStyleSheet(
                f"color: {color}; font-size: 8pt; background: transparent;")
        # When auto-check is enabled, only update if it's not a countdown message
        elif not msg.startswith("⏰"):
            # Temporarily show the message, but countdown will override it
            self._status_lbl.setText(msg)
            self._status_lbl.setStyleSheet(
                f"color: {color}; font-size: 8pt; background: transparent;")

    def _toggle_auto_check(self):
        """Toggle automatic proxy checking."""
        if not self._is_cliproxy_running():
            # Prevent enabling auto check if Cliproxy is not running
            self._set_status("⚠ Auto check requires CliProxy to be running", PALETTE['warning'])
            return
        self._auto_check_enabled = not self._auto_check_enabled
        if self._auto_check_enabled:
            self._auto_check_pending = 0
            self._auto_check_timer.start(self._auto_check_interval * 1000)
            self._countdown_remaining = self._auto_check_interval
            self._countdown_timer.start(1000)  # Update every second
            self._auto_check_status.setText("ON")
            self._auto_check_status.setStyleSheet(f"color: {PALETTE['success']}; background: transparent;")
            self._auto_check_btn.setProperty("checked", True)
            self._update_countdown_display()
        else:
            self._auto_check_pending = 0
            self._auto_check_timer.stop()
            self._countdown_timer.stop()
            self._auto_check_status.setText("OFF")
            self._auto_check_status.setStyleSheet(f"color: {PALETTE['subtext']}; background: transparent;")
            self._auto_check_btn.setProperty("checked", False)
            self._set_status("", PALETTE['subtext'])  # Clear countdown display
        # Show/hide bulk buttons and stretch fetch button accordingly
        self._bulk_widget.setVisible(not self._auto_check_enabled)

        # Force style update
        self._auto_check_btn.style().unpolish(self._auto_check_btn)
        self._auto_check_btn.style().polish(self._auto_check_btn)

        # Update visibility of buttons on all proxy cards
        self._update_all_proxy_cards_visibility()

    def _update_countdown(self):
        """Update countdown timer display."""
        self._countdown_remaining -= 1
        if self._countdown_remaining < 0:
            self._countdown_remaining = 0
        self._update_countdown_display()

    def _update_countdown_display(self):
        """Update the countdown display in status label."""
        if self._auto_check_enabled:
            self._status_lbl.setText(f"⏰ Next check in {self._countdown_remaining}s")
            self._status_lbl.setStyleSheet(f"color: {PALETTE['accent']}; font-size: 8pt; background: transparent;")
        else:
            self._status_lbl.setText("")
            self._status_lbl.setStyleSheet(f"color: {PALETTE['subtext']}; font-size: 8pt; background: transparent;")

    def _update_all_proxy_cards_visibility(self):
        """Update button visibility on all proxy cards based on auto-check state."""
        count = self._result_layout.count()
        for i in range(count - 1):  # -1 to skip the stretch
            item = self._result_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget.objectName() == "proxyCard" and hasattr(widget, 'update_button_visibility'):
                    widget.update_button_visibility(self._auto_check_enabled)

    def _show_timer_popover(self):
        """Show the timer interval popover below the timer button, right-aligned."""
        self._timer_popover.set_value(self._auto_check_interval)
        btn = self._timer_interval_btn
        # Right-align popover to the button's right edge
        pos = btn.mapToGlobal(QPoint(btn.width() - self._timer_popover.width(), btn.height() + 4))
        self._timer_popover.move(pos)
        self._timer_popover.show()

    def _on_interval_changed(self, val: int):
        """Called when the user moves the timer popover slider."""
        self._auto_check_interval = val
        if self._auto_check_enabled:
            # Restart both timers with the new interval
            self._auto_check_timer.stop()
            self._countdown_timer.stop()
            self._auto_check_timer.start(self._auto_check_interval * 1000)
            self._countdown_remaining = self._auto_check_interval
            self._countdown_timer.start(1000)
            self._update_countdown_display()

    def _update_auto_check_btn_state(self, count: int = None):
        """Enable/disable the Auto Check button based on whether there are proxy cards and Cliproxy is running."""
        if count is None:
            count = self._result_layout.count() - 1  # exclude stretch
        has_proxies = count > 0
        cliproxy_running = self._is_cliproxy_running()
        enabled = has_proxies and cliproxy_running
        self._auto_check_btn.setEnabled(enabled)
        self._timer_interval_btn.setEnabled(enabled)
        self._bulk_check_btn.setEnabled(enabled)
        self._bulk_refresh_btn.setEnabled(enabled)
        if not enabled and self._auto_check_enabled:
            # Turn off auto check if list becomes empty or Cliproxy stops running
            self._auto_check_enabled = False
            self._auto_check_timer.stop()
            self._countdown_timer.stop()
            self._auto_check_status.setText("OFF")
            self._auto_check_status.setStyleSheet(f"color: {PALETTE['subtext']}; background: transparent;")
            self._auto_check_btn.setProperty("checked", False)
            self._auto_check_btn.style().unpolish(self._auto_check_btn)
            self._auto_check_btn.style().polish(self._auto_check_btn)
            self._update_all_proxy_cards_visibility()

    def _auto_check_all_proxies(self):
        """Automatically check all proxy cards and refresh dead ones."""
        # Stop countdown while we are processing (restart after all done)
        self._countdown_timer.stop()

        # Verify local IP is reachable before starting the cycle
        current_ip = current_ipv4()
        if not current_ip:
            self._status_lbl.setText("⚠ No network – auto check skipped")
            self._status_lbl.setStyleSheet(f"color: {PALETTE['warning']}; font-size: 8pt; background: transparent;")
            self._restart_auto_check_timer()
            return

        self._status_lbl.setText("⚡ Checking…")
        self._status_lbl.setStyleSheet(f"color: {PALETTE['accent2']}; font-size: 8pt; background: transparent;")

        # Iterate through all widgets in the result layout
        count = self._result_layout.count()
        if count <= 1:  # Only stretch item or empty
            self._restart_auto_check_timer()
            return

        cards = []
        for i in range(count - 1):  # -1 to skip the stretch
            item = self._result_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget.objectName() == "proxyCard" and hasattr(widget, '_auto_check_triggered') and hasattr(widget, '_do_check'):
                    cards.append(widget)

        if not cards:
            self._restart_auto_check_timer()
            return

        self._auto_check_pending = len(cards)
        for widget in cards:
            # Skip cards already running a check or refresh
            if ((widget._check_thread is not None and widget._check_thread.isRunning()) or
                    (widget._refresh_thread is not None and widget._refresh_thread.isRunning())):
                # Count it as done so pending counter stays consistent
                self._auto_check_pending = max(0, self._auto_check_pending - 1)
                continue
            widget._auto_check_triggered = True
            widget._do_check()

        # If all cards were busy, pending will be 0 — restart timer immediately
        if self._auto_check_pending == 0:
            self._restart_auto_check_timer()

    def _on_auto_check_card_done(self, card):
        """Called when a single card finishes its auto-check cycle (alive or refresh done)."""
        self._auto_check_pending = max(0, self._auto_check_pending - 1)
        if self._auto_check_pending == 0:
            # All cards finished → restart the timer for the next cycle
            self._restart_auto_check_timer()

    def _restart_auto_check_timer(self):
        """Restart countdown and schedule the next auto-check cycle."""
        if not self._auto_check_enabled:
            return
        self._countdown_remaining = self._auto_check_interval
        self._countdown_timer.start(1000)
        self._auto_check_timer.start(self._auto_check_interval * 1000)
        self._update_countdown_display()

    def _bulk_check(self):
        """Check all proxy cards concurrently (mirrors proxy.py concurrency model).
        Each card spins up its own QThread; _check_semaphore inside
        ProxyCheckWorker caps simultaneous TCP connections at PROXY_CHECK_CONCURRENCY.
        """
        count = self._result_layout.count()
        if count <= 1:
            return
        checked = 0
        for i in range(count - 1):
            item = self._result_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget.objectName() == "proxyCard" and hasattr(widget, '_do_check'):
                    widget._auto_check_triggered = False
                    widget._do_check()
                    checked += 1
        if checked:
            self._set_status(f"⚡ Checking {checked} proxies… (concurrency={PROXY_CHECK_CONCURRENCY})", PALETTE['accent2'])

    def _bulk_refresh(self):
        """Refresh all proxy cards at once."""
        count = self._result_layout.count()
        if count <= 1:
            return
        refreshed = 0
        for i in range(count - 1):
            item = self._result_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget.objectName() == "proxyCard" and hasattr(widget, '_do_refresh'):
                    widget._do_refresh()
                    refreshed += 1
        if refreshed:
            self._set_status(f"↻ Refreshing {refreshed} proxies…", PALETTE['accent2'])

    def _clear_cache(self):
        """Wipe all saved proxies and clear the result view."""
        reply = QMessageBox.question(
            self, "Clear Cache",
            "Delete all saved proxies?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            data = _load_app_data()
            data["proxies"] = []
            _save_app_data(data)
        except Exception as e:
            print(f"Error clearing cache: {e}")
        self._clear_rows()
        self._proxy_search.clear()
        self._res_count_lbl.setText("0 proxies")
        self._set_status("🗑  Cache cleared", PALETTE['subtext'])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    icon_path = os.path.join(_BUNDLE_DIR, "icon.png")
    app.setWindowIcon(QIcon(icon_path))
    app.setFont(QFont("Segoe UI", 10))
    win = ProxyApp()
    win.show()
    sys.exit(app.exec())
