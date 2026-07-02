from __future__ import annotations

import csv
import json
import re

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QThread
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QGraphicsOpacityEffect,
    QPushButton,
    QStyle,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from ping import ProxyPingBatchWorker, _proxy_location
from proxy_scoring import (
    enrich_proxy_result,
    export_proxy_row,
    format_proxy_clipboard_line,
    format_proxy_detail,
    proxy_table_fields,
    score_tone,
)

from .common import (
    COMPACT_CONTROL_HEIGHT,
    build_tool_shell,
    make_hint,
    make_section,
    make_tool_button,
)


class ProxyStatsChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._stats = {
            "total": 0,
            "alive": 0,
            "dead": 0,
            "pending": 0,
            "good": 0,
            "fair": 0,
            "weak": 0,
            "bad": 0,
            "risk": 0,
        }
        self.setMinimumHeight(104)
        self.setMaximumHeight(122)
        self.setObjectName("proxyStatsChart")

    def set_stats(self, stats: dict):
        self._stats = dict(stats)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -8)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#0f1420"))
        painter.drawRoundedRect(rect, 8, 8)

        total = max(1, int(self._stats.get("total", 0) or 0))
        left_width = int(rect.width() * 0.58)
        left_rect = rect.adjusted(14, 12, -(rect.width() - left_width), -12)
        right_rect = rect.adjusted(left_width + 24, 12, -14, -12)
        self._draw_overview(painter, left_rect, total)
        self._draw_signal_quality(painter, right_rect, total)
        painter.end()

    def _draw_overview(self, painter: QPainter, rect, total: int):
        total = int(self._stats.get("total", 0) or 0)
        alive = int(self._stats.get("alive", 0) or 0)
        dead = int(self._stats.get("dead", 0) or 0)
        pending = int(self._stats.get("pending", 0) or 0)
        painter.setPen(QColor("#e7edf7"))
        painter.drawText(int(rect.left()), int(rect.top() + 12), f"Overview: {total} total")
        segments = (
            ("Alive", alive, QColor("#34d399")),
            ("Dead", dead, QColor("#fb7185")),
            ("Pending", pending, QColor("#7d8aa1")),
        )
        bar = QRectF(rect.left(), rect.top() + 24, rect.width(), 14)
        self._draw_ratio_bar(painter, bar, segments, max(1, total))
        self._draw_segment_labels(painter, int(rect.left()), int(rect.top() + 55), segments)

    def _draw_signal_quality(self, painter: QPainter, rect, total: int):
        segments = (
            ("Good", int(self._stats.get("good", 0) or 0), QColor("#34d399")),
            ("Fair", int(self._stats.get("fair", 0) or 0), QColor("#fbbf24")),
            ("Weak", int(self._stats.get("weak", 0) or 0), QColor("#fb923c")),
            ("Bad", int(self._stats.get("bad", 0) or 0), QColor("#fb7185")),
        )
        painter.setPen(QColor("#e7edf7"))
        painter.drawText(int(rect.left()), int(rect.top() + 12), "Signal quality")
        bar = QRectF(rect.left(), rect.top() + 24, rect.width(), 14)
        signal_total = max(1, sum(value for _label, value, _color in segments))
        self._draw_ratio_bar(painter, bar, segments, signal_total)
        self._draw_segment_labels(painter, int(rect.left()), int(rect.top() + 55), segments)

    def _draw_ratio_bar(self, painter: QPainter, bar: QRectF, segments, total: int):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#161c2a"))
        painter.drawRoundedRect(bar, 7, 7)

        x = bar.left()
        visible_segments = [(label, value, color) for label, value, color in segments if value > 0]
        for index, (_label, value, color) in enumerate(visible_segments):
            width = bar.width() * value / total
            if index == len(visible_segments) - 1:
                width = bar.right() - x
            if width <= 0:
                continue
            painter.setBrush(color)
            painter.drawRect(QRectF(x, bar.top(), width, bar.height()))
            x += width

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QColor("#161c2a"))
        painter.drawRoundedRect(bar, 7, 7)

    def _draw_segment_labels(self, painter: QPainter, x: int, y: int, segments):
        cursor_x = x
        for label, value, color in segments:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(cursor_x, y - 9, 10, 10), 3, 3)
            painter.setPen(QColor("#a7b0c3"))
            text = f"{label} {value}"
            painter.drawText(cursor_x + 15, y, text)
            cursor_x += 82


