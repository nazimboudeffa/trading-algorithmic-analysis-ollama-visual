"""
Widget Qt de graphique de chandeliers dessine a la main (QPainter).

Vue : bougies OHLC, EMAs, supports/resistances, order blocks, FVG,
patterns candlestick, prix actuel et lignes Entree/SL/TP.
Interaction : zoom molette, pan drag, crosshair + info OHLC au survol.
"""
import math

import numpy as np
import pandas as pd
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPolygonF
from PySide6.QtWidgets import QWidget


COL_BG = QColor(13, 17, 23)
COL_GRID_LIGHT = QColor(32, 38, 50)
COL_GRID = QColor(24, 29, 40)
COL_TEXT = QColor(222, 228, 240)
COL_MUTED = QColor(140, 150, 170)
COL_UP = QColor(38, 166, 91)
COL_DOWN = QColor(239, 83, 80)
COL_LAST = QColor(233, 30, 99)
COL_ENTRY = QColor(66, 165, 245)
COL_SL = QColor(239, 83, 80)
COL_TP = QColor(102, 187, 106)

EMA_COLORS = {20: QColor(66, 165, 245), 50: QColor(255, 167, 38),
              100: QColor(102, 187, 106), 200: QColor(171, 71, 188)}
STRENGTH_COLORS = {"Strong": (70, 220, 130), "Medium": (250, 200, 80),
                   "Weak": (255, 120, 80), None: (160, 170, 190)}


