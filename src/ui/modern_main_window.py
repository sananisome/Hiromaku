"""
modern_main_window.py —— 治幕主窗口新界面（换皮层）

做法：继承原来的 HealJimakuApp，让它照常执行 init_ui() 把所有控件、信号、下拉选项都建好，
然后把这些「原装控件」挪进新布局、换上新样式。所有业务逻辑（配置读写、转换、云端转录、
LLM 档案、拖拽、批量）都还是原来那 3700 行代码在跑，新界面只负责「长什么样」。

启用：src/main.py 里把
    from ui.main_window import HealJimakuApp
换成
    from ui.modern_main_window import ModernHealJimakuApp as HealJimakuApp
想临时切回旧界面：设置环境变量 HEAL_JIMAKU_LEGACY_UI=1（见 README）。
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from typing import Any, List, Optional

from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QRectF, QSize
from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (QApplication, QBoxLayout, QButtonGroup, QFrame, QGridLayout, QHBoxLayout,
                             QLabel, QLayout, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from .main_window import HealJimakuApp
from . import theme_modern as theme
from .subtitle_data import load_srt, load_words_from_json, sniff_json_source
from .subtitle_preview import SubtitlePreview

try:
    import config as app_config
except Exception:  # pragma: no cover
    app_config = None


# GBK 控制台下 print 含 ℹ ✕ › 之类字符会抛 UnicodeEncodeError；在 PyQt6 槽函数里抛出会直接 abort。
# 打包成无控制台的 exe 时 stdout 可能是 None，所以逐个判断。
for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream is not None and hasattr(_stream, "reconfigure"):
            _stream.reconfigure(errors="replace")
    except Exception:
        pass


def _safe_print(*parts):
    try:
        print(*parts)
    except Exception:
        try:
            text = " ".join(str(x) for x in parts)
            sys.stderr.write(text.encode("ascii", "replace").decode("ascii") + "\n")
        except Exception:
            pass


def _safe_print_exc():
    _safe_print(traceback.format_exc())


def _cfg(name: str, default: Any = None) -> Any:
    return getattr(app_config, name, default) if app_config is not None else default


def _repolish(w: QWidget):
    st = w.style()
    st.unpolish(w)
    st.polish(w)
    w.update()


# ---------------------------------------------------------------- 流式布局（格式标签换行排）
class FlowLayout(QLayout):
    def __init__(self, parent: Optional[QWidget] = None, hspacing: int = 8, vspacing: int = 8):
        super().__init__(parent)
        self._items = []
        self._h, self._v = hspacing, vspacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._layout(rect, False)

    def sizeHint(self):
        w = self.geometry().width() or 336
        return QSize(w, self.heightForWidth(w))

    def minimumSize(self):
        s = QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        return s

    def _layout(self, rect: QRect, test: bool) -> int:
        x, y, line_h = rect.x(), rect.y(), 0
        for it in self._items:
            sz = it.sizeHint()
            if x + sz.width() > rect.right() + 1 and line_h > 0:
                x = rect.x()
                y += line_h + self._v
                line_h = 0
            if not test:
                it.setGeometry(QRect(QPoint(x, y), sz))
            x += sz.width() + self._h
            line_h = max(line_h, sz.height())
        return y + line_h - rect.y()


# ---------------------------------------------------------------- 主窗口
class ModernHealJimakuApp(HealJimakuApp):
    SIDEBAR_W = 384
    HEADER_H = 48
    EDGE = 6  # 留给无边框窗口拖拽缩放的边

    # ============================================================ 构建
    def init_ui(self):
        super().init_ui()
        self._hj_modern = False
        self._hj_snap: List[dict] = []
        self._hj_tracked: List[QWidget] = []
        self._hj_root: Optional[QWidget] = None
        try:
            self._hj_build()
            self._hj_modern = True
        except Exception:
            _safe_print_exc()
            _safe_print("[治幕新界面] 构建失败，已恢复旧界面")
            self._hj_restore_legacy()
            return
        self._hj_snap = []          # 快照只给失败回退用，成功后就不再持有旧图标/样式/布局引用
        self._hj_install_dialog_theme()
        self._hj_preview_key = None
        self._hj_t0 = 0.0
        self._hj_label_colors = {}
        self._hj_seen_errors = set()
        self._hj_timer = QTimer(self)
        self._hj_timer.timeout.connect(self._hj_sync)
        self._hj_timer.start(250)
        QTimer.singleShot(0, self._hj_sync)

    def _hj_install_dialog_theme(self):
        """新界面构建成功后，把其它窗口（各设置对话框、弹窗、拖拽遮罩）也换成新主题。

        对话框都是每次打开时现建的，并在运行时读 ui.theme，所以这里改完之后打开的窗口就是新皮。
        主窗口自己的旧样式表会层叠到它弹出的 QMessageBox 上，所以顺手用新主题重新生成一次。"""
        try:
            from . import theme as legacy_theme
            theme.install_into_legacy_theme(legacy_theme)
            apply = getattr(self, "apply_styles", None)
            if callable(apply):
                apply()
        except Exception:
            _safe_print_exc()
            _safe_print("[治幕新界面] 对话框换皮失败，对话框继续使用原主题")

    def _hj_on(self) -> bool:
        return bool(getattr(self, "_hj_modern", False))

    def _hj_build(self):
        required = ["api_key_entry", "json_path_entry", "json_browse_button", "json_format_combo",
                    "output_path_entry", "output_browse_button", "progress_bar", "start_button",
                    "log_area", "free_transcription_button"]
        missing = [n for n in required if getattr(self, n, None) is None]
        if missing:
            raise RuntimeError(f"旧界面缺少控件: {missing}")

        self._hj_fonts = theme.resolve_fonts()
        assets = theme.ensure_assets()
        legacy = self.centralWidget()
        min_btn = legacy.findChild(QPushButton, "minButton") if legacy else None
        close_btn = legacy.findChild(QPushButton, "closeButton") if legacy else None

        # ---------- 第一阶段：只搭新骨架，不碰旧控件 ----------
        root = QWidget()
        root.setObjectName("HJRoot")
        root.setAcceptDrops(True)
        root.setMouseTracking(True)
        root.setStyleSheet(theme.build_qss(self._hj_fonts, assets))
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QWidget()
        header.setObjectName("HJHeader")
        header.setFixedHeight(self.HEADER_H)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 0, 8, 0)
        hl.setSpacing(4)
        wordmark = self._label("治幕", "wordmark")
        sub = self._label("Heal-Jimaku", "sub")
        hl.addWidget(wordmark)
        hl.addSpacing(8)
        hl.addWidget(sub, 0, Qt.AlignmentFlag.AlignBottom)
        hl.addStretch(1)
        self._hj_header_layout = hl
        outer.addWidget(header)
        outer.addWidget(self._line("hline"))

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)

        # 左栏
        sidebar = QWidget()
        sidebar.setObjectName("HJSidebar")
        sidebar.setFixedWidth(self.SIDEBAR_W)
        sv = QVBoxLayout(sidebar)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setAutoFillBackground(False)
        scroll.viewport().setObjectName("HJViewport")
        form = QWidget()
        form.setObjectName("HJForm")
        fl = QVBoxLayout(form)
        fl.setContentsMargins(24, 20, 24, 20)
        fl.setSpacing(26)
        scroll.setWidget(form)
        sv.addWidget(scroll, 1)
        sv.addWidget(self._line("hline"))
        footer = QWidget()
        ftl = QVBoxLayout(footer)
        ftl.setContentsMargins(24, 14, 24, 18)
        ftl.setSpacing(10)
        sv.addWidget(footer)
        body.addWidget(sidebar)

        # 右侧放映区
        stage = QWidget()
        stage.setObjectName("HJStage")
        stl = QVBoxLayout(stage)
        stl.setContentsMargins(24, 24, 24, 24)
        stl.setSpacing(16)
        self._preview = SubtitlePreview(self._hj_fonts)
        stl.addWidget(self._preview, 1)
        log_card = QFrame()
        log_card.setProperty("role", "card")
        lcl = QVBoxLayout(log_card)
        lcl.setContentsMargins(16, 8, 10, 10)
        lcl.setSpacing(4)
        lhead = QHBoxLayout()
        lhead.addWidget(self._label("日志", "cardtitle"))
        lhead.addStretch(1)
        self._log_toggle = QPushButton("收起")
        self._log_toggle.setProperty("role", "plain")
        self._log_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._log_toggle.clicked.connect(self._hj_toggle_log)
        lhead.addWidget(self._log_toggle)
        lcl.addLayout(lhead)
        stl.addWidget(log_card)
        body.addWidget(stage, 1)
        self._hj_sidebar, self._hj_stage = sidebar, stage

        # ---------- 第二阶段：把旧控件挪进来（每个控件先拍快照，失败可原样放回） ----------
        self._hj_root = root
        self._hj_legacy_root = legacy

        # 标题栏按钮
        for attr, text in (("settings_button", "SRT 参数"), ("llm_advanced_settings_button", "LLM 配置"),
                           ("background_settings_button", "外观")):
            btn = getattr(self, attr, None)
            if btn is not None:
                self._adopt(btn, "title", text=text, clear_icon=True)
                hl.addWidget(btn)
        hl.addSpacing(6)
        vl = self._line("vline")
        vl.setFixedSize(1, 22)
        hl.addWidget(vl, 0, Qt.AlignmentFlag.AlignVCenter)
        hl.addSpacing(6)
        if min_btn is None:
            min_btn = QPushButton()   # 新建的，无需快照
            min_btn.clicked.connect(self.showMinimized)
        if close_btn is None:
            close_btn = QPushButton()
            close_btn.clicked.connect(self.close)
        for b, text, danger in ((min_btn, "─", False), (close_btn, "✕", True)):
            if b is not None:
                self._adopt(b, "winctl", text=text, clear_icon=True)
                b.setProperty("danger", "true" if danger else "false")
                hl.addWidget(b)

        # ① 来源
        s1 = self._step(fl, "1", "来源")
        seg = QFrame()
        seg.setProperty("role", "segwrap")
        sgl = QHBoxLayout(seg)
        sgl.setContentsMargins(4, 4, 4, 4)
        sgl.setSpacing(4)
        self._seg_local = QPushButton("本地 JSON")
        self._seg_cloud = QPushButton("云端转录")
        self._seg_group = QButtonGroup(self)
        self._seg_group.setExclusive(True)
        for b in (self._seg_local, self._seg_cloud):
            b.setProperty("role", "seg")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self._seg_group.addButton(b)
            sgl.addWidget(b, 1)
        self._seg_local.setChecked(True)
        self._seg_local.clicked.connect(lambda: self._hj_switch_mode(False))
        self._seg_cloud.clicked.connect(lambda: self._hj_switch_mode(True))
        s1.addWidget(seg)
        s1.addSpacing(4)
        row = QHBoxLayout()
        row.setSpacing(8)
        self._adopt(self.json_path_entry, None, expand=True)
        self._adopt(self.json_browse_button, None, text="浏览")
        row.addWidget(self.json_path_entry, 1)
        row.addWidget(self.json_browse_button)
        s1.addLayout(row)
        self._fmt_label = self._label("JSON 来自哪个服务", "field")
        s1.addSpacing(8)
        s1.addWidget(self._fmt_label)
        self._chips_box = QWidget()
        self._chips_flow = FlowLayout(self._chips_box, 8, 8)
        self._chip_group = QButtonGroup(self)
        self._chip_group.setExclusive(True)
        self._chips: List[QPushButton] = []
        s1.addWidget(self._chips_box)
        self._hj_rebuild_chips()
        # 原下拉框保留但隐藏：旧逻辑照常读写它，标签只是它的「皮」
        for w in (self.json_format_combo, self.free_transcription_button):
            self._hj_snapshot(w, move=False)
            w.hide()
        self._ai_hint = None
        if getattr(self, "ai_correction_check", None) is not None:
            s1.addSpacing(8)
            self._adopt_check(self.ai_correction_check, "AI 校对")
            s1.addWidget(self.ai_correction_check)
            self._ai_hint = self._label("", "hint")
            self._ai_hint.setContentsMargins(50, 0, 0, 0)
            s1.addWidget(self._ai_hint)

        # ② 断句模型
        s2 = self._step(fl, "2", "断句模型")
        self._profile_btn = QPushButton()
        self._profile_btn.setProperty("role", "card")
        self._profile_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pl = QHBoxLayout(self._profile_btn)
        pl.setContentsMargins(10, 0, 12, 0)
        pl.setSpacing(10)
        self._p_avatar = self._label("D", "avatar")
        self._p_avatar.setFixedSize(28, 28)
        self._p_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._p_name = self._label("", "pname")
        self._p_model = self._label("", "pmodel")
        chev = self._label("更换 ›", "chev")
        for w in (self._p_avatar, self._p_name, self._p_model, chev):
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # 档案名固定按内容宽度，绝不压缩；模型名在 _hj_sync 里按剩余宽度省略，空余留给末尾 stretch
        self._p_name.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        pl.addWidget(self._p_avatar)
        pl.addWidget(self._p_name)
        pl.addWidget(self._p_model)
        pl.addStretch(1)
        pl.addWidget(chev)
        self._profile_btn.clicked.connect(lambda: self._click_if_enabled("llm_advanced_settings_button"))
        s2.addWidget(self._profile_btn)
        s2.addSpacing(10)
        s2.addWidget(self._label("API Key", "field"))
        row = QHBoxLayout()
        row.setSpacing(8)
        self._adopt(self.api_key_entry, None, expand=True)
        self.api_key_entry.setProperty("mono", "true")
        row.addWidget(self.api_key_entry, 1)
        vis = getattr(self, "api_key_visibility_button", None)
        if vis is not None:
            self._adopt(vis, "icon")
            if not vis.text() and vis.icon().isNull():
                vis.setText("👁")
            row.addWidget(vis)
        test = getattr(self, "test_connection_button", None)
        if test is not None:
            self._adopt(test, None, text="测试")
            row.addWidget(test)
        s2.addLayout(row)
        remember = getattr(self, "remember_api_key_checkbox", None)
        if remember is not None:
            s2.addSpacing(6)
            self._adopt_check(remember, "记住 Key（不勾选则退出时清除）")
            s2.addWidget(remember)

        # ③ 导出到
        s3 = self._step(fl, "3", "导出到")
        row = QHBoxLayout()
        row.setSpacing(8)
        self._adopt(self.output_path_entry, None, expand=True)
        self.output_path_entry.setProperty("mono", "true")
        self._adopt(self.output_browse_button, None, text="选择")
        row.addWidget(self.output_path_entry, 1)
        row.addWidget(self.output_browse_button)
        s3.addLayout(row)
        self._srt_link = QPushButton("")
        self._srt_link.setProperty("role", "link")
        self._srt_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self._srt_link.clicked.connect(lambda: self._click_if_enabled("settings_button"))
        s3.addWidget(self._srt_link)
        fl.addStretch(1)

        # 底部：开始
        self._adopt(self.start_button, "primary", text="开始治幕")
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.setProperty("running", "false")
        ftl.addWidget(self.start_button)
        self._adopt(self.progress_bar, None)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        ftl.addWidget(self.progress_bar)
        self._foot_hint = self._label("", "hint")
        self._foot_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ftl.addWidget(self._foot_hint)

        # 日志
        self._adopt(self.log_area, None)
        self.log_area.setFrameShape(QFrame.Shape.NoFrame)
        self.log_area.setFixedHeight(150)
        try:
            self.log_area.document().setDocumentMargin(4)
        except Exception:
            pass
        lcl.addWidget(self.log_area)

        # 拖拽遮罩如果已经建好，挂到新根上
        ov = getattr(self, "drag_overlay_widget", None)
        if isinstance(ov, QWidget):
            self._hj_snapshot(ov)
            ov.setParent(root)
            ov.hide()

        # ---------- 第三阶段：全部装配成功后才换根 ----------
        # （背景图此时还没加载，等 _load_background → _scale_background_to_window 再交给放映区）
        self.takeCentralWidget()
        if legacy is not None:
            legacy.setParent(self)   # 留着引用，旧代码里如果还碰到那些分组/标签也不会崩
            legacy.hide()
        self.main_widget = root
        self.setCentralWidget(root)
        self.setContentsMargins(self.EDGE, self.EDGE, self.EDGE, self.EDGE)

    # ------------------------------------------------------------ 构建小工具
    def _label(self, text: str, role: str) -> QLabel:
        lb = QLabel(text)
        lb.setProperty("role", role)
        return lb

    def _line(self, role: str) -> QFrame:
        f = QFrame()
        f.setProperty("role", role)
        if role == "hline":
            f.setFixedHeight(1)
        else:
            f.setFixedWidth(1)
        return f

    def _step(self, parent_layout: QVBoxLayout, num: str, title: str) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(8)
        head = QHBoxLayout()
        head.setSpacing(10)
        head.addWidget(self._label(num, "stepnum"), 0, Qt.AlignmentFlag.AlignBottom)
        head.addWidget(self._label(title, "steptitle"), 0, Qt.AlignmentFlag.AlignBottom)
        head.addStretch(1)
        box.addLayout(head)
        box.addSpacing(4)
        parent_layout.addLayout(box)
        return box

    def _adopt(self, w: QWidget, role: Optional[str], text: Optional[str] = None,
               clear_icon: bool = False, expand: bool = False):
        """接管一个旧控件：清掉旧的内联样式和尺寸限制，换上新角色。"""
        self._hj_snapshot(w)
        w.setStyleSheet("")
        w.setMinimumSize(0, 0)
        w.setMaximumSize(16777215, 16777215)
        w.setSizePolicy(QSizePolicy.Policy.Expanding if expand else QSizePolicy.Policy.Preferred,
                        QSizePolicy.Policy.Preferred)
        if role:
            w.setProperty("role", role)
        if isinstance(w, QPushButton):
            if clear_icon:
                w.setIcon(QIcon())
            if text is not None:
                w.setText(text)
            w.setCursor(Qt.CursorShape.PointingHandCursor)
        w.show()
        self._hj_tracked.append(w)

    def _adopt_check(self, w: QWidget, text: Optional[str]):
        """StrokeCheckBoxWidget：去掉描边、换成开关样式，开关和文字紧挨着靠左。"""
        self._hj_snapshot(w)
        w.setStyleSheet("")
        w.setMinimumSize(0, 0)
        w.setMaximumSize(16777215, 16777215)
        inner = getattr(w, "checkbox", None)
        label = getattr(w, "label", None)
        if inner is not None:
            self._hj_snapshot(inner, move=False)
            inner.setStyleSheet("")
            inner.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            inner.setCursor(Qt.CursorShape.PointingHandCursor)
            self._hj_tracked.append(inner)
        if label is not None:
            self._hj_snapshot(label, move=False)
            label.setStyleSheet("")
            label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
            if hasattr(label, "setAlignment"):
                label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            if text and hasattr(label, "setText"):
                label.setText(text)
            if hasattr(label, "setCustomColors"):
                label.setCustomColors(QColor(theme.INK), QColor(0, 0, 0, 0))
            label.setMinimumWidth(0)
            label.setCursor(Qt.CursorShape.PointingHandCursor)
            # 点文字也能切换（原版只能点小方框）
            if inner is not None:
                label.mousePressEvent = lambda e, cb=inner: (cb.toggle() if cb.isEnabled() else None, e.accept())
            self._hj_tracked.append(label)
        lay = w.layout()
        if isinstance(lay, QBoxLayout) and not w.property("hj_stretched"):
            lay.addStretch(1)                   # 余下的宽度给空白，不再让两个子控件平分
            w.setProperty("hj_stretched", True)
        w.show()
        self._hj_tracked.append(w)

    def _hj_snapshot(self, w: QWidget, move: bool = True):
        """记下控件原来的样子和位置，构建失败时 _hj_restore_legacy 用它原样放回。"""
        if any(s["w"] is w for s in self._hj_snap):
            return
        info = {"w": w, "move": move, "parent": w.parentWidget(), "ss": w.styleSheet(),
                "min": w.minimumSize(), "max": w.maximumSize(), "sp": w.sizePolicy(),
                "visible": not w.isHidden(), "role": w.property("role"), "layout": None}
        if isinstance(w, QPushButton):
            info["text"], info["icon"] = w.text(), w.icon()
        if isinstance(w, QLabel):
            info["align"] = w.alignment()
            if hasattr(w, "main_color") and hasattr(w, "stroke_color"):
                info["colors"] = (QColor(w.main_color), QColor(w.stroke_color))
            info["label_text"] = w.text()
        par = w.parentWidget()
        if move and par is not None:
            for lay in [par.layout()] + par.findChildren(QLayout):
                if lay is None:
                    continue
                idx = lay.indexOf(w)
                if idx < 0:
                    continue
                if isinstance(lay, QGridLayout):
                    info["layout"] = ("grid", lay, lay.getItemPosition(idx))
                elif isinstance(lay, QBoxLayout):
                    info["layout"] = ("box", lay, idx, lay.stretch(idx))
                else:
                    info["layout"] = ("other", lay)
                break
        self._hj_snap.append(info)

    def _hj_restore_legacy(self):
        """把已经挪走/改过的旧控件按快照倒序放回，保证旧界面完整可用。"""
        for info in reversed(self._hj_snap):
            w = info["w"]
            try:
                li = info["layout"]
                if info["move"]:
                    if li and li[0] == "grid":
                        r, c, rs, cs = li[2]
                        li[1].addWidget(w, r, c, rs, cs)
                    elif li and li[0] == "box":
                        li[1].insertWidget(li[2], w, li[3])
                    elif li:
                        li[1].addWidget(w)
                    elif info["parent"] is not None and w.parentWidget() is not info["parent"]:
                        w.setParent(info["parent"])
                w.setStyleSheet(info["ss"])
                w.setMinimumSize(info["min"])
                w.setMaximumSize(info["max"])
                w.setSizePolicy(info["sp"])
                w.setProperty("role", info["role"])
                if "text" in info:
                    w.setText(info["text"])
                    w.setIcon(info["icon"])
                if "align" in info:
                    w.setAlignment(info["align"])
                    w.setText(info["label_text"])
                if "colors" in info and hasattr(w, "setCustomColors"):
                    w.setCustomColors(*info["colors"])
                if "mousePressEvent" in w.__dict__:
                    del w.mousePressEvent
                if w.property("hj_stretched"):
                    lay = w.layout()
                    if lay is not None and lay.count():
                        item = lay.itemAt(lay.count() - 1)
                        if item is not None and item.spacerItem() is not None:
                            lay.takeAt(lay.count() - 1)
                    w.setProperty("hj_stretched", None)
                w.setVisible(info["visible"])
            except Exception:
                _safe_print_exc()
        self._hj_snap = []
        legacy = getattr(self, "_hj_legacy_root", None)
        if legacy is not None and self.centralWidget() is not legacy:
            self.takeCentralWidget()
            self.setCentralWidget(legacy)
            legacy.show()
            self.main_widget = legacy
        self.setContentsMargins(0, 0, 0, 0)
        root = getattr(self, "_hj_root", None)
        if root is not None and root is not self.centralWidget():
            root.deleteLater()
        self._hj_root = None
        self._hj_modern = False

    def _hj_rebuild_chips(self):
        for c in self._chips:
            self._chip_group.removeButton(c)
            self._chips_flow.removeWidget(c)
            c.deleteLater()
        self._chips = []
        combo = self.json_format_combo
        for i in range(combo.count()):
            raw = combo.itemText(i)
            rec = "推荐" in raw
            label = raw.replace("(推荐)", "").replace("（推荐）", "").strip()
            c = QPushButton(label)
            c.setProperty("role", "chip")
            c.setCheckable(True)
            c.setCursor(Qt.CursorShape.PointingHandCursor)
            if rec:
                c.setToolTip("推荐")
            c.clicked.connect(lambda _=False, idx=i: self._hj_pick_format(idx))
            self._chip_group.addButton(c)
            self._chips_flow.addWidget(c)
            self._chips.append(c)

    def _hj_pick_format(self, idx: int):
        combo = self.json_format_combo
        if combo.isEnabled() and 0 <= idx < combo.count():
            combo.setCurrentIndex(idx)   # 触发旧代码里的 _on_format_changed
        QTimer.singleShot(0, self._hj_sync)

    def _click_if_enabled(self, attr: str):
        b = getattr(self, attr, None)
        if b is not None and b.isEnabled():
            b.click()

    def _hj_toggle_log(self):
        vis = not self.log_area.isVisible()
        self.log_area.setVisible(vis)
        self._log_toggle.setText("收起" if vis else "展开")

    # ============================================================ 模式
    def _hj_is_cloud(self) -> bool:
        mode = getattr(self, "_current_input_mode", "local_json")
        return mode in ("free_transcription", "cloud_transcription") or \
            bool(getattr(self, "_free_transcription_button_is_in_cancel_mode", False))

    def _hj_switch_mode(self, want_cloud: bool):
        """分段按钮 → 点原来的「云端获取JSON / 取消云端转录」按钮，走旧逻辑。"""
        if bool(getattr(self, "is_processing", False)):
            QTimer.singleShot(0, self._hj_sync)
            return
        if want_cloud == self._hj_is_cloud():
            QTimer.singleShot(0, self._hj_sync)
            return
        cancel_mode = bool(getattr(self, "_free_transcription_button_is_in_cancel_mode", False))
        if not want_cloud and not cancel_mode:
            # 云端任务跑完后，旧 _on_task_finished 只复位了按钮状态，_current_input_mode 还停在云端。
            # 这时再点原按钮会走「打开云端对话框」分支，所以直接调旧代码自己的复位函数。
            reset = getattr(self, "_cancel_free_transcription_mode", None)
            if callable(reset):
                reset()
            else:
                self._current_input_mode = "local_json"
                upd = getattr(self, "_update_input_mode_ui", None)
                if callable(upd):
                    upd()
        else:
            btn = self.free_transcription_button
            if btn.isEnabled():
                btn.click()      # 本地→云端：弹出云端转录对话框；云端(取消态)→本地：取消云端模式
        QTimer.singleShot(0, self._hj_sync)

    # ============================================================ 状态同步
    def _hj_sync(self):
        if not self._hj_on():
            return
        try:
            self._hj_sync_inner()
        except Exception as e:
            # 每种错误各打印一次，但同步本身不停：下一个 250ms 照常再试
            tb = traceback.extract_tb(e.__traceback__)
            sig = (type(e).__name__, str(e), tb[-1].lineno if tb else 0)
            if sig not in self._hj_seen_errors and len(self._hj_seen_errors) < 50:
                self._hj_seen_errors.add(sig)
                _safe_print_exc()

    def _hj_sync_inner(self):
        busy = bool(getattr(self, "is_processing", False))

        # 旧代码运行时会往控件上塞内联样式（红色停止按钮等），统一清掉，交给 QSS
        for w in self._hj_tracked:
            try:
                if w.styleSheet():
                    w.setStyleSheet("")
            except RuntimeError:
                pass

        # 开始 / 停止
        sb = self.start_button
        want = "true" if busy else "false"
        if sb.property("running") != want:
            sb.setProperty("running", want)
            _repolish(sb)
        txt = sb.text()
        if busy:
            if "正在停止" not in txt and txt != "停止":
                sb.setText("停止")
        elif txt != "开始治幕":
            sb.setText("开始治幕")

        # 模式分段
        cloud = self._hj_is_cloud()
        (self._seg_cloud if cloud else self._seg_local).setChecked(True)
        for b in (self._seg_local, self._seg_cloud):
            b.setEnabled(not busy)
        self._fmt_label.setText("转录完成后按此格式解析" if cloud else "JSON 来自哪个服务")

        # 格式标签
        combo = self.json_format_combo
        if combo.count() != len(self._chips):
            self._hj_rebuild_chips()
        ci = combo.currentIndex()
        en = combo.isEnabled() and not busy
        if 0 <= ci < len(self._chips) and not self._chips[ci].isChecked():
            self._chips[ci].setChecked(True)
        for c in self._chips:
            c.setEnabled(en)

        ai = getattr(self, "ai_correction_check", None)
        if ai is not None:
            # 旧 _set_all_controls_enabled(True) 在任务结束时会无条件启用这个开关，
            # 不会再按格式判一次；这里按当前格式重新对齐（等同于旧 _on_format_changed 的规则）
            is_soniox = "soniox" in combo.currentText().lower()
            if not busy and ai.isEnabled() != is_soniox:
                ai.setEnabled(is_soniox)
                if not is_soniox and ai.isChecked():
                    ai.setChecked(False)
            if self._ai_hint is not None:
                self._ai_hint.setText("导出后再让 LLM 校一遍同音错字" if is_soniox else "仅 Soniox 格式可用")

        # 开关文字颜色（CustomLabel 自己画字，不吃 QSS 的 disabled 颜色）
        for attr in ("ai_correction_check", "remember_api_key_checkbox"):
            w = getattr(self, attr, None)
            lb = getattr(w, "label", None) if w is not None else None
            if lb is not None and hasattr(lb, "setCustomColors"):
                col = theme.INK if w.isEnabled() else theme.FAINT
                if self._hj_label_colors.get(attr) != col:
                    self._hj_label_colors[attr] = col
                    lb.setCustomColors(QColor(col), QColor(0, 0, 0, 0))

        # 模型档案
        name, model = self._hj_profile_info()
        self._p_avatar.setText((name[:1] or "?").upper())
        self._p_name.setText(name or "未配置")
        # 卡片宽度 - 头像 - 档案名 - 「更换 ›」- 间距，剩下的给模型名，放不下就中间省略
        room = max(40, self._profile_btn.width() - 28 - self._p_name.sizeHint().width() - 64 - 40)
        shown = self._p_model.fontMetrics().elidedText(model or "", Qt.TextElideMode.ElideMiddle, room)
        if self._p_model.text() != shown:
            self._p_model.setText(shown)
        self._p_model.setToolTip(model if shown != model else "")

        # SRT 参数摘要
        self._srt_link.setText(self._hj_srt_summary() + "   改 ›")

        # 底部提示
        jb = list(getattr(self, "_batch_files", []) or [])
        ab = list(getattr(self, "_batch_audio_files", []) or [])
        n = len(ab) if cloud else len(jb)
        src = f"批量 {n} 个文件" if n > 1 else "单个文件"
        if cloud:
            fmt = "云端转录"
        else:
            fmt = self._chips[ci].text() if 0 <= ci < len(self._chips) else "JSON"
        self._foot_hint.setText(f"{src} · {fmt} → SRT")

        # 放映区
        if busy:
            self._preview.set_progress(self.progress_bar.value())
            return
        if self._preview.state == "healing":
            return
        healed = self._preview.state == "healed"
        if cloud:
            single = getattr(self, "_temp_audio_file_for_free_transcription", None)
            name = os.path.basename(ab[0]) if ab else (os.path.basename(single) if single else "")
            key = ("cloud", name)
            if key != self._hj_preview_key:
                self._hj_preview_key = key
                if healed and not name:
                    return
                self._preview.set_waiting(name + (f"  等 {len(ab)} 个" if len(ab) > 1 else ""))
        else:
            path = jb[0] if jb else self.json_path_entry.text().strip()
            key = ("json", path)
            if key != self._hj_preview_key:
                self._hj_preview_key = key
                valid = bool(path) and path.lower().endswith(".json") and os.path.isfile(path)
                if healed and not valid:
                    return   # 转换结束后旧逻辑会把云端模式复位，别把刚出炉的结果冲掉
                if valid:
                    self._hj_autopick_format(path)
                    words = load_words_from_json(path)
                    label = os.path.basename(path) + (f"  等 {len(jb)} 个" if len(jb) > 1 else "")
                    if words:
                        self._preview.set_words(words, label)
                    else:
                        self._preview.set_empty()
                else:
                    self._preview.set_empty()

    def _hj_autopick_format(self, path: str):
        """选中 / 拖入的 JSON 能认出来源时，自动把格式切过去（目前只认 Gemini Transcribe）。"""
        if sniff_json_source(path) != "gemini":
            return
        combo = self.json_format_combo
        idx = combo.findText("Gemini")
        if idx < 0 or idx == combo.currentIndex() or not combo.isEnabled():
            return
        combo.setCurrentIndex(idx)          # 走旧代码的 _on_format_changed，配置里也会记住
        log = getattr(self, "log_message", None)
        if callable(log):
            log("已识别为 Gemini Transcribe 输出，格式自动切换为 Gemini")

    def _hj_profile_info(self):
        prof = None
        getter = _cfg("get_current_llm_profile")
        if callable(getter):
            try:
                prof = getter(getattr(self, "config", {}) or {})
            except Exception:
                prof = None
        for meth in (() if isinstance(prof, dict) else
                     ("_get_current_llm_profile", "get_current_llm_profile", "_get_current_profile")):
            f = getattr(self, meth, None)
            if callable(f):
                try:
                    prof = f()
                    break
                except Exception:
                    prof = None
        if not isinstance(prof, dict):
            cfg = getattr(self, "config", {}) or {}
            lp = cfg.get(_cfg("LLM_PROFILES_KEY", "llm_profiles"))
            cid_key = _cfg("CURRENT_PROFILE_ID_KEY", "current_profile_id")
            profiles, cid = [], cfg.get(cid_key)
            if isinstance(lp, dict):
                profiles = lp.get("profiles", []) or []
                cid = lp.get(cid_key) or lp.get("current_profile_id") or cid
            elif isinstance(lp, list):
                profiles = lp
            for p in profiles:
                if isinstance(p, dict) and p.get("id") == cid:
                    prof = p
                    break
            if prof is None and profiles and isinstance(profiles[0], dict):
                prof = profiles[0]
        if not isinstance(prof, dict):
            return "", ""
        name = prof.get("name") or prof.get("profile_name") or prof.get("display_name") or ""
        model = prof.get("model_name") or prof.get("model") or ""
        return str(name), str(model)

    def _hj_srt_summary(self) -> str:
        s = getattr(self, "advanced_srt_settings", {}) or {}

        def g(const, short, default_const, fallback):
            for k in (_cfg(const), short, "user_" + short):
                if k and k in s:
                    return s[k]
            return _cfg(default_const, fallback)

        mn = g("USER_MIN_DURATION_TARGET_KEY", "min_duration_target", "DEFAULT_MIN_DURATION_TARGET", 1.2)
        mx = g("USER_MAX_DURATION_KEY", "max_duration", "DEFAULT_MAX_DURATION", 12.0)
        ch = g("USER_MAX_CHARS_PER_LINE_KEY", "max_chars_per_line", "DEFAULT_MAX_CHARS_PER_LINE", 60)
        gp = g("USER_DEFAULT_GAP_MS_KEY", "default_gap_ms", "DEFAULT_DEFAULT_GAP_MS", 100)

        def n(v):
            try:
                return f"{float(v):g}"
            except (TypeError, ValueError):
                return str(v)
        return f"{n(mn)}–{n(mx)}s · ≤{n(ch)}字/行 · 间隔{n(gp)}ms"

    # ============================================================ 任务钩子
    def _on_task_started(self, *args, **kwargs):
        if self._hj_on():
            self._hj_t0 = time.time()
            self._preview.begin_healing()
        result = super()._on_task_started(*args, **kwargs)
        if self._hj_on():
            self._hj_sync()
        return result

    def _on_task_finished(self, *args, **kwargs):
        if self._hj_on():
            success = next((a for a in args if isinstance(a, bool)), kwargs.get("success", True))
            try:
                if success:
                    self._hj_show_result()
                else:
                    self._preview.cancel_healing()
            except Exception:
                _safe_print_exc()
                self._preview.cancel_healing()
        result = super()._on_task_finished(*args, **kwargs)   # 原逻辑会弹完成提示框
        if self._hj_on():
            self._hj_sync()
        return result

    def update_progress(self, value, *args, **kwargs):
        result = super().update_progress(value, *args, **kwargs)
        if self._hj_on():
            self._preview.set_progress(value)
        return result

    def _hj_show_result(self):
        """转换完成：在导出目录里找本次新写出的 SRT（以及云端模式下的 JSON），放进预览。"""
        out = self.output_path_entry.text().strip()
        t0 = self._hj_t0 - 2
        srts, jsons = [], []
        if os.path.isdir(out):
            dirs = [out] + [os.path.join(out, d) for d in os.listdir(out) if os.path.isdir(os.path.join(out, d))][:50]
            for d in dirs:
                try:
                    names = os.listdir(d)
                except OSError:
                    continue
                for fn in names:
                    p = os.path.join(d, fn)
                    try:
                        m = os.path.getmtime(p)
                    except OSError:
                        continue
                    if m < t0:
                        continue
                    low = fn.lower()
                    if low.endswith(".srt"):
                        srts.append((m, p))
                    elif low.endswith(".json"):
                        jsons.append((m, p))
        if not srts:
            self._preview.cancel_healing()
            return
        srt_path = max(srts)[1]
        cues = load_srt(srt_path)
        words = None
        if not self._preview.words and jsons:
            words = load_words_from_json(max(jsons)[1])
        self._preview.finish_healing(cues, words, os.path.basename(srt_path))

    # ============================================================ 窗口外观覆盖
    def _scale_background_to_window(self, *args, **kwargs):
        if not self._hj_on():
            return super()._scale_background_to_window(*args, **kwargs)
        bg = getattr(self, "original_background", None)
        # 旧 resizeEvent 发现 background 为空会重新随机加载，所以这里给它一个非空引用
        self.background = bg
        # 只在换了图时才交给放映区；纯 resize 由放映区自己的 resizeEvent 重缩放，避免一次拖动缩两遍
        if bg is not None and self._preview.backdrop is not bg:
            self._preview.set_backdrop(bg)

    def _init_adaptive_window_size(self, *args, **kwargs):
        if not self._hj_on():
            return super()._init_adaptive_window_size(*args, **kwargs)
        if getattr(self, "_hj_sized", False):
            return      # 换背景时旧代码会再调一次，别把用户拖好的窗口大小重置
        self._hj_sized = True
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(1240, 800)
            return
        ag = screen.availableGeometry()
        w = min(1280, int(ag.width() * 0.92))
        h = min(820, int(ag.height() * 0.92))
        self.setMinimumSize(min(1000, w), min(660, h))
        self.resize(w, h)

    def _update_layout_proportions(self, *args, **kwargs):
        if not self._hj_on():
            f = getattr(super(), "_update_layout_proportions", None)
            return f(*args, **kwargs) if f else None

    def _update_control_heights(self, *args, **kwargs):
        if not self._hj_on():
            f = getattr(super(), "_update_control_heights", None)
            return f(*args, **kwargs) if f else None

    def _apply_responsive_fonts(self, *args, **kwargs):
        if not self._hj_on():
            f = getattr(super(), "_apply_responsive_fonts", None)
            return f(*args, **kwargs) if f else None

    def paintEvent(self, event):
        if not self._hj_on():
            return super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        radius = 0 if self.isMaximized() else 12
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, radius, radius)
        p.fillPath(path, QBrush(QColor(theme.PAPER)))
        p.setClipPath(path)
        stage = getattr(self, "_hj_stage", None)
        if stage is not None and stage.isVisible():
            tl = stage.mapTo(self, QPoint(0, 0))
            p.fillRect(QRect(tl.x(), tl.y(), self.width() - tl.x(), self.height() - tl.y()), QColor(theme.STAGE))
            p.fillRect(QRect(tl.x() - 1, tl.y(), 1, self.height() - tl.y()), QColor(theme.LINE))
        p.setClipping(False)
        p.setPen(QPen(QBrush(QColor("#c4d6d6")), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.end()
