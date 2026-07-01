from __future__ import annotations

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from ping import (
    PortBatchWorker,
    _format_port_result_line,
    _parse_port_range,
    _split_batch_text,
)
from utils import current_ipv4

from .common import (
    COMPACT_CONTROL_HEIGHT,
    build_tool_shell,
    make_action_row,
    make_hint,
    make_section,
    make_text_area,
    make_tool_button,
)


class HostTab(QWidget):
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
        outer, layout = build_tool_shell(
            self,
            "Host",
            self._show_close_button,
            self._close_handler,
            self._outer_margins,
        )

        columns = QHBoxLayout()
        columns.setSpacing(12)
        columns.addLayout(self._build_check_column(), 1)
        columns.addLayout(self._build_scan_column(), 1)
        layout.addLayout(columns)

        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        self._port_summary = QLabel("Check: ready")
        self._port_summary.setObjectName("toolHint")
        self._port_summary.setToolTip("Status for manual host:port checks.")
        self._scan_summary = QLabel("Scan: ready")
        self._scan_summary.setObjectName("toolHint")
        self._scan_summary.setToolTip("Status for local host port scans.")
        status_row.addWidget(self._port_summary, 1)
        status_row.addWidget(self._scan_summary, 1)
        layout.addLayout(status_row)

        layout.addWidget(make_section("Result"))
        self._port_result = make_text_area(
            "Check and scan results will appear here.",
            tooltip="Shared result output for both Check port and Scan host.",
            minimum_height=230,
            read_only=True,
            output=True,
        )
        layout.addWidget(self._port_result, 1)

        if not self._show_close_button:
            outer.addStretch(1)

    def _build_check_column(self) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setSpacing(8)
        column.addWidget(make_section("Check port"))
        column.addWidget(
            make_hint(
                "Enter one target per line. Use <b>host:port</b> or just <b>port</b> "
                "to check against this machine's current IPv4."
            )
        )

        self._port_input = make_text_area(
            "8.8.8.8:53\n1.1.1.1:443\n2000",
            tooltip="One target per line. Use host:port, or only port to use this host.",
            minimum_height=145,
        )
        column.addWidget(self._port_input, 1)

        self._port_clear_btn = make_tool_button(
            "✕ Clear",
            self._clear_port_results,
            tooltip="Clear check-port input and the shared result output.",
        )
        self._port_btn = make_tool_button(
            "⚡ Check all",
            self._run_port_check,
            accent=True,
            tooltip="Check all listed host:port targets using parallel TCP connections.",
        )
        column.addLayout(make_action_row(self._port_clear_btn, self._port_btn))
        return column

    def _build_scan_column(self) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setSpacing(8)
        column.addWidget(make_section("Scan host"))
        column.addWidget(
            make_hint(
                "Scan open ports on this machine's current IPv4. Use ranges like "
                "<b>1-1024</b>, <b>2000</b>, or <b>3000-3010</b>."
            )
        )

        scan_row = QHBoxLayout()
        scan_row.setSpacing(8)
        self._scan_range_edit = QLineEdit("1-1024")
        self._scan_range_edit.setPlaceholderText("1-1024,2000,3000-3010")
        self._scan_range_edit.setFixedHeight(COMPACT_CONTROL_HEIGHT)
        self._scan_range_edit.setToolTip("Ports to scan on this host. Separate ranges with commas.")
        scan_row.addWidget(self._scan_range_edit, 1)

        self._scan_btn = make_tool_button(
            "🔎 Scan",
            self._run_host_scan,
            accent=True,
            tooltip="Scan this host for open ports using parallel TCP probes.",
        )
        scan_row.addWidget(self._scan_btn)
        column.addLayout(scan_row)

        self._scan_clear_btn = make_tool_button(
            "✕ Clear",
            self._clear_scan_results,
            tooltip="Clear the shared result output.",
        )
        column.addLayout(make_action_row(self._scan_clear_btn))
        column.addStretch(1)
        return column

    def _clear_port_results(self):
        self._port_input.clear()
        self._port_result.clear()
        self._port_summary.setText("Check: ready")

    def _clear_scan_results(self):
        self._port_result.clear()
        self._scan_summary.setText("Scan: ready")

    def _run_port_check(self):
        targets = _split_batch_text(self._port_input.toPlainText())
        if not targets:
            self._port_result.setPlainText("Please enter host:port or a port number.")
            self._port_summary.setText("Check: no targets")
            return

        self._port_result.clear()
        self._port_mode = "check"
        self._scan_found_count = 0
        self._set_controls_enabled(False)
        self._port_summary.setText(f"Check: 0/{len(targets)} targets")

        self._port_thread = QThread()
        self._port_worker = PortBatchWorker(targets, timeout=5.0, max_workers=64)
        self._start_worker()

    def _run_host_scan(self):
        try:
            ports = _parse_port_range(self._scan_range_edit.text() or "1-1024")
        except ValueError:
            self._port_result.setPlainText("Invalid port range.")
            self._scan_summary.setText("Scan: invalid range")
            return

        if not ports:
            self._port_result.setPlainText("No ports to scan.")
            self._scan_summary.setText("Scan: no ports")
            return

        host = current_ipv4() or "127.0.0.1"
        targets = [f"{host}:{port}" for port in ports]
        self._port_result.clear()
        self._port_mode = "scan"
        self._scan_found_count = 0
        self._set_controls_enabled(False)
        self._scan_summary.setText(f"Scan: {host} 0/{len(targets)} ports")

        self._port_thread = QThread()
        self._port_worker = PortBatchWorker(
            targets,
            timeout=0.25,
            max_workers=256,
            emit_closed=False,
        )
        self._start_worker()

    def _start_worker(self):
        self._port_worker.moveToThread(self._port_thread)
        self._port_thread.started.connect(self._port_worker.run)
        self._port_worker.item_result.connect(self._on_port_item_result)
        self._port_worker.progress.connect(self._on_port_progress)
        self._port_worker.finished.connect(self._on_port_batch_finished)
        self._port_worker.finished.connect(self._port_thread.quit)
        self._port_worker.finished.connect(self._port_worker.deleteLater)
        self._port_thread.finished.connect(self._port_thread.deleteLater)
        self._port_thread.start()

    def _set_controls_enabled(self, enabled: bool):
        self._port_btn.setEnabled(enabled)
        self._scan_btn.setEnabled(enabled)
        self._port_clear_btn.setEnabled(enabled)
        self._scan_clear_btn.setEnabled(enabled)

    def _on_port_item_result(self, result: dict):
        if self._port_mode == "scan" and result.get("alive"):
            self._scan_found_count += 1
        self._port_result.appendPlainText(_format_port_result_line(result))

    def _on_port_progress(self, done: int, total: int):
        if self._port_mode == "scan":
            self._scan_summary.setText(
                f"Scan: {done}/{total} ports, open {self._scan_found_count}"
            )
        else:
            self._port_summary.setText(f"Check: {done}/{total} targets")

    def _on_port_batch_finished(self):
        self._set_controls_enabled(True)
        if self._port_mode == "scan":
            if self._scan_found_count == 0:
                self._port_result.appendPlainText("No open ports found.")
            self._scan_summary.setText(f"Scan: done, open {self._scan_found_count}")
        else:
            self._port_summary.setText("Check: done")
