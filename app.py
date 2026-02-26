import sys
import json
import requests

from PySide6.QtCore    import Qt, Signal, QObject, QStringListModel, QThread
from PySide6.QtGui     import QColor, QFont, QTextCursor, QPainter, QTextDocument, QAbstractTextDocumentLayout
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QComboBox, QPushButton,
    QTextEdit, QFrame, QSizePolicy, QCompleter, QMessageBox,
    QScrollArea, QStyledItemDelegate, QStyleOptionViewItem, QStyle
)

# ─── Data ──────────────────────────────────────────────────────────────────────
COUNTRY_DATA = {
    "US": {
        "states":   ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL",
                     "IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT",
                     "NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI",
                     "SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"],
        "networks": ["ATT","Verizon","T-Mobile","Sprint","Comcast","Charter","CenturyLink","Cox"],
    },
    "AU": {
        "states":   ["NSW","VIC","QLD","SA","WA","TAS","NT","ACT"],
        "networks": ["Vodafone","Telstra","Optus","TPG","Aussie Broadband"],
    },
    "CA": {
        "states":   ["AB","BC","MB","NB","NL","NS","NT","NU","ON","PE","QC","SK","YT"],
        "networks": ["Rogers","Bell","Telus","Freedom Mobile","Shaw","Videotron"],
    },
    "GB": {
        "states":   ["England","Scotland","Wales","Northern Ireland"],
        "networks": ["BT","EE","O2","Vodafone","Three","Sky","Virgin Media"],
    },
    "DE": {
        "states":   ["BY","BE","BB","HB","HH","HE","MV","NI","NW","RP","SL","SN","ST","SH","TH"],
        "networks": ["Deutsche Telekom","Vodafone","O2","1&1","Freenet"],
    },
    "FR": {
        "states":   ["IDF","ARA","BFC","BRE","CVL","GES","HDF","NOR","NAQ","OCC","PDL","PAC"],
        "networks": ["Orange","SFR","Bouygues Telecom","Free Mobile"],
    },
    "JP": {
        "states":   ["Tokyo","Osaka","Kyoto","Aichi","Fukuoka","Hokkaido","Kanagawa","Okinawa"],
        "networks": ["NTT","SoftBank","KDDI","Rakuten Mobile"],
    },
    "SG": {
        "states":   ["Central","North","South","East","West"],
        "networks": ["Singtel","StarHub","M1","TPG Telecom"],
    },
    "IN": {
        "states":   ["MH","DL","KA","TN","UP","WB","GJ","RJ","MP","AP"],
        "networks": ["Jio","Airtel","Vi","BSNL","MTNL"],
    },
    "BR": {
        "states":   ["SP","RJ","MG","BA","PR","RS","PE","CE","PA","MA"],
        "networks": ["Claro","Vivo","TIM","Oi","Nextel"],
    },
}

ALL_NETWORKS = sorted({n for d in COUNTRY_DATA.values() for n in d["networks"]})
API_BASE     = "http://192.168.1.33:1998/api"

# ─── Palette ───────────────────────────────────────────────────────────────────
C = {
    "bg":           "#0f1117",
    "panel":        "#1a1d2e",
    "card":         "#1e2235",
    "accent":       "#6c63ff",
    "accent2":      "#a78bfa",
    "success":      "#22c55e",
    "error":        "#f87171",
    "text":         "#e2e8f0",
    "subtext":      "#64748b",
    "border":       "#2d3150",
    "border_focus": "#6c63ff",
    "entry_bg":     "#151728",
    "btn_hv":       "#7c73ff",
    "label":        "#94a3b8",
}

