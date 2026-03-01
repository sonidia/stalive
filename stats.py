"""
stats.py — Thống kê & Phân tích Proxy
Chứa: StatsCollector (singleton), PingChartWidget, StatsModal
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import TYPE_CHECKING, Callable, List, Tuple

from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import (
    QColor, QPainter, QPen, QBrush, QPainterPath, QLinearGradient,
)
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from shared import PALETTE


# ─── Stats Collector ──────────────────────────────────────────────────────────

class StatsCollector:
    """
    Singleton – thu thập thống kê toàn cục:
      • ping_history        : list of (unix_timestamp, ping_ms)
      • refresh_success_count
      • refresh_fail_count
    """
    _instance: "StatsCollector | None" = None

    def __new__(cls) -> "StatsCollector":
        if cls._instance is None:
            obj = super().__new__(cls)
            obj.ping_history: List[Tuple[float, float]] = []
            obj.refresh_success_count: int = 0
            obj.refresh_fail_count: int = 0
            cls._instance = obj
        return cls._instance

    # ── Recording ──────────────────────────────────────────────────────────

    def record_ping(self, ping_ms: float) -> None:
        """Record one successful ping reading."""
        self.ping_history.append((time.time(), float(ping_ms)))
        # Keep only last 200 readings to avoid unbounded growth
        if len(self.ping_history) > 200:
            self.ping_history = self.ping_history[-200:]

    def record_refresh_success(self) -> None:
        self.refresh_success_count += 1

    def record_refresh_fail(self) -> None:
        self.refresh_fail_count += 1

    # ── Queries ────────────────────────────────────────────────────────────

    def avg_ping(self) -> float | None:
        pings = [p for _, p in self.ping_history]
        return sum(pings) / len(pings) if pings else None

    def reset(self) -> None:
        self.ping_history.clear()
        self.refresh_success_count = 0
        self.refresh_fail_count = 0


# Module-level singleton – import this in app.py
stats_collector = StatsCollector()


# ─── Ping Chart Widget ────────────────────────────────────────────────────────

class PingChartWidget(QWidget):
    """Vẽ biểu đồ đường (line chart) ping theo thời gian bằng QPainter."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(170)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._data: List[Tuple[float, float]] = []

    def set_data(self, data: List[Tuple[float, float]]) -> None:
        self._data = data
        self.update()

    # ── Paint ──────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(PALETTE["entry_bg"]))

        # Border
        painter.setPen(QPen(QColor(PALETTE["border"]), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 6, 6)

        if not self._data or len(self._data) < 2:
            painter.setPen(QColor(PALETTE["subtext"]))
            font = painter.font()
            font.setPointSizeF(9)
            painter.setFont(font)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Chưa có dữ liệu ping\n(hãy Check proxy để bắt đầu)",
            )
            painter.end()
            return

        PAD_L, PAD_R, PAD_T, PAD_B = 50, 18, 22, 34
        cw = self.width()  - PAD_L - PAD_R
        ch = self.height() - PAD_T - PAD_B

        pings   = [p for _, p in self._data]
        ts_list = [t for t, _ in self._data]

        min_p   = max(0.0, min(pings) - 15)
        max_p   = max(pings) + 15
        p_range = (max_p - min_p) or 1.0

        t_min   = ts_list[0]
        t_max   = ts_list[-1]
        t_range = (t_max - t_min) or 1.0

        def xp(ts: float) -> float:
            return PAD_L + (ts - t_min) / t_range * cw

        def yp(ping: float) -> float:
            return PAD_T + ch - (ping - min_p) / p_range * ch

        # ── Grid lines ──
        grid_pen = QPen(QColor(PALETTE["border"]), 1, Qt.PenStyle.DotLine)
        grid_count = 4
        font = painter.font()
        font.setPointSizeF(7.5)
        painter.setFont(font)

        for i in range(grid_count + 1):
            gy = PAD_T + i * ch // grid_count
            painter.setPen(grid_pen)
            painter.drawLine(PAD_L, gy, PAD_L + cw, gy)
            ping_val = max_p - i * p_range / grid_count
            painter.setPen(QColor(PALETTE["subtext"]))
            painter.drawText(
                QRect(0, int(gy) - 8, PAD_L - 6, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{ping_val:.0f}",
            )

        # ── Y-axis label "ms" ──
        painter.setPen(QColor(PALETTE["label"]))
        font2 = painter.font()
        font2.setPointSizeF(7.0)
        painter.setFont(font2)
        painter.drawText(QRect(0, PAD_T - 14, PAD_L - 6, 14),
                         Qt.AlignmentFlag.AlignRight,
                         "ms")

        # ── Fill path (gradient under line) ──
        fill_path = QPainterPath()
        x0, y0 = xp(ts_list[0]), yp(pings[0])
        fill_path.moveTo(x0, PAD_T + ch)
        fill_path.lineTo(x0, y0)
        for i in range(1, len(self._data)):
            fill_path.lineTo(xp(ts_list[i]), yp(pings[i]))
        fill_path.lineTo(xp(ts_list[-1]), PAD_T + ch)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, PAD_T, 0, PAD_T + ch)
        accent_a = QColor(PALETTE["accent"]); accent_a.setAlpha(70)
        accent_0 = QColor(PALETTE["accent"]); accent_0.setAlpha(0)
        grad.setColorAt(0.0, accent_a)
        grad.setColorAt(1.0, accent_0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawPath(fill_path)

        # ── Line path ──
        line_path = QPainterPath()
        line_path.moveTo(xp(ts_list[0]), yp(pings[0]))
        for i in range(1, len(self._data)):
            line_path.lineTo(xp(ts_list[i]), yp(pings[i]))

        pen = QPen(QColor(PALETTE["accent"]), 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(pen)
        painter.drawPath(line_path)

        # ── Dots for last ≤30 points ──
        recent = self._data[-min(30, len(self._data)):]
        painter.setBrush(QBrush(QColor(PALETTE["accent"])))
        painter.setPen(Qt.PenStyle.NoPen)
        for ts, p in recent:
            painter.drawEllipse(int(xp(ts)) - 2, int(yp(p)) - 2, 5, 5)

        # ── X-axis time labels ──
        painter.setPen(QColor(PALETTE["subtext"]))
        font3 = painter.font()
        font3.setPointSizeF(7.5)
        painter.setFont(font3)
        t_start_str = datetime.fromtimestamp(ts_list[0]).strftime("%H:%M:%S")
        t_end_str   = datetime.fromtimestamp(ts_list[-1]).strftime("%H:%M:%S")
        painter.drawText(
            QRect(PAD_L, PAD_T + ch + 6, 70, 18),
            Qt.AlignmentFlag.AlignLeft,
            t_start_str,
        )
        painter.drawText(
            QRect(PAD_L + cw - 70, PAD_T + ch + 6, 70, 18),
            Qt.AlignmentFlag.AlignRight,
            t_end_str,
        )

        painter.end()


# ─── Stat Card helper ─────────────────────────────────────────────────────────

def _make_stat_card(
    title:        str,
    initial_val:  str = "—",
    initial_sub:  str = "",
    accent_color: str = PALETTE["accent"],
) -> QWidget:
    """Tạo một card hiển thị 1 chỉ số thống kê."""
    card = QWidget()
    card.setObjectName("statsCard")
    card.setStyleSheet(
        f"QWidget#statsCard {{"
        f"  background: {PALETTE['card']};"
        f"  border: 1.5px solid {PALETTE['border']};"
        f"  border-radius: 10px;"
        f"}}"
    )
    lay = QVBoxLayout(card)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(4)

    title_lbl = QLabel(title)
    title_lbl.setStyleSheet(
        f"color: {PALETTE['subtext']}; font-size: 7.5pt; font-weight: 700;"
        f"letter-spacing: 0.4px; background: transparent;"
    )
    lay.addWidget(title_lbl)

    val_lbl = QLabel(initial_val)
    val_lbl.setObjectName("statValue")
    val_lbl.setStyleSheet(
        f"color: {accent_color}; font-size: 20pt; font-weight: 700; background: transparent;"
    )
    lay.addWidget(val_lbl)

    sub_lbl = QLabel(initial_sub)
    sub_lbl.setObjectName("statSub")
    sub_lbl.setStyleSheet(
        f"color: {PALETTE['label']}; font-size: 7.5pt; background: transparent;"
    )
    lay.addWidget(sub_lbl)

    return card


# ─── Stats Modal ──────────────────────────────────────────────────────────────

class StatsModal(QDialog):
    """
    Modal hiển thị Thống Kê & Phân Tích:
      - Tỷ lệ proxy sống / chết
      - Ping trung bình
      - Số lần refresh thành công
      - Biểu đồ ping theo thời gian
    """

    def __init__(self, get_cards_fn: Callable, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._get_cards_fn = get_cards_fn
        self.setWindowTitle("Thống Kê & Phân Tích")
        self.setFixedSize(580, 540)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build()

    # ── Build UI ──────────────────────────────────────────────────────────

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Outer container (rounded panel)
        container = QWidget()
        container.setObjectName("statsContainer")
        container.setStyleSheet(
            f"QWidget#statsContainer {{"
            f"  background: {PALETTE['panel']};"
            f"  border: 1.5px solid {PALETTE['border']};"
            f"  border-radius: 14px;"
            f"}}"
        )
        outer.addWidget(container)

        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 20, 24, 22)
        lay.setSpacing(14)

        # ── Header ────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(8)

        title_lbl = QLabel("📊  Thống Kê & Phân Tích")
        title_lbl.setStyleSheet(
            f"color: {PALETTE['text']}; font-size: 12pt;"
            f" font-weight: 700; background: transparent;"
        )
        hdr.addWidget(title_lbl)
        hdr.addStretch()

        refresh_btn = QPushButton("↻")
        refresh_btn.setToolTip("Làm mới số liệu")
        refresh_btn.setFixedSize(28, 28)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {PALETTE['card']}; color: {PALETTE['accent2']};"
            f"  border: 1px solid {PALETTE['border']}; border-radius: 6px;"
            f"  font-size: 13pt; padding: 0;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {PALETTE['accent']}; color: #fff;"
            f"  border-color: {PALETTE['accent']};"
            f"}}"
        )
        refresh_btn.clicked.connect(self._refresh_stats)
        hdr.addWidget(refresh_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {PALETTE['card']}; color: {PALETTE['subtext']};"
            f"  border: 1px solid {PALETTE['border']}; border-radius: 6px;"
            f"  font-size: 10pt; padding: 0;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {PALETTE['error']}; color: #fff;"
            f"  border-color: {PALETTE['error']};"
            f"}}"
        )
        close_btn.clicked.connect(self.close)
        hdr.addWidget(close_btn)

        lay.addLayout(hdr)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {PALETTE['border']}; border: none;")
        lay.addWidget(div)

        # ── Stat cards row ─────────────────────────────────────────────────
        self._alive_card   = _make_stat_card(
            "PROXY SỐNG / CHẾT", "—", "", PALETTE["success"]
        )
        self._ping_card    = _make_stat_card(
            "PING TRUNG BÌNH",   "—", "milliseconds", PALETTE["warning"]
        )
        self._refresh_card = _make_stat_card(
            "REFRESH THÀNH CÔNG", "—", "", PALETTE["accent2"]
        )

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        for c in (self._alive_card, self._ping_card, self._refresh_card):
            cards_row.addWidget(c, 1)
        lay.addLayout(cards_row)

        # ── Chart section ──────────────────────────────────────────────────
        chart_title = QLabel("BIỂU ĐỒ PING THEO THỜI GIAN")
        chart_title.setStyleSheet(
            f"color: {PALETTE['subtext']}; font-size: 7.5pt; font-weight: 700;"
            f" letter-spacing: 0.5px; background: transparent;"
        )
        lay.addWidget(chart_title)

        self._chart = PingChartWidget()
        lay.addWidget(self._chart, 1)

        # ── Footer ────────────────────────────────────────────────────────
        self._footer_lbl = QLabel("")
        self._footer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._footer_lbl.setStyleSheet(
            f"color: {PALETTE['subtext']}; font-size: 7.5pt; background: transparent;"
        )
        lay.addWidget(self._footer_lbl)

    # ── Helpers: find child labels by objectName ───────────────────────────

    @staticmethod
    def _val_lbl(card: QWidget) -> QLabel | None:
        return card.findChild(QLabel, "statValue")

    @staticmethod
    def _sub_lbl(card: QWidget) -> QLabel | None:
        return card.findChild(QLabel, "statSub")

    # ── Refresh stats ─────────────────────────────────────────────────────

    def _refresh_stats(self) -> None:
        """Tính toán lại và cập nhật tất cả số liệu."""
        collector = stats_collector
        cards = self._get_cards_fn()

        # ── Alive / Dead ──
        alive = sum(
            1 for c in cards
            if getattr(c, "_status_lbl", None) is not None
            and c._status_lbl.objectName() == "statusAlive"
        )
        dead = sum(
            1 for c in cards
            if getattr(c, "_status_lbl", None) is not None
            and c._status_lbl.objectName() == "statusDead"
        )
        total = len(cards)
        pct   = f"{alive / total * 100:.0f}%" if total else "0%"

        alive_val = self._val_lbl(self._alive_card)
        alive_sub = self._sub_lbl(self._alive_card)
        if alive_val:
            alive_val.setText(f"{alive}/{total}")
            color = PALETTE["success"] if alive > 0 else PALETTE["subtext"]
            alive_val.setStyleSheet(
                f"color: {color}; font-size: 20pt; font-weight: 700; background: transparent;"
            )
        if alive_sub:
            alive_sub.setText(
                f"{pct} còn sống  •  {dead} chết"
                if total else "Chưa có proxy"
            )

        # ── Average ping ──
        avg = collector.avg_ping()
        ping_val = self._val_lbl(self._ping_card)
        ping_sub = self._sub_lbl(self._ping_card)
        if ping_val:
            ping_val.setText(f"{avg:.0f}" if avg is not None else "—")
        if ping_sub:
            if avg is not None:
                color = (
                    PALETTE["success"] if avg < 150
                    else PALETTE["warning"] if avg < 400
                    else PALETTE["error"]
                )
                level = "Tốt" if avg < 150 else ("Trung bình" if avg < 400 else "Chậm")
                ping_sub.setText(f"milliseconds  •  {level}")
                if ping_val:
                    ping_val.setStyleSheet(
                        f"color: {color}; font-size: 20pt; font-weight: 700; background: transparent;"
                    )
            else:
                ping_sub.setText("milliseconds")

        # ── Refresh count ──
        ok    = collector.refresh_success_count
        fail  = collector.refresh_fail_count
        total_ref = ok + fail

        ref_val = self._val_lbl(self._refresh_card)
        ref_sub = self._sub_lbl(self._refresh_card)
        if ref_val:
            ref_val.setText(str(ok))
        if ref_sub:
            ref_sub.setText(
                f"{fail} thất bại  •  tổng {total_ref}" if total_ref > 0 else "Chưa có refresh"
            )

        # ── Chart ──
        self._chart.set_data(collector.ping_history)

        # ── Footer ──
        n = len(collector.ping_history)
        self._footer_lbl.setText(
            f"Dữ liệu từ {n} lần ping"
            if n else "Chưa có dữ liệu — hãy Check proxy để bắt đầu"
        )

    # ── Events ────────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._refresh_stats()
        # Center on parent window
        if self.parent():
            p = self.parent()
            self.move(
                p.x() + (p.width()  - self.width())  // 2,
                p.y() + (p.height() - self.height()) // 2,
            )

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