class CandleChart(QWidget):
    infoChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 350)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self.result = None
        self.tf = "M15"
        self.bars_visible = 150
        self.offset = 0
        self._drag = None
        self.hover = None

        self._series = None
        self._dates = None
        self._ema = {}
        self._levels = []
        self._patterns = []
        self._zone_ob_bull = []
        self._zone_ob_bear = []
        self._zone_fvg_bull = None
        self._zone_fvg_bear = None
        self._signal_lines = []

    # ------------------------------------------------------------------ API
    def set_result(self, result):
        self.result = result
        self.tf = "M15"
        self.offset = 0
        self._build_series()
        self.repaint()

    def set_tf(self, tf):
        if tf not in (self.result or {}).get("data", {}):
            return
        self.tf = tf
        self.offset = 0
        self._build_series()
        self.repaint()

    def clear(self):
        self.result = None
        self._series = None
        self.repaint()

    # ------------------------------------------------------------- internals
    def _build_series(self):
        if not self.result:
            return
        df = self.result["data"][self.tf]
        ind = self.result["indicators"][self.tf]
        n = len(df)
        self._series = {
            "open": df["Open"].to_numpy(dtype=float),
            "high": df["High"].to_numpy(dtype=float),
            "low": df["Low"].to_numpy(dtype=float),
            "close": df["Close"].to_numpy(dtype=float),
        }
        idx = df.index.tolist() if isinstance(df.index, pd.DatetimeIndex) else list(range(n))
        self._dates = list(df.index)
        self._ema = {w: ind[f"ema{w}"].to_numpy(dtype=float) for w in (20, 50, 100, 200)}
        self._levels = list(self.result["levels"].get(self.tf, []))
        zones = self.result.get("zones", {}).get(self.tf, {})
        self._zone_ob_bull = zones.get("bullish_ob", [])
        self._zone_ob_bear = zones.get("bearish_ob", [])
        self._zone_fvg_bull = zones.get("fvg_bullish")
        self._zone_fvg_bear = zones.get("fvg_bearish")
        self._patterns = self.result["patterns"] if self.tf == "M15" else []

        self._signal_lines = []
        if self.result["entry"] is not None:
            self._signal_lines.append(("Entrée", self.result["entry"], COL_ENTRY, Qt.DashLine))
            self._signal_lines.append(("SL", self.result["stop_loss"], COL_SL, Qt.DashLine))
            self._signal_lines.append(("TP", self.result["take_profit"], COL_TP, Qt.DashLine))

        price = self.result["price"]
        self._signal_lines.append(("Prix", price, COL_LAST, Qt.DotLine))

        if self.bars_visible > n:
            self.bars_visible = max(30, n)
        self._clamp_offset()

    def _clamp_offset(self):
        n = len(self._series["high"]) if self._series else 0
        if n == 0:
            return
        self.bars_visible = min(self.bars_visible, n)
        max_off = max(0, n - self.bars_visible)
        self.offset = max(0, min(self.offset, max_off))

    def _view(self):
        n = len(self._series["high"])
        if n == 0:
            return 0, 0, 0
        start = max(0, n - self.bars_visible - self.offset)
        end = min(n, start + self.bars_visible)
        return start, end, n

    def _geometry(self):
        left, top = 12, 10
        right, bottom = 58, 26
        gw = max(1, self.width() - left - right)
        gh = max(1, self.height() - top - bottom)
        return left, top, right, bottom, gw, gh

    # ---------------------------------------------------------------- painting
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), COL_BG)

        if not self._series or self.result is None:
            p.setPen(COL_MUTED)
            p.drawText(self.rect(), Qt.AlignCenter, "Analysez une paire pour afficher le graphique.")
            return

        start, end, n = self._view()
        if start >= end:
            return
        left, top, right, bottom, gw, gh = self._geometry()
        plot = (left, top, gw, gh)

        high = self._series["high"][start:end]
        low = self._series["low"][start:end]
        pmin = float(np.min(low))
        pmax = float(np.max(high))

        for v in list(self._ema.values()):
            seg = v[start:end]
            seg = seg[np.isfinite(seg)]
            if len(seg):
                pmin = min(pmin, float(seg.min()))
                pmax = max(pmax, float(seg.max()))
        for lvl in self._levels:
            pmin = min(pmin, lvl["level"])
            pmax = max(pmax, lvl["level"])
        for v in list(self._zone_ob_bull) + list(self._zone_ob_bear):
            pmin = min(pmin, v)
            pmax = max(pmax, v)
        for zv in (self._zone_fvg_bull, self._zone_fvg_bear):
            if zv:
                pmin = min(pmin, zv[0])
                pmax = max(pmax, zv[1])
        for _name, val, _c, _s in self._signal_lines:
            pmin = min(pmin, val)
            pmax = max(pmax, val)

        pad = max(0.0005, (pmax - pmin) * 0.08)
        pmin, pmax = pmin - pad, pmax + pad

        cw = gw / self.bars_visible

        def x_of(i):
            return left + (i - start + 0.5) * cw

        def y_of(pr):
            return top + gh - (pr - pmin) / (pmax - pmin) * gh

        self._draw_grid(p, plot, start, end, pmin, pmax, cw, x_of)
        self._draw_zones(p, x_of, y_of)
        self._draw_candles(p, start, end, x_of, y_of, cw)
        self._draw_ema(p, start, end, x_of, y_of)
        self._draw_levels(p, x_of, y_of)
        self._draw_patterns(p, start, end, x_of, y_of, cw)
        self._draw_signal_lines(p, x_of, y_of)
        self._draw_axis(p, start, end, pmin, pmax, left, top, cw, x_of, y_of)
        if self.hover is not None:
            self._draw_crosshair(p, start, end, pmin, pmax, cw, x_of, y_of, left, top, gh)
        p.end()

    def _draw_grid(self, p, plot, start, end, pmin, pmax, cw, x_of):
        left, top, gw, gh = plot
        p.setPen(QPen(COL_GRID, 1))
        # horizontales
        steps = 8
        for k in range(steps + 1):
            y = int(top + gh * k / steps)
            p.drawLine(left, y, left + gw, y)
        # verticales
        vstep = max(1, self.bars_visible // 8)
        for i in range(start, end, vstep):
            x = int(x_of(i))
            p.drawLine(x, top, x, top + gh)

    def _draw_zones(self, p, x_of, y_of):
        left, top, right, bottom, gw, gh = self._geometry()
        for zv, color in ((self._zone_fvg_bull, COL_UP), (self._zone_fvg_bear, COL_DOWN)):
            if zv:
                y1, y2 = y_of(zv[1]), y_of(zv[0])
                brush = QBrush(color)
                brush.setStyle(Qt.BDiagPattern)
                p.setBrush(brush)
                p.setPen(Qt.NoPen)
                p.drawRect(int(x_of(0)), int(y1), int(gw), max(2, int(y2 - y1)))
        for zone in (self._zone_ob_bull, self._zone_ob_bear):
            color = COL_UP if zone is self._zone_ob_bull else COL_DOWN
            for lvl in zone:
                c = QColor(color)
                c.setAlpha(70)
                p.setBrush(c)
                p.setPen(Qt.NoPen)
                yp = y_of(lvl)
                half_h = 6.0
                p.drawRect(int(x_of(0)), int(yp - half_h), int(gw), int(2 * half_h))

    def _draw_candles(self, p, start, end, x_of, y_of, cw):
        body_w = max(1.0, cw * 0.72)
        for i in range(start, end):
            o, c = self._series["open"][i], self._series["close"][i]
            h, l = self._series["high"][i], self._series["low"][i]
            up = c >= o
            color = COL_UP if up else COL_DOWN
            pen = QPen(color, 1)
            p.setPen(pen)
            x = x_of(i)
            p.drawLine(int(x), int(y_of(h)), int(x), int(y_of(l)))
            y_top = y_of(max(o, c))
            y_bot = y_of(min(o, c))
            hgt = max(1.0, y_bot - y_top)
            p.setBrush(color if not up else QBrush(color))
            p.setBrush(QBrush(color))
            p.drawRect(int(x - body_w / 2), int(y_top), int(body_w), int(hgt))

    def _draw_ema(self, p, start, end, x_of, y_of):
        for w in (20, 50, 100, 200):
            arr = self._ema[w]
            pts = [QPointF(x_of(i), y_of(arr[i])) for i in range(start, end)
                   if i < len(arr) and np.isfinite(arr[i])]
            if len(pts) > 1:
                pen = QPen(EMA_COLORS[w], 1.2)
                p.setPen(pen)
                for a, b in zip(pts, pts[1:]):
                    p.drawLine(a, b)

    def _draw_levels(self, p, x_of, y_of):
        left, _t, _r, _b, gw, _h = self._geometry()
        p.setFont(QFont("Segoe UI", 8))
        for lvl in self._levels[:6]:
            is_s = lvl["type"] == "Support"
            color = QColor(38, 166, 154) if is_s else QColor(239, 83, 80)
            sc, gc, bc = STRENGTH_COLORS[lvl["strength"]]
            pen = QPen(color, 1 if lvl["strength"] != "Strong" else 2, Qt.DashLine)
            p.setPen(pen)
            y = int(y_of(lvl["level"]))
            p.drawLine(int(x_of(0) - 2), y, int(x_of(0) - 2) + gw + 2, y)
            label = f"{lvl['type'][0]} {lvl['level']:.5f}"
            bg = QColor(sc, gc, bc)
            bg.setAlpha(180)
            p.setBrush(bg)
            p.setPen(Qt.NoPen)
            tw = p.fontMetrics().horizontalAdvance(label) + 6
            p.drawRoundedRect(int(x_of(0)), y - 8, tw, 16, 3, 3)
            p.setPen(QColor(10, 12, 16))
            p.drawText(int(x_of(0)) + 3, y + 4, label)

    def _draw_patterns(self, p, start, end, x_of, y_of, cw):
        if not self._patterns:
            return
        p.setFont(QFont("Segoe UI", 7))
        n = len(self._series["high"])
        grouped = {}
        for pat in self._patterns:
            i = n + pat["candle"]
            if not (start <= i < end):
                continue
            grouped.setdefault(i, []).append(pat)

        for i, pats in grouped.items():
            hi = self._series["high"][i]
            lo = self._series["low"][i]
            ups = [p_ for p_ in pats if p_["signal"].lower().startswith("bull")]
            downs = [p_ for p_ in pats if p_["signal"].lower().startswith("bear")]
            neut = [p_ for p_ in pats if not (
                p_["signal"].lower().startswith("bull") or p_["signal"].lower().startswith("bear"))]
            y = y_of(hi) - 6
            for p_ in ups + neut:
                color = COL_UP if "bull" in p_["signal"].lower() else COL_MUTED
                txt = f"▲ {p_['pattern']}" if "bull" in p_["signal"].lower() else f"◆ {p_['pattern']}"
                p.setPen(color)
                p.drawText(QPointF(x_of(i) - 20, y), txt)
                y -= 12
            y = y_of(lo) + 14
            for p_ in downs:
                p.setPen(COL_DOWN)
                p.drawText(QPointF(x_of(i) - 20, y), f"▼ {p_['pattern']}")
                y += 12

    def _draw_signal_lines(self, p, x_of, y_of):
        left, _t, _r, _b, gw, _h = self._geometry()
        p.setFont(QFont("Segoe UI", 8))
        for name, val, color, style in self._signal_lines:
            p.setPen(QPen(color, 1, style))
            y = int(y_of(val))
            p.drawLine(int(x_of(0)), y, int(x_of(0)) + gw, y)
            label = f"{name} {val:.5f}"
            bg = QColor(color)
            bg.setAlpha(150)
            p.setBrush(bg)
            p.setPen(Qt.NoPen)
            tw = p.fontMetrics().horizontalAdvance(label) + 6
            p.drawRoundedRect(int(x_of(0)), y - 8, tw, 16, 3, 3)
            p.setPen(QColor(10, 12, 16))
            p.drawText(int(x_of(0)) + 3, y + 4, label)

    def _draw_axis(self, p, start, end, pmin, pmax, left, top, cw, x_of, y_of):
        _l, _t, right, bottom, gw, gh = self._geometry()
        p.setFont(QFont("Segoe UI", 8))
        # prix
        steps = 6
        for k in range(steps + 1):
            price = pmin + (pmax - pmin) * k / steps
            y = top + gh - gh * k / steps
            p.setPen(COL_MUTED)
            p.drawText(int(left + gw + 6), int(y + 3), f"{price:.5f}")
        # temps
        p.setPen(COL_MUTED)
        vstep = max(1, self.bars_visible // 8)
        n = len(self._dates)
        for i in range(start, end, vstep):
            if 0 <= i < n:
                d = self._dates[i]
                if isinstance(d, pd.Timestamp):
                    if self.tf in ("M15", "H1"):
                        txt = d.strftime("%m-%d %H:%M")
                    else:
                        txt = d.strftime("%Y-%m-%d")
                else:
                    txt = str(d)
                p.drawText(int(x_of(i) - 25), top + gh + 15, f"{txt}")

    def _draw_crosshair(self, p, start, end, pmin, pmax, cw, x_of, y_of, left, top, gh):
        mx, my = self.hover
        left0, _t, right, bottom, gw, _h = self._geometry()
        i = int((mx - left0) / cw) + start
        price = pmax - (my - top) / gh * (pmax - pmin)
        p.setPen(QPen(QColor(200, 205, 220), 0.6, Qt.DashLine))
        if left0 <= mx <= left0 + gw:
            p.drawLine(int(mx), top, int(mx), top + gh)
        if top <= my <= top + gh:
            p.drawLine(left0, int(my), left0 + gw, int(my))
        if 0 <= i < end and left0 <= mx <= left0 + gw:
            s = self._series
            o, c, h, l = s["open"][i], s["close"][i], s["high"][i], s["low"][i]
            d = self._dates[i] if i < len(self._dates) else None
            txt = f"O:{o:.5f}  H:{h:.5f}  L:{l:.5f}  C:{c:.5f}"
            if isinstance(d, pd.Timestamp):
                txt += f"   {d.strftime('%Y-%m-%d %H:%M')}"
            w = p.fontMetrics().horizontalAdvance(txt) + 14
            p.setBrush(QColor(24, 29, 40, 230))
            p.setPen(QPen(COL_MUTED, 1))
            p.drawRoundedRect(6, 6, w, 20, 4, 4)
            p.setPen(COL_TEXT)
            p.drawText(13, 20, txt)

    # ----------------------------------------------------------- interactions
    def wheelEvent(self, event):
        if not self._series:
            return
        n = len(self._series["high"])
        old_bv = self.bars_visible
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        new_bv = int(max(20, min(n, old_bv * factor)))
        if new_bv == old_bv:
            return
        left, top, right, bottom, gw, gh = self._geometry()
        if event.position().x() >= left:
            frac = max(0.0, min(1.0, (event.position().x() - left) / gw))
        else:
            frac = 0.5
        start, _e, _nn = self._view()
        anchor = start + int(frac * (old_bv - 1))
        self.bars_visible = new_bv
        new_start = anchor - int(frac * (new_bv - 1))
        self.offset = max(0, min(max(0, n - new_bv), n - new_bv - new_start))
        self.repaint()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._series:
            left, top, right, bottom, gw, gh = self._geometry()
            if left <= event.position().x() <= left + gw:
                self._drag = (event.position().x(), self.offset)
            else:
                self._drag = None
        elif event.button() == Qt.RightButton:
            self.offset = 0
            self.bars_visible = min(self.bars_visible, 60)
            self.repaint()

    def mouseMoveEvent(self, event):
        self.hover = (event.position().x(), event.position().y())
        if self._drag and self._series:
            left, top, right, bottom, gw, gh = self._geometry()
            x0, off0 = self._drag
            n = len(self._series["high"])
            cw = gw / self.bars_visible
            dx = event.position().x() - x0
            self.offset = int(max(0, min(max(0, n - self.bars_visible), off0 - dx / cw)))
        self.repaint()

    def mouseReleaseEvent(self, event):
        self._drag = None
        self.repaint()

    def leaveEvent(self, event):
        self.hover = None
        self.repaint()