# ─── Global stylesheet ─────────────────────────────────────────────────────────
STYLESHEET = f"""
QMainWindow, QWidget#central {{
    background: {C['bg']};
}}
QWidget#card {{
    background: {C['card']};
    border: 1px solid {C['border']};
    border-radius: 12px;
}}
QLabel#section {{
    color: {C['accent2']};
    font-weight: 700;
    font-size: 9pt;
    background: transparent;
}}
QLabel#field {{
    color: {C['subtext']};
    font-size: 7pt;
    font-weight: 700;
    letter-spacing: 0.5px;
    background: transparent;
}}
QLabel {{
    color: {C['text']};
    background: transparent;
}}
QLineEdit {{
    background: {C['entry_bg']};
    color: {C['text']};
    border: 1.5px solid {C['border']};
    border-radius: 8px;
    padding: 7px 11px;
    font-size: 10pt;
    selection-background-color: {C['accent']};
}}
QLineEdit:focus {{
    border-color: {C['border_focus']};
}}
QComboBox {{
    background: {C['entry_bg']};
    color: {C['text']};
    border: 1.5px solid {C['border']};
    border-radius: 8px;
    padding: 7px 11px;
    font-size: 10pt;
    selection-background-color: {C['accent']};
}}
QComboBox:focus {{
    border-color: {C['border_focus']};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 28px;
    border: none;
    background: transparent;
}}
QComboBox::down-arrow {{
    image: none;
    width: 0px;
    height: 0px;
    border: none;
    background: transparent;
}}
QComboBox QAbstractItemView {{
    background: {C['panel']};
    color: {C['text']};
    border: 1.5px solid {C['border_focus']};
    border-radius: 8px;
    selection-background-color: {C['accent']};
    selection-color: #fff;
    padding: 4px;
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    min-height: 28px;
    padding: 2px 10px;
    border-radius: 4px;
}}
QComboBox QAbstractItemView::item:hover {{
    background: {C['accent']};
    color: #fff;
}}
QPushButton#fetchBtn {{
    background: {C['accent']};
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 10px 26px;
    font-size: 10pt;
    font-weight: 700;
}}
QPushButton#fetchBtn:hover   {{ background: {C['btn_hv']}; }}
QPushButton#fetchBtn:pressed  {{ background: #5a52e0; }}
QPushButton#fetchBtn:disabled {{ background: {C['border']}; color: {C['subtext']}; }}
QPushButton#clearBtn {{
    background: {C['card']};
    color: {C['label']};
    border: 1.5px solid {C['border']};
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 10pt;
    font-weight: 700;
}}
QPushButton#clearBtn:hover  {{ background: {C['border']}; color: {C['text']}; }}
QPushButton#clearBtn:pressed {{ background: #252840; }}
/* Proxy row */
QWidget#proxyRow {{
    background: {C['card']};
    border: 1px solid {C['border']};
    border-radius: 8px;
}}
QWidget#proxyRow:hover {{
    border-color: {C['border_focus']};
}}
QLabel#proxyText {{
    color: {C['text']};
    font-family: "Consolas", monospace;
    font-size: 10pt;
    background: transparent;
    padding: 0px 4px;
}}
/* Check button */
QPushButton#checkBtn {{
    background: transparent;
    color: {C['accent2']};
    border: 1.5px solid {C['border']};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 8pt;
    font-weight: 700;
    min-width: 60px;
}}
QPushButton#checkBtn:hover   {{ background: {C['accent']}; color: #fff; border-color: {C['accent']}; }}
QPushButton#checkBtn:pressed  {{ background: #5a52e0; color: #fff; }}
QPushButton#checkBtn:disabled {{ color: {C['subtext']}; border-color: {C['border']}; }}
/* Copy button */
QPushButton#copyBtn {{
    background: transparent;
    color: {C['subtext']};
    border: 1.5px solid {C['border']};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 8pt;
    font-weight: 700;
    min-width: 54px;
}}
QPushButton#copyBtn:hover   {{ background: {C['panel']}; color: {C['text']}; }}
QPushButton#copyBtn:pressed  {{ background: {C['border']}; }}
/* Status labels */
QLabel#statusAlive {{
    color: {C['success']};
    font-size: 8pt;
    font-weight: 700;
    background: transparent;
    padding: 0px 4px;
}}
QLabel#statusDead {{
    color: {C['error']};
    font-size: 8pt;
    font-weight: 700;
    background: transparent;
    padding: 0px 4px;
}}
QLabel#statusChecking {{
    color: {C['subtext']};
    font-size: 8pt;
    background: transparent;
    padding: 0px 4px;
}}
/* Result scroll area */
QScrollArea#resultScroll {{
    background: {C['entry_bg']};
    border: 1px solid {C['border']};
    border-radius: 10px;
}}
QScrollArea#resultScroll > QWidget > QWidget {{
    background: {C['entry_bg']};
}}
QTextEdit#result {{
    background: {C['entry_bg']};
    color: {C['text']};
    border: 1px solid {C['border']};
    border-radius: 10px;
    font-family: "Consolas", monospace;
    font-size: 10pt;
    padding: 10px 14px;
    selection-background-color: {C['accent']};
}}
QScrollBar:vertical {{
    background: {C['entry_bg']};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C['border']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {C['accent']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QFrame#divider {{
    background: {C['border']};
    border: none;
}}
QLabel#badge {{
    background: {C['accent']};
    color: #fff;
    border-radius: 4px;
    padding: 1px 7px;
    font-size: 8pt;
    font-weight: 700;
}}
"""