class ProxyTab(QWidget):
    RESULT_COLUMNS = (
        ("#", "index", 46, Qt.AlignmentFlag.AlignCenter),
        ("Proxy", "proxy", 260, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
        ("Type", "type", 82, Qt.AlignmentFlag.AlignCenter),
        ("IP public", "ip_public", 128, Qt.AlignmentFlag.AlignCenter),
        ("Location", "location", 170, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
        ("MS", "ms", 70, Qt.AlignmentFlag.AlignCenter),
        ("TCP", "tcp", 64, Qt.AlignmentFlag.AlignCenter),
        ("AVG", "avg", 70, Qt.AlignmentFlag.AlignCenter),
        ("Quality", "quality", 86, Qt.AlignmentFlag.AlignCenter),
        ("Risk", "risk", 180, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
    )

    TONE_COLORS = {
        "good": "#34d399",
        "warn": "#fbbf24",
        "bad": "#fb7185",
        "muted": "#7d8aa1",
    }

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
        self._proxy_entry_lines: dict[int, int] = {}
        self._proxy_results: dict[int, dict] = {}
        self._proxy_visible_indexes: list[int] = []
        self._is_running = False
        self._refreshing_table = False

        self._build_ui()
        self._show_input_page()
        self._update_input_count()
        self._update_proxy_stats()

    def _build_ui(self):
        outer, layout = build_tool_shell(
            self,
            "Proxy",
            self._show_close_button,
            self._close_handler,
            self._outer_margins,
        )
        layout.addWidget(make_section("Proxy quality check"))
        layout.addWidget(
            make_hint(
                "Paste one proxy per line. Full score mode adds lightweight checks for "
                "Google, Facebook, Instagram, and TikTok; scores are internal estimates."
            )
        )

        self._stack = QStackedWidget()
        self._input_page = self._build_input_page()
        self._result_page = self._build_result_page()
        self._stack.addWidget(self._input_page)
        self._stack.addWidget(self._result_page)
        layout.addWidget(self._stack, 1)

        self._proxy_summary = QLabel("Ready")
        self._proxy_summary.setObjectName("toolHint")
        layout.addWidget(self._proxy_summary)

        self._proxy_stats_lbl = QLabel("Stats: total 0 | done 0 | alive 0 | dead 0")
        self._proxy_stats_lbl.setObjectName("toolHint")
        self._proxy_stats_lbl.setToolTip("Summary of the current proxy result set.")
        layout.addWidget(self._proxy_stats_lbl)

    def _build_input_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("proxyInputPage")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(8)

        fmt_hint = QLabel(
            "<code>host:port</code> | "
            "<code>host:port:user:pass</code> | "
            "<code>user:pass@host:port</code> | "
            "<code>socks5h://user:pass@host:port</code> | "
            "<code>http://user:pass@host:port</code>"
        )
        fmt_hint.setWordWrap(True)
        fmt_hint.setObjectName("toolFormatHint")
        page_layout.addWidget(fmt_hint)

        self._proxy_input = QPlainTextEdit()
        self._proxy_input.setObjectName("toolTextArea")
        self._proxy_input.setPlaceholderText(
            "host:port\nhost:port:user:pass\nsocks5h://user:pass@host:port"
        )
        self._proxy_input.setToolTip("Paste or type one proxy per line. Empty lines are ignored.")
        self._proxy_input.setMinimumHeight(460)
        self._proxy_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._proxy_input.textChanged.connect(self._update_input_count)
        page_layout.addWidget(self._proxy_input, 1)

        self._input_count_lbl = QLabel("0 proxies ready")
        self._input_count_lbl.setObjectName("toolHint")
        page_layout.addWidget(self._input_count_lbl)
        page_layout.addLayout(self._build_input_action_row())
        return page

    def _build_input_action_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        self._proto_combo = QComboBox()
        self._add_checked_combo_item(self._proto_combo, "HTTP", "http")
        self._add_checked_combo_item(self._proto_combo, "HTTPS", "https")
        self._add_checked_combo_item(self._proto_combo, "SOCKS5", "socks5")
        self._add_checked_combo_item(self._proto_combo, "SOCKS4", "socks4")
        self._proto_combo.setCurrentIndex(2)
        self._proto_combo.currentIndexChanged.connect(
            lambda _idx: self._refresh_checked_combo_labels(self._proto_combo)
        )
        self._proto_combo.setFixedHeight(COMPACT_CONTROL_HEIGHT)
        self._proto_combo.setFixedWidth(132)
        self._proto_combo.setToolTip("Default protocol for lines without a scheme.")
        self._refresh_checked_combo_labels(self._proto_combo)
        row.addWidget(self._proto_combo)

        self._mode_combo = QComboBox()
        self._add_checked_combo_item(self._mode_combo, "Fast ping", False)
        self._add_checked_combo_item(self._mode_combo, "Full score", True)
        self._mode_combo.currentIndexChanged.connect(
            lambda _idx: self._refresh_checked_combo_labels(self._mode_combo)
        )
        self._mode_combo.setFixedHeight(COMPACT_CONTROL_HEIGHT)
        self._mode_combo.setMinimumWidth(122)
        self._mode_combo.setToolTip("Full score adds lightweight platform compatibility probes.")
        self._refresh_checked_combo_labels(self._mode_combo)
        row.addWidget(self._mode_combo)

        self._workers_combo = QComboBox()
        for workers in (8, 16, 32, 64):
            self._add_checked_combo_item(self._workers_combo, f"{workers} threads", workers)
        self._workers_combo.setCurrentIndex(1)
        self._workers_combo.currentIndexChanged.connect(
            lambda _idx: self._refresh_checked_combo_labels(self._workers_combo)
        )
        self._workers_combo.setFixedHeight(COMPACT_CONTROL_HEIGHT)
        self._workers_combo.setMinimumWidth(118)
        self._workers_combo.setToolTip("Parallel proxy checks. Lower this if the machine or network is busy.")
        self._refresh_checked_combo_labels(self._workers_combo)
        row.addWidget(self._workers_combo)

        row.addStretch()

        self._proxy_paste_btn = make_tool_button(
            "Paste",
            self._paste_proxy_clipboard,
            tooltip="Paste proxy lines from the clipboard.",
        )
        self._proxy_import_btn = make_tool_button(
            "Import .txt",
            self._import_proxy_file,
            tooltip="Import proxies from a .txt file.",
        )
        self._proxy_clean_btn = make_tool_button(
            "Clean",
            self._clean_proxy_input,
            tooltip="Trim lines, split comma/semicolon lists, and remove duplicates.",
        )
        self._proxy_clear_btn = make_tool_button(
            "Clear",
            self._clear_proxy_results,
            tooltip="Clear proxy input, results, and statistics.",
        )
        self._proxy_btn = make_tool_button(
            "Check all",
            self._run_proxy_ping,
            accent=True,
            tooltip="Check all proxy lines and open the result table.",
        )
        self._view_results_btn = make_tool_button(
            "View results",
            self._show_result_page,
            tooltip="Switch back to the current result table.",
        )
        self._view_results_btn.hide()
        self._set_button_icon(self._proxy_paste_btn, "SP_FileDialogDetailedView")
        self._set_button_icon(self._proxy_import_btn, "SP_DialogOpenButton")
        self._set_button_icon(self._proxy_clean_btn, "SP_BrowserReload")
        self._set_button_icon(self._proxy_clear_btn, "SP_DialogDiscardButton")
        self._set_button_icon(self._proxy_btn, "SP_DialogApplyButton")
        self._set_button_icon(self._view_results_btn, "SP_ArrowForward")
        row.addWidget(self._proxy_paste_btn)
        row.addWidget(self._proxy_import_btn)
        row.addWidget(self._proxy_clean_btn)
        row.addWidget(self._proxy_clear_btn)
        row.addWidget(self._view_results_btn)
        row.addWidget(self._proxy_btn)
        return row

    def _build_result_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("proxyResultPage")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._proxy_search = QLineEdit()
        self._proxy_search.setPlaceholderText("Search results")
        self._proxy_search.setFixedHeight(COMPACT_CONTROL_HEIGHT)
        self._proxy_search.setMinimumWidth(180)
        self._proxy_search.textChanged.connect(lambda _text: self._refresh_proxy_results_view())
        toolbar.addWidget(self._proxy_search)

        self._proxy_filter_combo = QComboBox()
        for label, mode in (
            ("All", "all"),
            ("Alive", "alive"),
            ("Dead", "dead"),
            ("Good 80+", "good"),
            ("Needs review", "review"),
            ("Has risk", "risk"),
        ):
            self._add_checked_combo_item(self._proxy_filter_combo, label, mode)
        self._proxy_filter_combo.setFixedHeight(COMPACT_CONTROL_HEIGHT)
        self._proxy_filter_combo.setMinimumWidth(124)
        self._proxy_filter_combo.currentIndexChanged.connect(self._on_filter_combo_changed)
        self._refresh_checked_combo_labels(self._proxy_filter_combo)
        toolbar.addWidget(self._proxy_filter_combo)

        self._proxy_sort_combo = QComboBox()
        for label, mode in (
            ("Input order", "input"),
            ("AVG high", "score_desc"),
            ("AVG low", "score_asc"),
            ("Speed fast", "speed_asc"),
            ("Speed slow", "speed_desc"),
            ("Status", "status"),
            ("Location", "location"),
            ("Type", "type"),
        ):
            self._add_checked_combo_item(self._proxy_sort_combo, label, mode)
        self._proxy_sort_combo.setFixedHeight(COMPACT_CONTROL_HEIGHT)
        self._proxy_sort_combo.setMinimumWidth(128)
        self._proxy_sort_combo.currentIndexChanged.connect(self._on_sort_combo_changed)
        self._refresh_checked_combo_labels(self._proxy_sort_combo)
        toolbar.addWidget(self._proxy_sort_combo)

        toolbar.addStretch()

        self._edit_input_btn = make_tool_button(
            "Edit input",
            self._show_input_page,
            tooltip="Return to the input screen without clearing current results.",
        )
        self._copy_table_btn = make_tool_button(
            "Copy table",
            self._copy_visible_results,
            tooltip="Copy the visible table rows to the clipboard.",
        )
        self._copy_alive_btn = make_tool_button(
            "Copy alive",
            self._copy_alive_sources,
            tooltip="Copy original input lines for alive proxies.",
        )
        self._export_btn = make_tool_button(
            "Export",
            self._export_proxy_results,
            tooltip="Export visible results as CSV, JSON, or TXT.",
        )
        self._new_check_btn = make_tool_button(
            "New check",
            self._clear_proxy_results,
            danger=True,
            tooltip="Clear everything and return to input.",
        )
        self._set_button_icon(self._edit_input_btn, "SP_ArrowBack")
        self._set_button_icon(self._copy_table_btn, "SP_FileDialogContentsView")
        self._set_button_icon(self._copy_alive_btn, "SP_DialogSaveButton")
        self._set_button_icon(self._export_btn, "SP_DialogSaveButton")
        self._set_button_icon(self._new_check_btn, "SP_DialogResetButton")
        toolbar.addWidget(self._edit_input_btn)
        toolbar.addWidget(self._copy_table_btn)
        toolbar.addWidget(self._copy_alive_btn)
        toolbar.addWidget(self._export_btn)
        toolbar.addWidget(self._new_check_btn)
        page_layout.addLayout(toolbar)

        self._proxy_table = QTableWidget(0, len(self.RESULT_COLUMNS))
        self._proxy_table.setObjectName("proxyResultTable")
        self._proxy_table.setHorizontalHeaderLabels([label for label, *_rest in self.RESULT_COLUMNS])
        self._proxy_table.setAlternatingRowColors(True)
        self._proxy_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._proxy_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._proxy_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._proxy_table.setShowGrid(False)
        self._proxy_table.setMouseTracking(True)
        self._proxy_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._proxy_table.verticalHeader().setVisible(False)
        self._proxy_table.itemEntered.connect(self._on_result_item_entered)
        self._proxy_table.itemClicked.connect(self._on_result_item_clicked)
        self._proxy_table.itemSelectionChanged.connect(self._on_result_selection_changed)
        self._proxy_table.setStyleSheet(
            "QTableWidget#proxyResultTable::item:focus { outline: none; border: none; }"
        )

        header = self._proxy_table.horizontalHeader()
        header.setStretchLastSection(False)
        for index, (_label, key, width, _align) in enumerate(self.RESULT_COLUMNS):
            header.setSectionResizeMode(index, QHeaderView.ResizeMode.Interactive)
            self._proxy_table.setColumnWidth(index, width)
            if key == "proxy":
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.ResizeToContents)

        page_layout.addWidget(self._proxy_table, 9)

        self._stats_chart = ProxyStatsChart()
        page_layout.addWidget(self._stats_chart)
        return page

    def _add_checked_combo_item(self, combo: QComboBox, label: str, data):
        combo.addItem(label, data)
        combo.setItemData(combo.count() - 1, label, Qt.ItemDataRole.AccessibleDescriptionRole)

    def _refresh_checked_combo_labels(self, combo: QComboBox):
        for index in range(combo.count()):
            label = str(combo.itemData(index, Qt.ItemDataRole.AccessibleDescriptionRole) or "")
            if not label:
                label = str(combo.itemText(index)).lstrip("✓ ").strip()
                combo.setItemData(index, label, Qt.ItemDataRole.AccessibleDescriptionRole)
            prefix = "✓ " if index == combo.currentIndex() else "  "
            combo.setItemText(index, f"{prefix}{label}")

    def _set_button_icon(self, button, standard_pixmap_name: str):
        pixmap = getattr(
            QStyle.StandardPixmap,
            standard_pixmap_name,
            QStyle.StandardPixmap.SP_FileIcon,
        )
        button.setIcon(self.style().standardIcon(pixmap))
        button.setIconSize(QSize(15, 15))

    def _on_filter_combo_changed(self, _index: int):
        self._refresh_checked_combo_labels(self._proxy_filter_combo)
        self._refresh_proxy_results_view()

    def _on_sort_combo_changed(self, _index: int):
        self._refresh_checked_combo_labels(self._proxy_sort_combo)
        self._refresh_proxy_results_view()

    def _show_input_page(self):
        self._stack.setCurrentWidget(self._input_page)
        self._view_results_btn.setVisible(bool(self._proxy_results))
        self._proxy_input.setFocus()

    def _show_result_page(self):
        if not self._proxy_results:
            return
        self._stack.setCurrentWidget(self._result_page)

    def _collect_proxy_entries(self) -> list[tuple[int, str]]:
        raw_lines = self._proxy_input.toPlainText().splitlines()
        return [
            (line_no, line.strip())
            for line_no, line in enumerate(raw_lines)
            if line.strip()
        ]

    def _update_input_count(self):
        if not hasattr(self, "_input_count_lbl"):
            return
        count = len(self._collect_proxy_entries())
        self._input_count_lbl.setText(f"{count} prox{'y' if count == 1 else 'ies'} ready")

    def _paste_proxy_clipboard(self):
        text = QApplication.clipboard().text().strip()
        if not text:
            return
        self._show_input_page()
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
            self._show_input_page()
            self._proxy_input.setPlainText(text.strip())

    def _clean_proxy_input(self):
        raw = self._proxy_input.toPlainText()
        parts = [part.strip() for part in re.split(r"[\n,;]+", raw) if part.strip()]
        seen = set()
        cleaned = []
        for part in parts:
            key = part.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(part)
        self._proxy_input.setPlainText("\n".join(cleaned))
        self._proxy_summary.setText(f"Cleaned {len(cleaned)} unique proxies")

    def _clear_proxy_results(self):
        if self._is_running:
            return
        self._proxy_input.clear()
        self._proxy_table.setRowCount(0)
        self._proxy_entry_lines.clear()
        self._proxy_results.clear()
        self._proxy_visible_indexes.clear()
        self._proxy_search.clear()
        self._proxy_filter_combo.setCurrentIndex(0)
        self._proxy_sort_combo.setCurrentIndex(0)
        self._proxy_summary.setText("Ready")
        self._update_input_count()
        self._update_proxy_stats()
        self._view_results_btn.hide()
        self._show_input_page()

    def _run_proxy_ping(self):
        line_entries = self._collect_proxy_entries()
        entries = [entry for _line_no, entry in line_entries]
        if not entries:
            self._proxy_summary.setText("Please enter at least one proxy address.")
            return

        default_proto = str(self._proto_combo.currentData() or "socks5").lower()
        max_workers = int(self._workers_combo.currentData() or 16)
        include_platform_tests = bool(self._mode_combo.currentData())

        self._proxy_entries = entries
        self._proxy_entry_lines = {
            idx: line_no
            for idx, (line_no, _entry) in enumerate(line_entries, start=1)
        }
        self._proxy_results = {
            idx: enrich_proxy_result(
                {
                    "index": idx,
                    "label": raw,
                    "source": raw,
                    "alive": None,
                    "elapsed_ms": 0.0,
                    "info": "Waiting",
                }
            )
            for idx, raw in enumerate(entries, start=1)
        }
        self._show_result_page()
        self._refresh_proxy_results_view()
        self._set_actions_enabled(False)
        self._is_running = True
        mode_text = "full score" if include_platform_tests else "fast ping"
        self._proxy_summary.setText(f"Checking 0/{len(entries)} proxies ({mode_text})...")

        self._proxy_thread = QThread()
        self._proxy_worker = ProxyPingBatchWorker(
            entries,
            default_proto,
            max_workers=max_workers,
            include_platform_tests=include_platform_tests,
        )
        self._proxy_worker.moveToThread(self._proxy_thread)
        self._proxy_thread.started.connect(self._proxy_worker.run)
        self._proxy_worker.item_result.connect(self._on_proxy_item_result)
        self._proxy_worker.progress.connect(self._on_proxy_progress)
        self._proxy_worker.finished.connect(self._on_proxy_batch_finished)
        self._proxy_worker.finished.connect(self._proxy_thread.quit)
        self._proxy_worker.finished.connect(self._proxy_worker.deleteLater)
        self._proxy_thread.finished.connect(self._proxy_thread.deleteLater)
        self._proxy_thread.finished.connect(self._on_proxy_thread_finished)
        self._proxy_thread.start()

    def _set_actions_enabled(self, enabled: bool):
        for widget in (
            self._proxy_btn,
            self._proxy_clear_btn,
            self._proxy_paste_btn,
            self._proxy_import_btn,
            self._proxy_clean_btn,
            self._proto_combo,
            self._mode_combo,
            self._workers_combo,
            self._view_results_btn,
            self._edit_input_btn,
            self._copy_table_btn,
            self._copy_alive_btn,
            self._export_btn,
            self._new_check_btn,
        ):
            widget.setEnabled(enabled)
            effect = widget.graphicsEffect()
            if not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(widget)
                widget.setGraphicsEffect(effect)
            effect.setOpacity(1.0 if enabled else 0.38)
            widget.setCursor(
                Qt.CursorShape.PointingHandCursor
                if enabled
                else Qt.CursorShape.WaitCursor
            )

    def _on_proxy_item_result(self, result: dict):
        idx = int(result.get("index", 0) or 0)
        if idx:
            self._proxy_results[idx] = result
        self._refresh_proxy_results_view()

    def _on_proxy_progress(self, done: int, total: int):
        self._proxy_summary.setText(f"Checking {done}/{total} proxies...")

    def _on_proxy_batch_finished(self):
        self._is_running = False
        self._set_actions_enabled(True)
        self._proxy_summary.setText("Done")
        self._refresh_proxy_results_view()

    def _on_proxy_thread_finished(self):
        self._proxy_worker = None
        self._proxy_thread = None

    def _filtered_proxy_results(self) -> list[dict]:
        results = list(self._proxy_results.values())
        query = self._proxy_search.text().strip().lower()
        if query:
            results = [item for item in results if query in self._result_search_blob(item)]

        filter_mode = self._proxy_filter_combo.currentData() or "all"
        if filter_mode == "alive":
            results = [item for item in results if item.get("alive") is True]
        elif filter_mode == "dead":
            results = [item for item in results if item.get("alive") is False]
        elif filter_mode == "good":
            results = [item for item in results if (item.get("avg_score") or 0) >= 80]
        elif filter_mode == "review":
            results = [
                item
                for item in results
                if item.get("alive") is True and (item.get("avg_score") or 0) < 80
            ]
        elif filter_mode == "risk":
            results = [item for item in results if item.get("risk_flags")]

        sort_mode = self._proxy_sort_combo.currentData() or "input"
        if sort_mode == "score_desc":
            results.sort(key=lambda item: item.get("avg_score") if item.get("avg_score") is not None else -1, reverse=True)
        elif sort_mode == "score_asc":
            results.sort(key=lambda item: item.get("avg_score") if item.get("avg_score") is not None else 101)
        elif sort_mode == "speed_asc":
            results.sort(key=lambda item: item.get("elapsed_ms", 0.0) or 10**9)
        elif sort_mode == "speed_desc":
            results.sort(key=lambda item: item.get("elapsed_ms", 0.0) or -1, reverse=True)
        elif sort_mode == "status":
            results.sort(key=lambda item: (item.get("alive") is not True, item.get("index", 0)))
        elif sort_mode == "location":
            results.sort(key=lambda item: (_proxy_location(item), item.get("index", 0)))
        elif sort_mode == "type":
            results.sort(key=lambda item: (item.get("proxy_type") or "", item.get("index", 0)))
        else:
            results.sort(key=lambda item: item.get("index", 0))
        return results

    def _result_search_blob(self, item: dict) -> str:
        fields = proxy_table_fields(item)
        parts = [
            fields.get("proxy", ""),
            fields.get("type", ""),
            fields.get("ip_public", ""),
            fields.get("location", ""),
            fields.get("quality", ""),
            fields.get("risk", ""),
            str(item.get("country") or ""),
            str(item.get("country_code") or ""),
            str(item.get("city") or ""),
            str(item.get("region") or ""),
            str(item.get("asn") or ""),
            str(item.get("isp") or ""),
            str(item.get("org") or ""),
            str(item.get("source") or ""),
        ]
        return " ".join(parts).lower()

    def _refresh_proxy_results_view(self):
        selected_index = self._selected_result_index()
        results = self._filtered_proxy_results()
        self._proxy_visible_indexes = [int(item.get("index", 0) or 0) for item in results]

        self._refreshing_table = True
        self._proxy_table.setRowCount(len(results))
        for row, item in enumerate(results):
            self._populate_result_row(row, item)
        self._resize_proxy_column_to_contents()

        if results:
            next_index = selected_index if selected_index in self._proxy_visible_indexes else self._proxy_visible_indexes[0]
            self._select_result_index(next_index)
        self._refreshing_table = False

        self._update_proxy_stats()

    def _populate_result_row(self, row: int, result: dict):
        fields = proxy_table_fields(result)
        for col, (_label, key, _width, align) in enumerate(self.RESULT_COLUMNS):
            text = fields.get(key, "-")
            item = QTableWidgetItem("" if key == "proxy" else text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(align)
            item.setData(Qt.ItemDataRole.UserRole, int(result.get("index", 0) or 0))
            if key in {"avg", "tiktok", "google", "facebook", "instagram"}:
                item.setForeground(QColor(self.TONE_COLORS[score_tone(result.get("avg_score") if key == "avg" else (result.get("platform_scores") or {}).get(key))]))
            elif key == "quality":
                tone = score_tone(result.get("avg_score"))
                item.setForeground(QColor(self.TONE_COLORS[tone]))
                item.setBackground(QColor(self._badge_background(tone)))
            elif key == "tcp":
                item.setForeground(QColor("#34d399" if result.get("tcp_ok") is True else "#fb7185" if result.get("tcp_ok") is False else "#7d8aa1"))
                if result.get("tcp_ok") is not None:
                    item.setBackground(QColor("#10352a" if result.get("tcp_ok") else "#3d1722"))
            elif key == "risk":
                item.setForeground(QColor("#fb7185" if result.get("risk_flags") else "#7d8aa1"))
                if result.get("risk_flags"):
                    item.setBackground(QColor("#3d1722"))
            if key != "proxy":
                item.setToolTip(format_proxy_detail(result) if key in {"risk", "avg"} else text)
            self._proxy_table.setItem(row, col, item)
            if key == "proxy":
                self._proxy_table.setCellWidget(row, col, self._make_proxy_cell(result, text))
        self._proxy_table.setRowHeight(row, 30)

    def _make_proxy_cell(self, result: dict, proxy_text: str) -> QWidget:
        cell = QWidget()
        cell.setObjectName("proxyCell")
        row_index = int(result.get("index", 0) or 0)
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(6, 0, 4, 0)
        layout.setSpacing(5)

        label = QLabel(proxy_text)
        label.setObjectName("proxyCellText")
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        cell.mousePressEvent = lambda event, idx=row_index: self._on_proxy_cell_pressed(event, idx)
        label.mousePressEvent = lambda event, idx=row_index: self._on_proxy_cell_pressed(event, idx)
        layout.addWidget(label, 1)

        copy_btn = QPushButton()
        copy_btn.setObjectName("proxyCellCopyBtn")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        copy_btn.setFixedSize(22, 22)
        copy_btn.setToolTip("Copy proxy")
        copy_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        copy_btn.setIconSize(QSize(13, 13))
        copy_btn.clicked.connect(
            lambda _checked=False, text=proxy_text: self._copy_proxy_text(text)
        )
        layout.addWidget(copy_btn)
        return cell

    def _on_proxy_cell_pressed(self, event, index: int):
        self._select_result_index(index)
        self._display_result_detail(index, show_popover=True)
        event.accept()

    def _copy_proxy_text(self, text: str):
        QApplication.clipboard().setText(text)
        self._proxy_summary.setText("Copied proxy")

    def _resize_proxy_column_to_contents(self):
        proxy_col = self._column_index("proxy")
        if proxy_col >= 0:
            self._proxy_table.resizeColumnToContents(proxy_col)

    def _column_index(self, key: str) -> int:
        for index, (_label, column_key, _width, _align) in enumerate(self.RESULT_COLUMNS):
            if column_key == key:
                return index
        return -1

    def _badge_background(self, tone: str) -> str:
        return {
            "good": "#10352a",
            "warn": "#33280f",
            "bad": "#3d1722",
            "muted": "#1f2a44",
        }.get(tone, "#1f2a44")

    def _selected_result_index(self) -> int:
        selected = self._proxy_table.selectedItems()
        if not selected:
            return 0
        return int(selected[0].data(Qt.ItemDataRole.UserRole) or 0)

    def _select_result_index(self, index: int):
        for row in range(self._proxy_table.rowCount()):
            item = self._proxy_table.item(row, 0)
            if item and int(item.data(Qt.ItemDataRole.UserRole) or 0) == index:
                self._proxy_table.selectRow(row)
                return

    def _on_result_selection_changed(self):
        index = self._selected_result_index()
        if not index:
            return
        self._display_result_detail(index, show_popover=not self._refreshing_table)

    def _on_result_item_entered(self, item: QTableWidgetItem):
        index = int(item.data(Qt.ItemDataRole.UserRole) or 0)
        if index:
            self._display_result_detail(index, item=item, show_popover=True)

    def _on_result_item_clicked(self, item: QTableWidgetItem):
        index = int(item.data(Qt.ItemDataRole.UserRole) or 0)
        if index:
            self._display_result_detail(index, item=item, show_popover=True)

    def _display_result_detail(
        self,
        index: int,
        *,
        item: QTableWidgetItem | None = None,
        show_popover: bool = False,
    ):
        result = self._proxy_results.get(index)
        if not result:
            return
        detail = format_proxy_detail(result)
        if show_popover:
            if item is None:
                row = self._row_for_result_index(index)
                item = self._proxy_table.item(row, 1) if row >= 0 else None
            if item is not None:
                rect = self._proxy_table.visualItemRect(item)
                pos = self._proxy_table.viewport().mapToGlobal(
                    QPoint(rect.left() + 12, rect.bottom() + 8)
                )
                QToolTip.showText(pos, detail, self._proxy_table)

    def _row_for_result_index(self, index: int) -> int:
        for row in range(self._proxy_table.rowCount()):
            item = self._proxy_table.item(row, 0)
            if item and int(item.data(Qt.ItemDataRole.UserRole) or 0) == index:
                return row
        return -1

    def _visible_results(self) -> list[dict]:
        return [
            self._proxy_results[index]
            for index in self._proxy_visible_indexes
            if index in self._proxy_results
        ]

    def _copy_visible_results(self):
        results = self._visible_results()
        if not results:
            self._proxy_summary.setText("No visible results to copy")
            return
        header = "\t".join(
            [
                "#",
                "proxy",
                "type",
                "public_ip",
                "location",
                "ms",
                "tcp",
                "avg",
                "quality",
                "risk",
            ]
        )
        lines = [header] + [format_proxy_clipboard_line(item) for item in results]
        QApplication.clipboard().setText("\n".join(lines))
        self._proxy_summary.setText(f"Copied {len(results)} visible rows")

    def _copy_alive_sources(self):
        alive_lines = [
            str(item.get("source") or item.get("label") or "").strip()
            for item in self._proxy_results.values()
            if item.get("alive") is True
        ]
        alive_lines = [line for line in alive_lines if line]
        if not alive_lines:
            self._proxy_summary.setText("No alive proxies to copy")
            return
        QApplication.clipboard().setText("\n".join(alive_lines))
        self._proxy_summary.setText(f"Copied {len(alive_lines)} alive proxies")

    def _export_proxy_results(self):
        results = self._visible_results()
        if not results:
            QMessageBox.information(self, "Export", "No visible proxy results to export.")
            return

        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export proxy results",
            "proxy_results.csv",
            "CSV files (*.csv);;JSON files (*.json);;Text files (*.txt)",
        )
        if not path:
            return

        fmt = "csv"
        lower_path = path.lower()
        if lower_path.endswith(".json") or "JSON" in selected_filter:
            fmt = "json"
        elif lower_path.endswith(".txt") or "Text" in selected_filter:
            fmt = "txt"

        try:
            if fmt == "json":
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump([export_proxy_row(item) for item in results], fh, indent=2, ensure_ascii=False)
            elif fmt == "txt":
                with open(path, "w", encoding="utf-8") as fh:
                    for item in results:
                        fh.write(format_proxy_clipboard_line(item) + "\n")
            else:
                rows = [export_proxy_row(item) for item in results]
                fieldnames = list(rows[0].keys())
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
                    writer.writeheader()
                    writer.writerows(rows)
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", str(exc))
            return

        self._proxy_summary.setText(f"Exported {len(results)} rows")

    def _update_proxy_stats(self):
        total = len(self._proxy_results)
        done = sum(1 for item in self._proxy_results.values() if item.get("alive") is not None)
        alive = sum(1 for item in self._proxy_results.values() if item.get("alive") is True)
        dead = sum(1 for item in self._proxy_results.values() if item.get("alive") is False)
        pending = total - done
        visible = len(self._proxy_visible_indexes)
        scores = [
            item.get("avg_score")
            for item in self._proxy_results.values()
            if item.get("alive") is True and item.get("avg_score") is not None
        ]
        good = sum(1 for item in self._proxy_results.values() if (item.get("avg_score") or 0) >= 80)
        fair = sum(1 for item in self._proxy_results.values() if 60 <= (item.get("avg_score") or 0) < 80)
        weak = sum(1 for item in self._proxy_results.values() if 35 <= (item.get("avg_score") or 0) < 60)
        bad = sum(
            1
            for item in self._proxy_results.values()
            if item.get("avg_score") is not None and (item.get("avg_score") or 0) < 35
        )
        risk = sum(1 for item in self._proxy_results.values() if item.get("risk_flags"))
        avg_score = sum(scores) / len(scores) if scores else 0
        speeds = [
            item.get("elapsed_ms", 0.0)
            for item in self._proxy_results.values()
            if item.get("alive") is True and item.get("elapsed_ms", 0.0) > 0
        ]
        avg_ms = sum(speeds) / len(speeds) if speeds else 0
        suffix = ""
        if avg_score:
            suffix += f" | avg score {avg_score:.0f}"
        if avg_ms:
            suffix += f" | avg {avg_ms:.0f} ms"
        self._proxy_stats_lbl.setText(
            f"Stats: total {total} | done {done} | alive {alive} | dead {dead} | visible {visible}{suffix}"
        )
        if hasattr(self, "_stats_chart"):
            self._stats_chart.set_stats(
                {
                    "total": total,
                    "alive": alive,
                    "dead": dead,
                    "pending": pending,
                    "good": good,
                    "fair": fair,
                    "weak": weak,
                    "bad": bad,
                    "risk": risk,
                }
            )
