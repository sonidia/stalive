from __future__ import annotations

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from ping import ProxyPingBatchWorker, _format_proxy_result_line, _proxy_location

from .common import (
    COMPACT_CONTROL_HEIGHT,
    LinkedPlainTextEdit,
    build_tool_shell,
    make_hint,
    make_section,
    make_tool_button,
)

class ProxyTab(QWidget):
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

        self._build_ui()

    def _build_ui(self):
        outer, layout = build_tool_shell(
            self,
            "Proxy",
            self._show_close_button,
            self._close_handler,
            self._outer_margins,
        )
        layout.addWidget(make_section("Proxy TCP ping"))
        layout.addWidget(
            make_hint(
                "Enter one proxy per line in <b>any format</b>. "
                "Select the default protocol if the string does not have a scheme."
            )
        )

        fmt_hint = QLabel(
            "<code>host:port</code>  ·  "
            "<code>host:port:user:pass</code>  ·  "
            "<code>user:pass@host:port</code>  ·  "
            "<code>socks5h://user:pass@host:port</code>  ·  "
            "<code>http://user:pass@host:port</code>"
        )
        fmt_hint.setWordWrap(True)
        fmt_hint.setObjectName("toolFormatHint")
        layout.addWidget(fmt_hint)

        self._proxy_input = LinkedPlainTextEdit()
        self._proxy_input.setObjectName("toolTextArea")
        self._proxy_input.setPlaceholderText(
            "host:port\nhost:port:user:pass\nsocks5h://user:pass@host:port"
        )
        self._proxy_input.setToolTip("Paste or type one proxy per line. Empty lines are ignored.")
        self._proxy_input.setMinimumHeight(250)
        self._proxy_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self._proxy_result = LinkedPlainTextEdit()
        self._proxy_result.setObjectName("toolOutput")
        self._proxy_result.setReadOnly(True)
        self._proxy_result.setMinimumHeight(250)
        self._proxy_result.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._proxy_result.setPlaceholderText("Line-by-line results will appear here.")
        self._proxy_result.setToolTip(
            "Proxy results align with input lines. Hover one side to highlight the matching row."
        )

        io_row = QHBoxLayout()
        io_row.setSpacing(10)
        io_row.addWidget(self._proxy_input, 1)
        io_row.addWidget(self._proxy_result, 1)
        layout.addLayout(io_row, 1)
        self._proxy_input.line_hovered.connect(self._on_proxy_input_hover)
        self._proxy_result.line_hovered.connect(self._on_proxy_result_hover)

        layout.addLayout(self._build_action_row())

        self._proxy_summary = QLabel("Ready")
        self._proxy_summary.setObjectName("toolHint")
        layout.addWidget(self._proxy_summary)

        layout.addLayout(self._build_stats_row())
        if not self._show_close_button:
            outer.addStretch(1)

    def _build_action_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        self._proto_combo = QComboBox()
        self._proto_combo.addItem("HTTP", "http")
        self._proto_combo.addItem("HTTPS", "https")
        self._proto_combo.addItem("SOCKS5", "socks5")
        self._proto_combo.addItem("SOCKS4", "socks4")
        self._proto_combo.setCurrentIndex(2)
        self._proto_combo.currentIndexChanged.connect(self._refresh_proto_combo_labels)
        self._refresh_proto_combo_labels()
        self._proto_combo.setFixedHeight(COMPACT_CONTROL_HEIGHT)
        self._proto_combo.setFixedWidth(132)
        self._proto_combo.setToolTip(
            "Default protocol. Only applies when the proxy string has no scheme."
        )
        row.addWidget(self._proto_combo)
        row.addStretch()

        self._proxy_paste_btn = make_tool_button(
            "📋 Paste",
            self._paste_proxy_clipboard,
            tooltip="Paste proxy lines from the clipboard.",
        )
        self._proxy_import_btn = make_tool_button(
            "📄 Import .txt",
            self._import_proxy_file,
            tooltip="Import proxies from a .txt file.",
        )
        self._proxy_clear_btn = make_tool_button(
            "✕ Clear",
            self._clear_proxy_results,
            tooltip="Clear proxy input, results, and statistics.",
        )
        self._proxy_btn = make_tool_button(
            "📡 Ping all",
            self._run_proxy_ping,
            accent=True,
            tooltip="Ping all proxy lines in parallel and fetch response IP details.",
        )
        row.addWidget(self._proxy_paste_btn)
        row.addWidget(self._proxy_import_btn)
        row.addWidget(self._proxy_clear_btn)
        row.addWidget(self._proxy_btn)
        return row

    def _build_stats_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        self._proxy_stats_lbl = QLabel("Stats: total 0 · done 0 · alive 0 · dead 0")
        self._proxy_stats_lbl.setObjectName("toolHint")
        self._proxy_stats_lbl.setToolTip("Summary of current proxy results.")
        row.addWidget(self._proxy_stats_lbl, 1)

        self._proxy_filter_combo = QComboBox()
        self._proxy_filter_combo.addItems(["All", "Alive", "Dead"])
        self._proxy_filter_combo.setFixedHeight(COMPACT_CONTROL_HEIGHT)
        self._proxy_filter_combo.setMinimumWidth(108)
        self._proxy_filter_combo.setToolTip("Filter proxy results by status.")
        self._proxy_filter_combo.currentTextChanged.connect(
            lambda _text: self._refresh_proxy_results_view()
        )
        row.addWidget(self._proxy_filter_combo)

        self._proxy_sort_combo = QComboBox()
        self._proxy_sort_combo.addItems(["Input order", "Speed ↑", "Speed ↓", "Status", "Location"])
        self._proxy_sort_combo.setFixedHeight(COMPACT_CONTROL_HEIGHT)
        self._proxy_sort_combo.setMinimumWidth(154)
        self._proxy_sort_combo.setToolTip("Sort visible proxy results.")
        self._proxy_sort_combo.currentTextChanged.connect(
            lambda _text: self._refresh_proxy_results_view()
        )
        row.addWidget(self._proxy_sort_combo)
        return row

    def _refresh_proto_combo_labels(self):
        for index in range(self._proto_combo.count()):
            value = self._proto_combo.itemData(index)
            label = str(value or self._proto_combo.itemText(index)).upper()
            prefix = "✓ " if index == self._proto_combo.currentIndex() else "  "
            self._proto_combo.setItemText(index, f"{prefix}{label}")

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
        self._proxy_input.clear()
        self._proxy_result.clear()
        self._proxy_entry_lines.clear()
        self._proxy_results.clear()
        self._proxy_visible_indexes.clear()
        self._proxy_summary.setText("Ready")
        self._update_proxy_stats()

    def _run_proxy_ping(self):
        raw_lines = self._proxy_input.toPlainText().splitlines()
        line_entries = [
            (line_no, line.strip())
            for line_no, line in enumerate(raw_lines)
            if line.strip()
        ]
        entries = [entry for _line_no, entry in line_entries]
        if not entries:
            self._proxy_result.setPlainText("Please enter at least one proxy address.")
            self._proxy_summary.setText("No proxies")
            return

        default_proto = str(self._proto_combo.currentData() or "socks5").lower()
        self._proxy_entries = entries
        self._proxy_entry_lines = {
            idx: line_no
            for idx, (line_no, _entry) in enumerate(line_entries, start=1)
        }
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
        self._set_actions_enabled(False)
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

    def _set_actions_enabled(self, enabled: bool):
        self._proxy_btn.setEnabled(enabled)
        self._proxy_clear_btn.setEnabled(enabled)
        self._proxy_paste_btn.setEnabled(enabled)
        self._proxy_import_btn.setEnabled(enabled)

    def _on_proxy_item_result(self, result: dict):
        idx = int(result.get("index", 0) or 0)
        if idx:
            self._proxy_results[idx] = result
        self._refresh_proxy_results_view()

    def _on_proxy_progress(self, done: int, total: int):
        self._proxy_summary.setText(f"Pinging {done}/{total} proxies...")

    def _on_proxy_batch_finished(self):
        self._set_actions_enabled(True)
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
            f"Stats: total {total} · done {done} · alive {alive} · dead {dead} · "
            f"visible {visible}{avg_text}"
        )

    def _on_proxy_input_hover(self, input_line: int):
        self._proxy_input.set_highlight_line(-1)
        result_line = -1
        if input_line >= 0:
            block = self._proxy_input.document().findBlockByNumber(input_line)
            if block.isValid() and block.text().strip():
                for input_index, line_no in self._proxy_entry_lines.items():
                    if line_no == input_line and input_index in self._proxy_visible_indexes:
                        result_line = self._proxy_visible_indexes.index(input_index)
                        break
        self._proxy_result.set_highlight_line(result_line)

    def _on_proxy_result_hover(self, result_line: int):
        self._proxy_result.set_highlight_line(-1)
        input_line = -1
        if 0 <= result_line < len(self._proxy_visible_indexes):
            input_index = self._proxy_visible_indexes[result_line]
            input_line = self._proxy_entry_lines.get(input_index, input_index - 1)
        self._proxy_input.set_highlight_line(input_line)


# Compatibility shim: keep imports from tabs.proxy working while the richer,
# easier-to-maintain implementation lives in its own module.
from .proxy_quality import ProxyTab as ProxyTab