# ─── Worker thread ──────────────────────────────────────────────────────────────
class FetchWorker(QObject):
    finished = Signal(object)
    error    = Signal(str)

    def __init__(self, params: dict):
        super().__init__()
        self._params = params

    def run(self):
        try:
            resp = requests.get(API_BASE, params=self._params, timeout=15)
            self.finished.emit(resp)
        except requests.exceptions.ConnectionError:
            self.error.emit("Connection refused – check API server.")
        except requests.exceptions.Timeout:
            self.error.emit("Request timed out.")
        except Exception as exc:
            self.error.emit(str(exc))


# ─── Proxy check worker ────────────────────────────────────────────────────────
class ProxyCheckWorker(QObject):
    result = Signal(bool)   # True = alive, False = dead

    TEST_URL = "http://httpbin.org/ip"

    def __init__(self, proxy_str: str):
        super().__init__()
        self._proxy = proxy_str   # "ip:port"

    def run(self):
        try:
            proxies = {
                "http":  f"http://{self._proxy}",
                "https": f"http://{self._proxy}",
            }
            resp = requests.get(self.TEST_URL, proxies=proxies, timeout=8)
            self.result.emit(resp.status_code == 200)
        except Exception:
            self.result.emit(False)


# ─── Autocomplete ComboBox ──────────────────────────────────────────────────────
class HighlightDelegate(QStyledItemDelegate):
    """Custom delegate to highlight matching text in dropdown items."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlight_color = QColor(C['accent'])
        self.match_text = ""

    def set_match_text(self, text: str):
        self.match_text = text.lower()

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        # Get the text
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not text:
            return super().paint(painter, option, index)

        # Check if we need to highlight
        if self.match_text and self.match_text in text.lower():
            # Draw highlighted background for the entire item
            painter.fillRect(option.rect, self.highlight_color)

            # Draw border radius
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.highlight_color)
            painter.drawRoundedRect(option.rect.adjusted(2, 2, -2, -2), 4, 4)

            # Draw text in white
            painter.setPen(QColor("#ffffff"))
            painter.drawText(option.rect.adjusted(10, 0, -10, 0),
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                           text)
        else:
            # No highlighting needed, use default painting
            super().paint(painter, option, index)


class AutoComboBox(QComboBox):
    """Editable QComboBox with live contains-filtering via QCompleter."""

    POPUP_STYLE = f"""
        QAbstractItemView {{
            background: {C['panel']};
            color: {C['text']};
            border: 1.5px solid {C['border_focus']};
            border-radius: 8px;
            selection-background-color: {C['accent']};
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
            background: {C['accent']};
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
        self._completer.popup().setStyleSheet(self.POPUP_STYLE)

        # Connect text changes to update highlighting
        self.editTextChanged.connect(self._update_highlight)

        # Custom arrow label
        self._arrow = QLabel("▼", self)
        self._arrow.setStyleSheet(f"""
            color: {C['text']};
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


# ─── Main window ───────────────────────────────────────────────────────────────
class ProxyApp(QMainWindow):
    _status_sig = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proxy Fetcher")
        self.setFixedSize(860, 720)
        self._status_sig.connect(self._apply_status)
        self._build_ui()
        self._center()
        self._set_defaults()

    def _center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )

    def _set_defaults(self):
        # Set default values: Area Code = US, State = FL, Network = ATT
        self._area_cb.setCurrentText("US")
        self._on_country_change("US")  # Manually trigger to populate state dropdown
        self._state_cb.setCurrentText("FL")
        self._network_cb.setCurrentText("ATT")

    # ── Build UI ────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget()
        root.setObjectName("central")
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(28, 22, 28, 22)
        main.setSpacing(0)

        # Header
        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        icon_lbl = QLabel("🌐")
        icon_lbl.setFont(QFont("Segoe UI Emoji", 20))
        icon_lbl.setStyleSheet(f"color: {C['accent']}; background: transparent;")
        title_lbl = QLabel("Proxy Fetcher")
        title_lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        badge = QLabel("v1.0")
        badge.setObjectName("badge")
        badge.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        hdr.addWidget(icon_lbl)
        hdr.addWidget(title_lbl)
        hdr.addWidget(badge)
        hdr.addStretch()
        main.addLayout(hdr)
        main.addSpacing(4)

        sub = QLabel("Search & retrieve proxies by country, state and network carrier")
        sub.setStyleSheet(f"color: {C['subtext']}; font-size: 9pt; background: transparent;")
        main.addWidget(sub)
        main.addSpacing(14)

        div0 = QFrame(); div0.setObjectName("divider"); div0.setFixedHeight(1)
        main.addWidget(div0)
        main.addSpacing(14)

        # ── Form card (full width) ──────────────────────────────────────────────
        card = QWidget(); card.setObjectName("card")
        card_v = QVBoxLayout(card)
        card_v.setContentsMargins(20, 18, 20, 18)
        card_v.setSpacing(0)

        # Grid 1 — Location (3 cols)
        g1 = QGridLayout()
        g1.setHorizontalSpacing(12); g1.setVerticalSpacing(6)
        for i in range(3): g1.setColumnStretch(i, 1)

        self._sec_lbl(g1, "🗺️  Location", 0, 0, 3)
        self._fld_lbl(g1, "AREA CODE",        0, 1)
        self._fld_lbl(g1, "STATE / PROVINCE", 1, 1)
        self._fld_lbl(g1, "NETWORK / ISP",    2, 1)

        self._area_cb = AutoComboBox()
        self._area_cb.set_items(list(COUNTRY_DATA.keys()))
        self._area_cb.setPlaceholderText("e.g. US")
        self._area_cb.currentTextChanged.connect(self._on_country_change)
        g1.addWidget(self._area_cb, 2, 0)

        self._state_cb = AutoComboBox()
        self._state_cb.setPlaceholderText("Any")
        g1.addWidget(self._state_cb, 2, 1)

        self._network_cb = AutoComboBox()
        self._network_cb.set_items(ALL_NETWORKS)
        self._network_cb.setPlaceholderText("Any")
        g1.addWidget(self._network_cb, 2, 2)

        card_v.addLayout(g1)
        card_v.addSpacing(14)

        div_inner = QFrame(); div_inner.setObjectName("divider"); div_inner.setFixedHeight(1)
        card_v.addWidget(div_inner)
        card_v.addSpacing(14)

        # Grid 2 — Query Options (3 cols)
        g2 = QGridLayout()
        g2.setHorizontalSpacing(12); g2.setVerticalSpacing(6)
        for i in range(3): g2.setColumnStretch(i, 1)

        sec2 = QLabel("⚙️  Query Options"); sec2.setObjectName("section")
        g2.addWidget(sec2, 0, 0, 1, 3)
        self._fld_lbl(g2, "PORT",              0, 1)
        self._fld_lbl(g2, "NUMBER OF RESULTS", 1, 1)
        self._fld_lbl(g2, "START OFFSET",      2, 1)

        self._port_edit = QLineEdit()
        self._port_edit.setPlaceholderText("e.g. 2000")
        g2.addWidget(self._port_edit, 2, 0)

        self._number_edit = QLineEdit("1")
        g2.addWidget(self._number_edit, 2, 1)

        self._start_edit = QLineEdit("40000")
        g2.addWidget(self._start_edit, 2, 2)

        card_v.addLayout(g2)
        main.addWidget(card)
        main.addSpacing(12)

        # ── Action bar (full width, 2 buttons) ───────────────────────────────
        act = QHBoxLayout(); act.setSpacing(10)

        self._fetch_btn = QPushButton("  🔍  Fetch Proxy")
        self._fetch_btn.setObjectName("fetchBtn")
        self._fetch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fetch_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._fetch_btn.clicked.connect(self._fetch)

        self._clear_btn = QPushButton("  ✕  Clear")
        self._clear_btn.setObjectName("clearBtn")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._clear_btn.clicked.connect(self._clear_result)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(
            f"color: {C['subtext']}; font-size: 9pt; background: transparent;")

        act.addWidget(self._fetch_btn, 1)
        act.addWidget(self._clear_btn, 1)
        main.addLayout(act)
        main.addSpacing(6)

        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main.addWidget(self._status_lbl)
        main.addSpacing(10)

        # ── Result section ────────────────────────────────────────────────────
        res_hdr = QLabel("RESULT")
        res_hdr.setStyleSheet(
            f"color: {C['subtext']}; font-size: 8pt; font-weight: 700; background: transparent;")
        main.addWidget(res_hdr)
        main.addSpacing(4)

        # Scroll area containing a VBox of proxy rows
        self._scroll = QScrollArea()
        self._scroll.setObjectName("resultScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._result_container = QWidget()
        self._result_container.setStyleSheet(f"background: {C['entry_bg']};")
        self._result_layout = QVBoxLayout(self._result_container)
        self._result_layout.setContentsMargins(10, 10, 10, 10)
        self._result_layout.setSpacing(6)
        self._result_layout.addStretch()

        self._scroll.setWidget(self._result_container)
        main.addWidget(self._scroll, 1)

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

    # ── Fetch ────────────────────────────────────────────────────────────────
    def _fetch(self):
        country = self._area_cb.current_value().upper()
        if not country:
            QMessageBox.warning(self, "Missing field",
                                "Please enter an Area Code (country).")
            return

        params = {
            "country": country,
            "state":   self._state_cb.current_value(),
            "city":    "",
            "postal":  "",
            "isp":     self._network_cb.current_value(),
            "start":   self._start_edit.text().strip() or "40000",
            "num":     self._number_edit.text().strip() or "1",
            "ip":      "",
        }
        port = self._port_edit.text().strip()
        if port:
            params["port"] = port

        self._set_status("⏳  Fetching…", C['subtext'])
        self._fetch_btn.setEnabled(False)
        self._result.clear()

        self._thread = QThread()
        self._worker = FetchWorker(params)
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
        if code == 200:
            self._set_status(f"✓  {code} OK", C['success'])
            try:
                self._render_json(resp.json(), resp.url)
            except Exception:
                self._add_info_row(resp.text)
        else:
            self._set_status(f"✗  HTTP {code}", C['error'])
            self._add_info_row(f"HTTP {code}\n{resp.text}", is_error=True)

    def _show_error(self, msg: str):
        self._fetch_btn.setEnabled(True)
        self._set_status("✗  Error", C['error'])
        self._add_info_row(f"Error: {msg}", is_error=True)

    # ── Result rendering ─────────────────────────────────────────────────────
    def _clear_rows(self):
        """Remove all widgets from the result layout (keep trailing stretch)."""
        while self._result_layout.count() > 1:
            item = self._result_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _render_json(self, data, url: str):
        self._clear_rows()
        # URL info row
        self._add_info_row(f"URL: {url}")

        if isinstance(data, list):
            self._add_info_row(f"Found {len(data)} result(s)", color=C['success'])
            for item in data:
                if isinstance(item, dict):
                    self._add_proxy_row(item)
                else:
                    self._add_info_row(str(item))
        elif isinstance(data, dict):
            self._add_proxy_row(data)
        else:
            self._add_info_row(str(data))

    def _proxy_str(self, d: dict) -> str:
        """Build a display string from a proxy dict."""
        ip   = d.get("ip",   d.get("host", ""))
        port = d.get("port", "")
        if ip and port:
            return f"{ip}:{port}"
        # fallback: show all key=value pairs
        parts = [f"{k}: {v}" for k, v in d.items() if v not in ("", None)]
        return "  |  ".join(parts)

    def _add_info_row(self, text: str, color: str = None, is_error: bool = False):
        lbl = QLabel(text)
        lbl.setObjectName("proxyText")
        lbl.setWordWrap(True)
        c = color or (C['error'] if is_error else C['subtext'])
        lbl.setStyleSheet(f"color: {c}; font-size: 9pt; background: transparent; padding: 4px 8px;")
        self._result_layout.insertWidget(self._result_layout.count() - 1, lbl)

    def _add_proxy_row(self, proxy_dict: dict):
        row = QWidget()
        row.setObjectName("proxyRow")
        row.setFixedHeight(44)

        hl = QHBoxLayout(row)
        hl.setContentsMargins(12, 0, 8, 0)
        hl.setSpacing(8)

        # Proxy text
        proxy_str = self._proxy_str(proxy_dict)
        txt = QLabel(proxy_str)
        txt.setObjectName("proxyText")
        txt.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        hl.addWidget(txt, 1)

        # Status label (empty until checked)
        status_lbl = QLabel("")
        status_lbl.setObjectName("statusChecking")
        status_lbl.setFixedWidth(80)
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(status_lbl)

        # Check button
        check_btn = QPushButton("⚡ Check")
        check_btn.setObjectName("checkBtn")
        check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        check_btn.setFixedHeight(30)
        hl.addWidget(check_btn)

        # Copy button
        copy_btn = QPushButton("📋 Copy")
        copy_btn.setObjectName("copyBtn")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setFixedHeight(30)
        hl.addWidget(copy_btn)

        # Wire up
        check_btn.clicked.connect(
            lambda _, s=status_lbl, b=check_btn, p=proxy_str: self._check_proxy(p, s, b))
        copy_btn.clicked.connect(
            lambda _, p=proxy_str: QApplication.clipboard().setText(p))

        self._result_layout.insertWidget(self._result_layout.count() - 1, row)

    # ── Proxy check ──────────────────────────────────────────────────────────
    def _check_proxy(self, proxy_str: str, status_lbl: QLabel, btn: QPushButton):
        btn.setEnabled(False)
        status_lbl.setObjectName("statusChecking")
        status_lbl.setText("…checking")
        status_lbl.setStyleSheet(f"color: {C['subtext']}; font-size: 8pt; background: transparent; padding: 0 4px;")

        self._check_thread = QThread()
        self._check_worker = ProxyCheckWorker(proxy_str)
        self._check_worker.moveToThread(self._check_thread)
        self._check_thread.started.connect(self._check_worker.run)
        self._check_worker.result.connect(
            lambda alive, s=status_lbl, b=btn: self._on_check_result(alive, s, b))
        self._check_worker.result.connect(self._check_thread.quit)
        self._check_thread.start()

    def _on_check_result(self, alive: bool, status_lbl: QLabel, btn: QPushButton):
        btn.setEnabled(True)
        if alive:
            status_lbl.setText("● Alive")
            status_lbl.setStyleSheet(
                f"color: {C['success']}; font-size: 8pt; font-weight: 700; background: transparent; padding: 0 4px;")
        else:
            status_lbl.setText("✕ Dead")
            status_lbl.setStyleSheet(
                f"color: {C['error']}; font-size: 8pt; font-weight: 700; background: transparent; padding: 0 4px;")

    # ── Status (thread-safe) ─────────────────────────────────────────────────
    def _set_status(self, msg: str, color: str):
        self._status_sig.emit(msg, color)

    def _apply_status(self, msg: str, color: str):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(
            f"color: {color}; font-size: 9pt; background: transparent;")

    def _clear_result(self):
        self._clear_rows()
        self._status_lbl.setText("")


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    app.setFont(QFont("Segoe UI", 10))
    win = ProxyApp()
    win.show()
    sys.exit(app.exec())
