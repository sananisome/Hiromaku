"""
subtitle_preview.py —— 新界面右侧的「放映区」

上半部分是画面（背景图只放在这里，不再铺满整个窗口），字幕用描边字绘制；
下半部分是类似打轴软件的时间轴：波形 + 原始逐词碎片（陶土色）+ 断句后的字幕块（青色）+ 播放头。

状态：
  empty    还没选文件
  raw      已读到 JSON：按固定时长硬切播放「原始 ASR」
  waiting  云端转录模式，等待转录
  healing  正在转换（显示进度，碎片上有扫描光）
  healed   转换完成：读取导出的 SRT，碎片从左到右「愈合」成整句

点画面：暂停 / 播放；点时间轴：跳转。
"""
from __future__ import annotations

import math
import random
import time
from bisect import bisect_left, bisect_right
from typing import List, Optional

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPainterPath,
                         QPen, QPixmap, QRadialGradient)
from PyQt6.QtWidgets import QSizePolicy, QWidget

from .subtitle_data import Span, build_raw_lines, fmt_short, fmt_tc
from . import theme_modern as theme


def _hash01(i: int) -> float:
    return abs(math.sin(i * 12.9898) * 43758.5453) % 1.0


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class SubtitlePreview(QWidget):
    TL_H = 128      # 时间轴高度
    SPAN = 30.0     # 时间轴可见窗口（秒）

    def __init__(self, fonts: dict, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.fonts = fonts
        self.setMinimumHeight(340)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.words: List[Span] = []
        self.w_starts: List[float] = []
        self.raw: List[Span] = []
        self.r_starts: List[float] = []
        self.cues: List[Span] = []
        self.c_starts: List[float] = []

        self.state = "empty"
        self._idle_state = "empty"
        self.name = ""
        self.progress = 0.0
        self.heal = 0.0
        self.t = 0.0
        self.playing = True
        self.anim = 0.0
        self._cut = 1.0
        self._cur_key = None

        self.backdrop: Optional[QPixmap] = None
        self._screen = QRectF()
        self._tl = QRectF()
        self._tl_map = (0.0, self.SPAN, QRectF())

        rng = random.Random(7)
        self.drops = [(rng.random(), 110 + rng.random() * 170, 18 + rng.random() * 38, rng.random() * 1000)
                      for _ in range(30)]

        self._bg_cache: Optional[QPixmap] = None   # 背景图 + 压暗渐变，只在尺寸/图片变化时重画
        self._frame = 0
        self._last = time.monotonic()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._layout_rects()

    # ------------------------------------------------------------ 对外接口
    def set_backdrop(self, pixmap: Optional[QPixmap]):
        self.backdrop = pixmap if (pixmap is not None and not pixmap.isNull()) else None
        self._rescale()
        self.update()

    def set_empty(self):
        self._reset_data()
        self.name = ""
        self.state = self._idle_state = "empty"

    def set_waiting(self, name: str):
        self._reset_data()
        self.name = name
        self.state = self._idle_state = "waiting"

    def set_words(self, words: List[Span], name: str):
        self._reset_data()
        self.name = name
        self._set_words(words)
        self.state = self._idle_state = "raw" if self.words else "empty"
        self.t = max(0.0, self.words[0].s - 0.3) if self.words else 0.0
        self.playing = True

    def begin_healing(self):
        if self.state in ("empty", "waiting", "raw"):
            self._idle_state = self.state
        self.cues, self.c_starts = [], []
        self.state = "healing"
        self.progress = 0.0
        self.heal = 0.0

    def set_progress(self, value):
        try:
            self.progress = float(value)
        except (TypeError, ValueError):
            pass

    def finish_healing(self, cues: List[Span], words: Optional[List[Span]] = None, name: Optional[str] = None):
        if words:
            self._set_words(words)
        if name:
            self.name = name
        self.cues = list(cues)
        self.c_starts = [c.s for c in self.cues]
        if self.cues:
            self.state = "healed"
            self.heal = 0.0
            self.t = max(0.0, self.cues[0].s - 0.4)
            self.playing = True
        else:
            self.cancel_healing()

    def cancel_healing(self):
        self.state = "raw" if self.words else (self._idle_state if self._idle_state != "healing" else "empty")
        self.progress = 0.0

    # ------------------------------------------------------------ 内部数据
    def _reset_data(self):
        self.words, self.w_starts, self.raw, self.r_starts = [], [], [], []
        self.cues, self.c_starts = [], []
        self.progress = 0.0
        self.heal = 0.0
        self.t = 0.0
        self._cur_key = None

    def _set_words(self, words: List[Span]):
        self.words = list(words)
        self.w_starts = [w.s for w in self.words]
        self.raw = build_raw_lines(self.words)
        self.r_starts = [r.s for r in self.raw]

    @property
    def duration(self) -> float:
        d = 0.0
        if self.words:
            d = max(d, self.words[-1].e)
        if self.cues:
            d = max(d, max(c.e for c in self.cues[-50:]))
        return max(d, 1.0)

    @staticmethod
    def _at(spans: List[Span], starts: List[float], t: float, tail: float = 0.0) -> Optional[Span]:
        i = bisect_right(starts, t) - 1
        if 0 <= i < len(spans) and spans[i].s <= t <= spans[i].e + tail:
            return spans[i]
        return None

    def _covered(self, t: float) -> bool:
        if self.words:
            return self._at(self.words, self.w_starts, t, 0.05) is not None
        if self.cues:
            return self._at(self.cues, self.c_starts, t) is not None
        return False

    # ------------------------------------------------------------ 动画
    def _tick(self):
        now = time.monotonic()
        dt = min(0.1, now - self._last)
        self._last = now
        win = self.window()
        if not self.isVisible() or (win is not None and win.isMinimized()):
            return
        self._frame += 1
        has_data = bool(self.words or self.cues)
        active = (has_data and self.playing and self.state in ("raw", "healing", "healed")) \
            or self.state == "healing" or (self.state == "healed" and self.heal < 1.0) or self._cut < 1.0
        if not active and self._frame % 2:
            return          # 空闲时只剩细雨，降到约 15fps；跳过的那帧用 dt×2 补上
        dt = min(0.15, dt if active else dt * 2)
        self.anim += dt
        if self.playing and has_data and self.state in ("raw", "healing", "healed"):
            self.t += dt
            if self.t > self.duration + 1.0:
                first = self.cues[0].s if (self.state == "healed" and self.cues) else (self.words[0].s if self.words else 0.0)
                self.t = max(0.0, first - 0.4)
        if self.state == "healed" and self.heal < 1.0:
            self.heal = min(1.0, self.heal + dt / 1.6)
        self._cut = min(1.0, self._cut + dt / 0.09)
        self.update()

    # ------------------------------------------------------------ 事件
    def resizeEvent(self, e):
        self._layout_rects()
        self._rescale()
        super().resizeEvent(e)

    def showEvent(self, e):
        self._last = time.monotonic()
        self._timer.start(33)
        super().showEvent(e)

    def hideEvent(self, e):
        self._timer.stop()
        super().hideEvent(e)

    def _layout_rects(self):
        r = QRectF(self.rect())
        self._screen = QRectF(r.x(), r.y(), r.width(), max(0.0, r.height() - self.TL_H))
        self._tl = QRectF(r.x(), self._screen.bottom(), r.width(), self.TL_H)

    def mousePressEvent(self, e):
        pos = e.position()
        if self._tl.contains(pos) and (self.words or self.cues):
            ws, span, inner = self._tl_map
            if inner.width() > 0:
                self.t = _clamp(ws + (pos.x() - inner.left()) / inner.width() * span, 0.0, self.duration)
                self._cur_key = None
        elif self._screen.contains(pos):
            self.playing = not self.playing
        e.accept()
        self.update()

    def _rescale(self):
        """重建静态背景层：缩放裁切背景图 + 压暗渐变（无图时用深青径向渐变）。"""
        dpr = self.devicePixelRatioF() or 1.0
        lw, lh = max(1, self.width()), max(1, self.height() - self.TL_H)
        cache = QPixmap(int(lw * dpr), int(lh * dpr))
        cache.setDevicePixelRatio(dpr)
        cache.fill(QColor("#031819"))
        p = QPainter(cache)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        sc = QRectF(0, 0, lw, lh)
        if self.backdrop is not None:
            w, h = int(lw * dpr), int(lh * dpr)
            pm = self.backdrop.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                      Qt.TransformationMode.SmoothTransformation)
            x = max(0, (pm.width() - w) // 2)
            y = max(0, (pm.height() - h) // 3)   # 稍微偏上裁切，人物脸一般在上方
            pm = pm.copy(x, y, w, h)
            pm.setDevicePixelRatio(dpr)
            p.drawPixmap(QPointF(0, 0), pm)
            g = QLinearGradient(sc.topLeft(), sc.bottomLeft())
            g.setColorAt(0.0, QColor(3, 24, 25, 120))
            g.setColorAt(0.55, QColor(3, 24, 25, 150))
            g.setColorAt(1.0, QColor(3, 24, 25, 225))
            p.fillRect(sc, QBrush(g))
        else:
            g = QRadialGradient(QPointF(lw * 0.3, lh * 0.2), lw * 0.9)
            g.setColorAt(0.0, QColor("#0f4a4c"))
            g.setColorAt(0.55, QColor("#062a2b"))
            g.setColorAt(1.0, QColor("#031819"))
            p.fillRect(sc, QBrush(g))
        p.end()
        self._bg_cache = cache

    # ------------------------------------------------------------ 绘制
    def _font(self, key: str, px: int, weight=QFont.Weight.Normal) -> QFont:
        f = QFont(self.fonts.get(key, self.fonts.get("ui", "")))
        f.setPixelSize(px)
        f.setWeight(weight)
        return f

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        r = QRectF(self.rect())
        clip = QPainterPath()
        clip.addRoundedRect(r, 16, 16)
        p.setClipPath(clip)
        self._layout_rects()
        self._paint_screen(p, self._screen)
        self._paint_timeline(p, self._tl)
        p.end()

    def _paint_screen(self, p: QPainter, sc: QRectF):
        # 背景（静态层缓存，每帧只贴图）
        if self._bg_cache is None:
            self._rescale()
        p.drawPixmap(sc.topLeft(), self._bg_cache)

        # 环境动效：细雨
        p.setPen(QPen(QBrush(QColor(190, 230, 231, 34)), 1.0))
        span_h = sc.height()
        for fx, speed, ln, ph in self.drops:
            x = sc.left() + fx * sc.width()
            y = sc.top() + ((ph + self.anim * speed) % (span_h + ln)) - ln
            p.drawLine(QPointF(x, y), QPointF(x, y + ln))

        # 顶栏：文件名 + 状态 + 时间码
        pad = 20.0
        f_name = self._font("ui", 14)
        fm = QFontMetricsF(f_name)
        y0 = sc.top() + 16
        x = sc.left() + pad
        if self.name:
            name = fm.elidedText(self.name, Qt.TextElideMode.ElideMiddle, sc.width() * 0.45)
            p.setFont(f_name)
            p.setPen(QColor("#cfe6e6"))
            p.drawText(QRectF(x, y0, fm.horizontalAdvance(name) + 2, 24),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, name)
            x += fm.horizontalAdvance(name) + 12
        chip = {
            "raw": ("原始 ASR", QColor(195, 137, 97, 60), QColor("#f0cfb4")),
            "waiting": ("等待转录", QColor(255, 255, 255, 28), QColor("#cfe6e6")),
            "healing": (f"治疗中 {int(self.progress)}%", QColor(0, 125, 130, 150), QColor("#ffffff")),
            "healed": ("治疗后", QColor(theme.TEAL), QColor("#ffffff")),
        }.get(self.state)
        if chip:
            f_chip = self._font("ui", 13, QFont.Weight.DemiBold)
            cw = QFontMetricsF(f_chip).horizontalAdvance(chip[0]) + 16
            cr = QRectF(x, y0, cw, 24)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(chip[1]))
            p.drawRoundedRect(cr, 6, 6)
            p.setFont(f_chip)
            p.setPen(chip[2])
            p.drawText(cr, Qt.AlignmentFlag.AlignCenter, chip[0])
        if self.words or self.cues:
            f_tc = self._font("mono", 14)
            p.setFont(f_tc)
            p.setPen(QColor("#cfe6e6"))
            label = fmt_tc(self.t) + ("" if self.playing else "  ❚❚")
            p.drawText(QRectF(sc.right() - pad - 260, y0, 260, 24),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, label)

        # 中央提示（没有可播放内容时）
        if not (self.words or self.cues):
            big, small = {
                "empty": ("拖进来", "JSON 或音视频，松手就能预览断句效果"),
                "waiting": ("待转录", "云端转录完成后，这里会按句播放字幕"),
                "healing": (f"{int(self.progress)}%", "正在转录 / 断句…"),
            }.get(self.state, ("", ""))
            if big:
                f_big = self._font("serif", 52, QFont.Weight.Black)
                f_small = self._font("ui", 15)
                cy = sc.center().y()
                p.setFont(f_big)
                p.setPen(QColor(255, 255, 255, 235))
                p.drawText(QRectF(sc.left(), cy - 56, sc.width(), 66), Qt.AlignmentFlag.AlignCenter, big)
                p.setFont(f_small)
                p.setPen(QColor("#a9d3d4"))
                p.drawText(QRectF(sc.left(), cy + 16, sc.width(), 26), Qt.AlignmentFlag.AlignCenter, small)
            return

        # 字幕
        if self.state == "healed":
            span = self._at(self.cues, self.c_starts, self.t)
            fill = QColor("#ffffff")
        else:
            span = self._at(self.raw, self.r_starts, self.t, 0.3)
            fill = QColor("#f3dcc9")
            ph = (self.anim % 1.7) / 1.7
            if 0.92 < ph < 0.95:          # 原始碎片的「卡顿闪烁」
                fill.setAlpha(60)
        key = (self.state, span.s if span else None)
        if key != self._cur_key:
            self._cur_key = key
            self._cut = 0.0 if self.state == "healed" else 1.0
        if span is None:
            return
        px = int(_clamp(sc.height() * 0.075, 22, 36))
        font = self._font("jp", px, QFont.Weight.Bold)
        self._draw_subtitle(p, sc, span.text, font, fill)

    def _wrap(self, text: str, fm: QFontMetricsF, maxw: float) -> List[str]:
        out: List[str] = []
        for para in text.split("\n"):
            if fm.horizontalAdvance(para) <= maxw:
                out.append(para)
                continue
            line = ""
            tokens = para.split(" ") if " " in para else list(para)
            sep = " " if " " in para else ""
            for tok in tokens:
                cand = (line + sep + tok) if line else tok
                if fm.horizontalAdvance(cand) > maxw and line:
                    out.append(line)
                    line = tok
                else:
                    line = cand
            if line:
                out.append(line)
        return out[:3]

    def _draw_subtitle(self, p: QPainter, sc: QRectF, text: str, font: QFont, fill: QColor):
        fm = QFontMetricsF(font)
        lines = self._wrap(text, fm, sc.width() - 96)
        lh = fm.height()
        gap = 4.0
        total = len(lines) * lh + (len(lines) - 1) * gap
        top = sc.bottom() - 34 - total
        path = QPainterPath()
        y = top + fm.ascent()
        for ln in lines:
            w = fm.horizontalAdvance(ln)
            path.addText(QPointF(sc.center().x() - w / 2, y), font, ln)
            y += lh + gap
        p.save()
        if self._cut < 1.0:  # 硬切入场：三帧从上往下露出
            frac = math.ceil(self._cut * 3) / 3.0
            p.setClipRect(QRectF(sc.left(), top - 8, sc.width(), (total + 16) * frac),
                          Qt.ClipOperation.IntersectClip)
        stroke = QColor("#031a1b")
        if fill.alpha() < 255:
            stroke.setAlpha(fill.alpha())
        p.setPen(QPen(QBrush(stroke), 6.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(fill))
        p.drawPath(path)
        p.restore()

    def _paint_timeline(self, p: QPainter, tl: QRectF):
        p.fillRect(tl, QColor("#062223"))
        pad = 20.0
        inner = QRectF(tl.left() + pad, tl.top() + 10, tl.width() - 2 * pad, tl.height() - 22)
        dur = self.duration
        span = min(self.SPAN, max(dur, 4.0))
        ws = self.t - span * 0.3
        ws = _clamp(ws, 0.0, max(0.0, dur - span))
        self._tl_map = (ws, span, inner)
        if inner.width() <= 0:
            return

        def x_of(s: float) -> float:
            return inner.left() + (s - ws) / span * inner.width()

        # 刻度
        step = 5 if span > 12 else 1
        p.setFont(self._font("mono", 12))
        s = math.ceil(ws / step) * step
        while s <= ws + span + 1e-6:
            x = x_of(s)
            p.fillRect(QRectF(x, inner.top(), 1, 14), QColor(255, 255, 255, 28))
            p.setPen(QColor("#b2dbdc"))
            p.drawText(QPointF(x + 4, inner.top() + 11), fmt_short(s))
            s += step

        has = bool(self.words or self.cues)
        # 波形（根据逐词覆盖生成，不读音频）
        wave = QRectF(inner.left(), inner.top() + 20, inner.width(), 40)
        n = max(1, int(wave.width() / 5))
        dtb = span / n
        k0 = int(math.floor(ws / dtb))
        p.setPen(Qt.PenStyle.NoPen)
        for k in range(k0, k0 + n + 2):
            tb = (k + 0.5) * dtb
            x = x_of(k * dtb)
            if x < wave.left() - 3 or x > wave.right():
                continue
            nz = _hash01(k)
            cov = self._covered(tb) if has else False
            h = (0.30 + 0.65 * nz) if cov else (0.05 + 0.07 * nz)
            h *= 0.86 + 0.14 * math.sin(self.anim * 2.1 + k * 0.7)
            bh = max(2.0, h * wave.height())
            p.setBrush(QBrush(QColor("#2f8f93") if tb < self.t else QColor("#1c4e50")))
            p.drawRoundedRect(QRectF(x, wave.center().y() - bh / 2, 3, bh), 1.5, 1.5)

        row = QRectF(inner.left(), wave.bottom() + 8, inner.width(), 28)
        front = inner.left() + self.heal * inner.width() * 1.15 if self.state == "healed" else -1e9
        scan = inner.left() + ((self.anim * 0.45) % 1.0) * inner.width() if self.state == "healing" else None

        # 原始碎片（陶土色）
        if self.words:
            i0 = max(0, bisect_left(self.w_starts, ws - 10))
            i1 = bisect_right(self.w_starts, ws + span)
            for w in self.words[i0:i1]:
                x1, x2 = x_of(w.s), x_of(w.e)
                if x2 < inner.left() or x1 > inner.right():
                    continue
                f = _clamp((front - x2) / 40.0, 0.0, 1.0)
                if f >= 1.0:
                    continue
                c = QColor(theme.CLAY)
                if scan is not None and abs((x1 + x2) / 2 - scan) < 60:
                    c = QColor("#e6b38f")
                c.setAlpha(int(215 * (1 - f)))
                hh = 12 * (1 - 0.7 * f)
                p.setBrush(QBrush(c))
                p.drawRoundedRect(QRectF(x1, row.center().y() - hh / 2, max(1.5, x2 - x1 - 1), hh), 3, 3)

        # 断句后的字幕块（青色）
        if self.state == "healed" and self.cues:
            j0 = max(0, bisect_left(self.c_starts, ws - 30))
            j1 = bisect_right(self.c_starts, ws + span)
            f_blk = self._font("jp", 12, QFont.Weight.Medium)
            p.setFont(f_blk)
            for c in self.cues[j0:j1]:
                x1, x2 = x_of(c.s), x_of(c.e)
                if x2 < inner.left() or x1 > inner.right():
                    continue
                a = _clamp((front - x1) / 60.0, 0.0, 1.0)
                if a <= 0:
                    continue
                active = c.s <= self.t <= c.e
                rr = QRectF(x1, row.top(), max(3.0, (x2 - x1) * (0.6 + 0.4 * a)), row.height())
                col = QColor("#00a3a9" if active else theme.TEAL)
                col.setAlpha(int(255 * a))
                p.setPen(QPen(QBrush(QColor(127, 211, 214, int(255 * a))), 2.0) if active else Qt.PenStyle.NoPen)
                p.setBrush(QBrush(col))
                p.drawRoundedRect(rr, 6, 6)
                if rr.width() > 24:
                    p.save()
                    p.setClipRect(rr.adjusted(8, 0, -6, 0))
                    p.setPen(QColor(255, 255, 255, int(255 * a)))
                    p.drawText(rr.adjusted(8, 0, 0, 0),
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                               c.text.replace("\n", " "))
                    p.restore()
            p.setPen(Qt.PenStyle.NoPen)

        # 播放头
        if has:
            x = x_of(self.t)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(theme.EMBER)))
            p.drawRoundedRect(QRectF(x - 1, inner.top() + 16, 2, row.bottom() - inner.top() - 16), 1, 1)
            p.drawEllipse(QPointF(x, inner.top() + 16), 5, 5)
