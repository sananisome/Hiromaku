"""
theme_modern.py —— 治幕新界面的配色、字体与 QSS

配色取自原型：纸面 / 墨 / 青（主色）/ 深青 / 陶土（原始碎片）/ 余烬（播放头）/ 血红（危险）/ 苔绿（成功）。
所有样式都挂在 #HJRoot 下，不会污染各个设置弹窗原有的样式。
"""
from __future__ import annotations

import os
import tempfile
from string import Template
from typing import Iterable

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QBrush, QColor, QFontDatabase, QPainter, QPixmap, QPen

PAPER = "#f6fafa"
CARD = "#edf3f3"
LINE = "#d5e2e2"
MUTED = "#587577"
FAINT = "#9db3b4"
INK = "#1b3133"
TEAL = "#007d82"
TEAL_HOVER = "#006c70"
TEAL_SOFT = "#e3f1f1"
DEEP = "#004042"
STAGE = "#eaf1f1"
CLAY = "#c38961"
EMBER = "#e04b28"
BLOOD = "#950404"
MOSS = "#388f30"


def pick_family(candidates: Iterable[str], fallback: str) -> str:
    try:
        fams = set(QFontDatabase.families())
    except Exception:
        return fallback
    for c in candidates:
        if c in fams:
            return c
    return fallback


def resolve_fonts():
    ui = pick_family(["Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "Noto Sans SC",
                      "Source Han Sans SC", "思源黑体"], "Microsoft YaHei")
    serif = pick_family(["Noto Serif SC", "Source Han Serif SC", "思源宋体", "Songti SC",
                         "STSong", "SimSun", "宋体"], ui)
    mono = pick_family(["Cascadia Mono", "Cascadia Code", "JetBrains Mono", "Consolas",
                        "Menlo", "Courier New"], "Consolas")
    jp = pick_family(["Noto Sans JP", "Yu Gothic UI", "Meiryo UI", "Meiryo", "Hiragino Sans",
                      "Microsoft YaHei UI"], ui)
    return {"ui": ui, "serif": serif, "mono": mono, "jp": jp}


# ---------------------------------------------------------------- 运行时生成的小图（开关、勾）
def _draw_toggle(path: str, on: bool, enabled: bool, scale: int):
    w, h = 40 * scale, 24 * scale
    pm = QPixmap(w, h)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    track = QColor(TEAL if on else "#c6d6d6")
    if not enabled:
        track.setAlpha(110)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(track))
    p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
    knob = QColor("#ffffff")
    if not enabled:
        knob.setAlpha(200)
    d = 16 * scale
    x = (w - d - 4 * scale) if on else 4 * scale
    p.setBrush(QBrush(QColor(0, 40, 42, 40)))
    p.drawEllipse(QRectF(x, 4 * scale + scale * 0.6, d, d))
    p.setBrush(QBrush(knob))
    p.drawEllipse(QRectF(x, 4 * scale, d, d))
    p.end()
    pm.save(path, "PNG")


def ensure_assets() -> dict:
    folder = os.path.join(tempfile.gettempdir(), "heal_jimaku_theme_v1")
    os.makedirs(folder, exist_ok=True)
    out = {}
    for name, on, en in (("toggle_on", True, True), ("toggle_off", False, True),
                         ("toggle_on_dis", True, False), ("toggle_off_dis", False, False)):
        p1 = os.path.join(folder, f"{name}.png")
        p2 = os.path.join(folder, f"{name}@2x.png")
        if not os.path.exists(p1):
            _draw_toggle(p1, on, en, 1)
        if not os.path.exists(p2):
            _draw_toggle(p2, on, en, 2)
        out[name] = p1.replace(os.sep, "/")
    return out


# ---------------------------------------------------------------- QSS
_QSS = Template(r"""
#HJRoot { background: transparent; }
#HJRoot QWidget { font-family: "$ui"; font-size: 14px; color: $INK; }
#HJRoot #HJForm, #HJRoot #HJViewport, #HJRoot #HJSidebar, #HJRoot #HJStage, #HJRoot #HJHeader { background: transparent; }

#HJRoot QLabel { background: transparent; }
#HJRoot QLabel[role="wordmark"] { font-family: "$serif"; font-size: 26px; font-weight: 900; color: $DEEP; }
#HJRoot QLabel[role="sub"] { color: $MUTED; letter-spacing: 1px; }
#HJRoot QLabel[role="stepnum"] { font-family: "$serif"; font-size: 22px; font-weight: 900; color: $TEAL; }
#HJRoot QLabel[role="steptitle"] { font-size: 16px; font-weight: bold; letter-spacing: 1px; }
#HJRoot QLabel[role="field"] { color: $MUTED; }
#HJRoot QLabel[role="hint"] { color: $MUTED; }
#HJRoot QLabel[role="cardtitle"] { font-weight: bold; letter-spacing: 1px; }
#HJRoot QLabel[role="avatar"] { background: $DEEP; color: #ffffff; border-radius: 8px;
    font-family: "$serif"; font-weight: 900; font-size: 14px; }
#HJRoot QLabel[role="pname"] { font-weight: 600; }
#HJRoot QLabel[role="pmodel"] { font-family: "$mono"; color: $MUTED; }
#HJRoot QLabel[role="chev"] { color: $MUTED; }

#HJRoot QFrame[role="hline"] { background: $LINE; border: none; }
#HJRoot QFrame[role="vline"] { background: $LINE; border: none; }
#HJRoot QFrame[role="card"] { background: #ffffff; border: 1px solid $LINE; border-radius: 16px; }
#HJRoot QFrame[role="segwrap"] { background: $CARD; border: none; border-radius: 12px; }

/* 输入框 */
#HJRoot QLineEdit { background: #ffffff; border: 1px solid $LINE; border-radius: 10px;
    padding: 0 10px; min-height: 38px; max-height: 38px; selection-background-color: $TEAL; }
#HJRoot QLineEdit:focus { border: 1px solid $TEAL; }
#HJRoot QLineEdit:disabled, #HJRoot QLineEdit:read-only { background: $CARD; color: $MUTED; }
#HJRoot QLineEdit[mono="true"] { font-family: "$mono"; }

/* 按钮：默认是描边幽灵按钮 */
#HJRoot QPushButton { background: #ffffff; border: 1px solid $LINE; border-radius: 10px;
    padding: 0 14px; min-height: 38px; max-height: 38px; font-weight: 500; }
#HJRoot QPushButton:hover { background: $CARD; border-color: #bcd0d0; }
#HJRoot QPushButton:pressed { background: #e2ecec; }
#HJRoot QPushButton:disabled { color: $FAINT; background: $CARD; border-color: $LINE; }

#HJRoot QPushButton[role="icon"] { padding: 0; min-width: 38px; max-width: 38px; }

#HJRoot QPushButton[role="title"] { background: transparent; border: none; color: $MUTED;
    border-radius: 8px; padding: 0 12px; min-height: 34px; max-height: 34px; }
#HJRoot QPushButton[role="title"]:hover { background: $CARD; color: $INK; }
#HJRoot QPushButton[role="title"]:disabled { color: $FAINT; background: transparent; }

#HJRoot QPushButton[role="winctl"] { background: transparent; border: none; color: $MUTED;
    border-radius: 8px; padding: 0; min-width: 34px; max-width: 34px; min-height: 34px; max-height: 34px;
    font-size: 15px; }
#HJRoot QPushButton[role="winctl"]:hover { background: $CARD; color: $INK; }
#HJRoot QPushButton[role="winctl"][danger="true"]:hover { background: $BLOOD; color: #ffffff; }

#HJRoot QPushButton[role="seg"] { background: transparent; border: none; border-radius: 9px;
    color: $MUTED; min-height: 34px; max-height: 34px; font-weight: 500; }
#HJRoot QPushButton[role="seg"]:hover { color: $INK; }
#HJRoot QPushButton[role="seg"]:checked { background: #ffffff; color: $DEEP; font-weight: 600; }
#HJRoot QPushButton[role="seg"]:disabled { color: $FAINT; }

#HJRoot QPushButton[role="chip"] { border-radius: 16px; min-height: 32px; max-height: 32px; padding: 0 13px; }
#HJRoot QPushButton[role="chip"]:checked { background: $DEEP; border-color: $DEEP; color: #ffffff; }
#HJRoot QPushButton[role="chip"]:checked:disabled { background: #6d8f90; border-color: #6d8f90; color: #eef5f5; }

#HJRoot QPushButton[role="card"] { text-align: left; border-radius: 12px; min-height: 46px; max-height: 46px; padding: 0 12px; }

#HJRoot QPushButton[role="link"] { background: transparent; border: none; color: $MUTED;
    padding: 0; min-height: 26px; max-height: 26px; text-align: left; font-family: "$mono"; }
#HJRoot QPushButton[role="link"]:hover { color: $TEAL; }
#HJRoot QPushButton[role="plain"] { background: transparent; border: none; color: $MUTED;
    padding: 0 6px; min-height: 28px; max-height: 28px; }
#HJRoot QPushButton[role="plain"]:hover { color: $TEAL; }

#HJRoot QPushButton[role="primary"] { background: $TEAL; color: #ffffff; border: none; border-radius: 16px;
    min-height: 54px; max-height: 54px; font-size: 17px; font-weight: bold; letter-spacing: 3px; }
#HJRoot QPushButton[role="primary"]:hover { background: $TEAL_HOVER; }
#HJRoot QPushButton[role="primary"]:pressed { background: $DEEP; }
#HJRoot QPushButton[role="primary"]:disabled { background: #8fbcbe; color: #eef7f7; }
#HJRoot QPushButton[role="primary"][running="true"] { background: #ffffff; color: $BLOOD;
    border: 1px solid #e3c4c4; letter-spacing: 2px; }
#HJRoot QPushButton[role="primary"][running="true"]:hover { background: #fbf1f1; }
#HJRoot QPushButton[role="primary"][running="true"]:disabled { color: $FAINT; background: $CARD; }

/* 开关（勾选框统一画成开关） */
#HJRoot QCheckBox { spacing: 10px; background: transparent; }
#HJRoot QCheckBox::indicator { width: 40px; height: 24px; image: url("$toggle_off"); }
#HJRoot QCheckBox::indicator:checked { image: url("$toggle_on"); }
#HJRoot QCheckBox::indicator:disabled { image: url("$toggle_off_dis"); }
#HJRoot QCheckBox::indicator:checked:disabled { image: url("$toggle_on_dis"); }

/* 进度条：开始按钮下面一条细线 */
#HJRoot QProgressBar { background: #dbe8e8; border: none; border-radius: 2px;
    min-height: 4px; max-height: 4px; }
#HJRoot QProgressBar::chunk { background: $TEAL; border-radius: 2px; }

/* 日志 */
#HJRoot QTextEdit { background: #ffffff; border: none; color: $INK; selection-background-color: $TEAL; }

/* 滚动 */
#HJRoot QScrollArea { background: transparent; border: none; }
#HJRoot QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
#HJRoot QScrollBar::handle:vertical { background: #c9d9d9; border-radius: 3px; min-height: 30px; }
#HJRoot QScrollBar::handle:vertical:hover { background: #a9c1c1; }
#HJRoot QScrollBar::add-line:vertical, #HJRoot QScrollBar::sub-line:vertical { height: 0; }
#HJRoot QScrollBar::add-page:vertical, #HJRoot QScrollBar::sub-page:vertical { background: transparent; }
""")


def build_qss(fonts: dict, assets: dict) -> str:
    g = {k: v for k, v in globals().items() if k.isupper() and isinstance(v, str)}
    g.update(fonts)
    g.update(assets)
    return _QSS.substitute(g)


# ====================================================================================
# 给其它窗口换皮：把项目原有 ui.theme 的调色板和 QSS 构建函数整体替换成新主题
# ------------------------------------------------------------------------------------
# 所有对话框（SRT 参数 / LLM 配置 / 背景 / 云端转录 / 免费转录 / 编辑弹窗）以及
# 主窗口的拖拽遮罩、弹出的 QMessageBox，都是在「运行时」通过 theme.XXX 取颜色和样式的。
# 所以只要在主窗口创建前把 ui.theme 模块里的值换掉，之后打开的每个窗口自然就是新皮。
# 旧界面（HEAL_JIMAKU_LEGACY_UI=1）和「新界面构建失败回退」都不会调用这里，原主题一字不动。
# ====================================================================================
from PyQt6.QtGui import QFont  # noqa: E402

_INSTALLED = False


def _fs(pt, lo=10.0, hi=12.0) -> float:
    """旧主题字号普遍偏大（13~16pt），收敛到 10~12pt。"""
    try:
        v = float(pt)
    except (TypeError, ValueError):
        return 10.5
    return max(lo, min(hi, round(v * 0.78 * 2) / 2))


def _draw_icon(path: str, kind: str, color: str, scale: int):
    sizes = {"chev_down": (12, 8), "chev_up": (10, 6), "chev_small_down": (10, 6), "check": (14, 14)}
    w, h = sizes[kind]
    pm = QPixmap(w * scale, h * scale)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QBrush(QColor(color)), 1.8 * scale)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    s = float(scale)
    from PyQt6.QtCore import QPointF
    if kind == "chev_down":
        pts = [QPointF(2 * s, 2 * s), QPointF(6 * s, 6 * s), QPointF(10 * s, 2 * s)]
    elif kind == "chev_small_down":
        pts = [QPointF(2 * s, 1.5 * s), QPointF(5 * s, 4.5 * s), QPointF(8 * s, 1.5 * s)]
    elif kind == "chev_up":
        pts = [QPointF(2 * s, 4.5 * s), QPointF(5 * s, 1.5 * s), QPointF(8 * s, 4.5 * s)]
    else:
        pts = [QPointF(3 * s, 7.5 * s), QPointF(6 * s, 10.5 * s), QPointF(11 * s, 4 * s)]
    p.drawPolyline(pts)
    p.end()
    pm.save(path, "PNG")


def ensure_icons() -> dict:
    folder = os.path.join(tempfile.gettempdir(), "heal_jimaku_theme_v1")
    os.makedirs(folder, exist_ok=True)
    out = {}
    for name, kind, color in (("chev_down", "chev_down", MUTED), ("chev_up", "chev_up", MUTED),
                              ("chev_small_down", "chev_small_down", MUTED), ("check", "check", "#ffffff")):
        p1 = os.path.join(folder, f"{name}.png")
        p2 = os.path.join(folder, f"{name}@2x.png")
        if not os.path.exists(p1):
            _draw_icon(p1, kind, color, 1)
        if not os.path.exists(p2):
            _draw_icon(p2, kind, color, 2)
        out[name] = p1.replace(os.sep, "/")
    return out


def _palette(fonts: dict) -> dict:
    return {
        "ACCENT": TEAL, "ACCENT_HOVER": TEAL_HOVER, "ACCENT_PRESSED": DEEP, "ON_ACCENT": "#ffffff",
        "TEXT_PRIMARY": INK, "TEXT_SECONDARY": MUTED,
        "PANEL_BG": "#ffffff", "PANEL_BORDER": LINE,
        "INPUT_BG": "#ffffff", "INPUT_BG_HOVER": "#ffffff", "INPUT_BG_FOCUS": "#ffffff", "INPUT_BORDER": LINE,
        "BTN_NEUTRAL_BG": "#ffffff", "BTN_NEUTRAL_HOVER": CARD, "BTN_NEUTRAL_PRESSED": "#e2ecec",
        "BTN_NEUTRAL_BORDER": LINE,
        "BTN_ICON_LIGHT_BG": "transparent", "BTN_ICON_LIGHT_HOVER": CARD, "BTN_ICON_LIGHT_PRESSED": "#e2ecec",
        "ON_ICON_LIGHT": MUTED,
        "SUCCESS": MOSS, "SUCCESS_HOVER": "#2f7a28", "SUCCESS_PRESSED": "#286a22", "ON_SUCCESS": "#ffffff",
        "DANGER": BLOOD, "DANGER_HOVER": "#7d0303", "DANGER_PRESSED": "#650202", "ON_DANGER": "#ffffff",
        "BTN_DISABLED_BG": CARD, "BTN_DISABLED_TEXT": FAINT,
        "POPUP_BG": "#ffffff", "POPUP_BORDER": LINE, "POPUP_SELECTION": TEAL, "POPUP_HOVER": CARD,
        "LOG_BG": "#ffffff", "LOG_TEXT": INK,
        "DIALOG_BG": PAPER, "DIALOG_BORDER": "#c4d6d6",
        "PROGRESS_CHUNK_A": TEAL, "PROGRESS_CHUNK_B": "#00a3a9",
        "SCRIM_TOP": QColor(3, 24, 25, 0), "SCRIM_BOTTOM": QColor(3, 24, 25, 0),
        "LABEL_MAIN": QColor(INK), "LABEL_STROKE": QColor(0, 0, 0, 0),
        "TITLE_MAIN": QColor(DEEP), "TITLE_STROKE": QColor(0, 0, 0, 0),
        "CHECKBOX_BORDER": "#9fb7b8",
        "ON_SELECTION": "#ffffff", "LIST_HOVER": CARD, "SELECTION_BG": "rgba(0, 125, 130, 70)",
        "TEXT_FOCUS_BG": "#ffffff", "TEXT_FOCUS_BG_STRONG": "#ffffff", "HINT_TEXT": MUTED,
        "SEPARATOR": LINE, "SPLITTER": LINE,
        "INPUT_DISABLED_BG": CARD, "INPUT_DISABLED_BORDER": LINE, "TEXT_LOCKED_BG": CARD,
        "ERROR_SOFT_BG": "#fbecec", "ERROR_SOFT_TEXT": BLOOD, "ERROR_SOFT_BORDER": "#e3c4c4",
        "PROFILE_CURRENT_BG": QColor(0, 125, 130, 34),
        "SLIDER_GROOVE": "#dbe8e8", "SLIDER_GROOVE_DISABLED": CARD, "SLIDER_SUBPAGE_DISABLED": "#c6d6d6",
        "SLIDER_HANDLE": "#ffffff", "SLIDER_HANDLE_BORDER": TEAL,
        "SLIDER_HANDLE_DISABLED": "#ffffff", "SLIDER_HANDLE_DISABLED_BORDER": "#c6d6d6",
        "CLOSE_BG": "transparent", "CLOSE_FG": MUTED, "CLOSE_HOVER_BG": BLOOD, "CLOSE_HOVER_FG": "#ffffff",
        "OVERLAY_SCRIM": "rgba(0, 64, 66, 215)", "OVERLAY_AREA_BG": "rgba(255, 255, 255, 18)",
        "OVERLAY_BORDER": "rgba(255, 255, 255, 170)", "OVERLAY_TEXT": "#ffffff",
    }


def _make_builders(fonts: dict, toggles: dict, icons: dict, legacy_qss_url):
    UI, SERIF = fonts["ui"], fonts["serif"]

    def qss_url(filename: str) -> str:
        name = os.path.basename(filename or "")
        mapping = {
            "dropdown_arrow_light.png": "chev_down", "dropdown_arrow.png": "chev_down",
            "up_arrow_light.png": "chev_up", "up_arrow.png": "chev_up",
            "down_arrow_light.png": "chev_small_down", "down_arrow.png": "chev_small_down",
            "checkmark.png": "check",
        }
        if name in mapping:
            return "url('" + icons[mapping[name]] + "')"
        return legacy_qss_url(filename)

    def button_qss(variant: str = "neutral", *, sel: str = "QPushButton", font_family: str = "",
                   font_size: int = 10, padding: str = "6px 15px", radius: int = 6, bold: bool = True) -> str:
        weight = "600" if bold else "normal"
        r = radius if radius >= 14 else max(radius, 8)
        table = {
            "primary": (TEAL, "#ffffff", "none", TEAL_HOVER, DEEP),
            "success": (MOSS, "#ffffff", "none", "#2f7a28", "#286a22"),
            "danger": ("#ffffff", BLOOD, "1px solid #e3c4c4", "#fbf1f1", "#f5e3e3"),
            "icon_light": ("transparent", MUTED, "none", CARD, "#e2ecec"),
        }
        bg, fg, border, hover, pressed = table.get(variant, ("#ffffff", INK, f"1px solid {LINE}", CARD, "#e2ecec"))
        hover_border = "border-color: #bcd0d0;" if variant == "neutral" or variant not in table else ""
        return f"""
            {sel} {{
                background: {bg}; color: {fg}; border: {border}; border-radius: {r}px;
                padding: {padding}; font-size: {_fs(font_size)}pt; font-weight: {weight};
                font-family: '{UI}';
            }}
            {sel}:hover {{ background: {hover}; {hover_border} }}
            {sel}:pressed {{ background: {pressed}; }}
            {sel}:disabled {{ background: {CARD}; color: {FAINT}; border: 1px solid {LINE}; }}
        """

    def line_edit_qss(font_family: str = "", font_size: int = 11, sel: str = "QLineEdit") -> str:
        return f"""
            {sel} {{
                background-color: #ffffff; color: {INK};
                border: 1px solid {LINE}; border-radius: 8px;
                padding: 6px 10px; font-size: {_fs(font_size)}pt; font-family: '{UI}'; min-height: 1.8em;
                selection-background-color: {TEAL}; selection-color: #ffffff;
            }}
            {sel}:hover {{ border: 1px solid #bcd0d0; }}
            {sel}:focus {{ border: 1px solid {TEAL}; }}
            {sel}:disabled {{ background-color: {CARD}; color: {FAINT}; }}
            {sel}[readOnly="true"] {{ background-color: {CARD}; color: {MUTED}; }}
        """

    def combo_qss(font_family: str = "", arrow_url: str = "none", font_size: int = 10,
                  sel: str = "QComboBox") -> str:
        arrow = arrow_url if arrow_url and arrow_url != "none" else f"url('{icons['chev_down']}')"
        return f"""
            {sel} {{
                background-color: #ffffff; color: {INK};
                border: 1px solid {LINE}; border-radius: 8px;
                padding: 5px 10px; font-size: {_fs(font_size)}pt; font-family: '{UI}'; min-height: 2.4em;
            }}
            {sel}:hover {{ border-color: #bcd0d0; }}
            {sel}:focus, {sel}:on {{ border-color: {TEAL}; }}
            {sel}:disabled {{ background-color: {CARD}; color: {FAINT}; }}
            {sel}::drop-down {{
                subcontrol-origin: padding; subcontrol-position: center right;
                width: 26px; border: none;
            }}
            {sel}::down-arrow {{ image: {arrow}; width: 12px; height: 8px; }}
            {sel} QAbstractItemView {{
                background-color: #ffffff; color: {INK};
                border: 1px solid {LINE}; border-radius: 8px;
                padding: 4px; outline: 0px;
            }}
            {sel} QAbstractItemView::item {{
                padding: 7px 10px; min-height: 2.0em; border-radius: 6px; background-color: transparent;
            }}
            {sel} QAbstractItemView::item:selected {{ background-color: {TEAL_SOFT}; color: {DEEP}; }}
            {sel} QAbstractItemView::item:hover {{ background-color: {CARD}; color: {INK}; }}
        """

    def spinbox_qss(font_family: str = "", up_url: str = "none", down_url: str = "none",
                    font_size: int = 11, sel: str = "QSpinBox") -> str:
        up = up_url if up_url and up_url != "none" else f"url('{icons['chev_up']}')"
        dn = down_url if down_url and down_url != "none" else f"url('{icons['chev_small_down']}')"
        return f"""
            {sel}, QDoubleSpinBox {{
                background-color: #ffffff; color: {INK};
                border: 1px solid {LINE}; border-radius: 8px;
                padding: 5px 8px; font-size: {_fs(font_size)}pt; font-family: '{UI}'; min-height: 1.8em;
                selection-background-color: {TEAL}; selection-color: #ffffff;
            }}
            {sel}:hover, QDoubleSpinBox:hover {{ border-color: #bcd0d0; }}
            {sel}:focus, QDoubleSpinBox:focus {{ border-color: {TEAL}; }}
            {sel}:disabled, QDoubleSpinBox:disabled {{ background-color: {CARD}; color: {FAINT}; }}
            {sel}::up-button, QDoubleSpinBox::up-button {{
                subcontrol-origin: border; subcontrol-position: top right;
                width: 22px; border: none; background: transparent;
            }}
            {sel}::down-button, QDoubleSpinBox::down-button {{
                subcontrol-origin: border; subcontrol-position: bottom right;
                width: 22px; border: none; background: transparent;
            }}
            {sel}::up-button:hover, QDoubleSpinBox::up-button:hover,
            {sel}::down-button:hover, QDoubleSpinBox::down-button:hover {{ background: {CARD}; }}
            {sel}::up-arrow, QDoubleSpinBox::up-arrow {{ image: {up}; width: 10px; height: 6px; }}
            {sel}::down-arrow, QDoubleSpinBox::down-arrow {{ image: {dn}; width: 10px; height: 6px; }}
        """

    def groupbox_qss(font_family: str = "", title_size: int = 15, sel: str = "QGroupBox") -> str:
        return f"""
            {sel} {{
                font-weight: bold; font-size: {_fs(title_size, 10.5, 11.5)}pt; font-family: '{UI}';
                color: {DEEP};
                border: 1px solid {LINE}; border-radius: 12px;
                margin-top: 14px; background-color: #ffffff;
            }}
            {sel}::title {{
                subcontrol-origin: margin; subcontrol-position: top left;
                left: 14px; padding: 0px 6px; color: {DEEP};
                font-weight: bold; font-family: '{UI}';
            }}
        """

    def scrollbar_qss() -> str:
        return """
            QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
            QScrollBar::handle:vertical { background: #c9d9d9; border-radius: 3px; min-height: 30px; }
            QScrollBar::handle:vertical:hover { background: #a9c1c1; }
            QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
            QScrollBar::handle:horizontal { background: #c9d9d9; border-radius: 3px; min-width: 30px; }
            QScrollBar::handle:horizontal:hover { background: #a9c1c1; }
            QScrollBar::add-line, QScrollBar::sub-line { height: 0px; width: 0px; }
            QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
        """

    def progress_qss(sel: str = "QProgressBar") -> str:
        return f"""
            {sel} {{
                border: none; border-radius: 3px; text-align: center;
                background: #dbe8e8; height: 6px; color: {INK};
            }}
            {sel}::chunk {{ background: {TEAL}; border-radius: 3px; }}
        """

    def log_qss(font_family: str = "", font_size: int = 11, sel: str = "QTextEdit") -> str:
        return f"""
            {sel} {{
                background-color: #ffffff; border: 1px solid {LINE};
                border-radius: 10px; color: {INK}; font-size: {_fs(font_size)}pt; font-family: '{UI}';
                selection-background-color: {TEAL}; selection-color: #ffffff;
            }}
        """

    def dialog_container_qss(object_name: str) -> str:
        return f"""
            QWidget#{object_name} {{
                background-color: {PAPER};
                border-radius: 16px;
                border: 1px solid #c4d6d6;
            }}
        """

    def checkbox_qss(check_url: str = "none", sel: str = "QCheckBox",
                     font_family: str = "", font_size: int = 0) -> str:
        size = f"font-size: {_fs(font_size)}pt;" if font_size else ""
        return f"""
            {sel} {{ color: {INK}; background: transparent; spacing: 10px; font-family: '{UI}'; {size} }}
            {sel}:disabled {{ color: {FAINT}; }}
            {sel}::indicator {{ width: 40px; height: 24px; image: url("{toggles['toggle_off']}"); }}
            {sel}::indicator:checked {{ image: url("{toggles['toggle_on']}"); }}
            {sel}::indicator:disabled {{ image: url("{toggles['toggle_off_dis']}"); }}
            {sel}::indicator:checked:disabled {{ image: url("{toggles['toggle_on_dis']}"); }}
        """

    def radio_qss(sel: str = "QRadioButton", font_size: int = 0) -> str:
        size = f"font-size: {_fs(font_size)}pt;" if font_size else ""
        return f"""
            {sel} {{ color: {INK}; background: transparent; spacing: 8px; font-family: '{UI}'; {size} }}
            {sel}::indicator {{
                width: 16px; height: 16px; border-radius: 10px;
                border: 2px solid #9fb7b8; background: #ffffff;
            }}
            {sel}::indicator:hover {{ border-color: {TEAL}; }}
            {sel}::indicator:checked {{
                border-color: {TEAL};
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                    stop:0 {TEAL}, stop:0.5 {TEAL}, stop:0.6 #ffffff, stop:1 #ffffff);
            }}
            {sel}:disabled {{ color: {FAINT}; }}
        """

    def tooltip_qss() -> str:
        return f"""
            QToolTip {{
                background-color: {DEEP}; color: #ffffff;
                border: none; border-radius: 6px; padding: 5px 9px;
            }}
        """

    def slider_qss(with_disabled: bool = False) -> str:
        qss = f"""
            QSlider::groove:horizontal {{ border: none; background: #dbe8e8; height: 6px; border-radius: 3px; }}
            QSlider::sub-page:horizontal {{ background: {TEAL}; height: 6px; border-radius: 3px; }}
            QSlider::handle:horizontal {{
                background: #ffffff; border: 2px solid {TEAL};
                width: 14px; height: 14px; margin: -6px 0; border-radius: 9px;
            }}
            QSlider::handle:horizontal:hover {{ background: {TEAL_SOFT}; }}
        """
        if with_disabled:
            qss += f"""
            QSlider::groove:horizontal:disabled {{ background: {CARD}; }}
            QSlider::sub-page:horizontal:disabled {{ background: #c6d6d6; }}
            QSlider::handle:horizontal:disabled {{ background: #ffffff; border: 2px solid #c6d6d6; }}
            """
        return qss

    def label_font(point_size: int, bold: bool = True):
        if point_size >= 18:                    # 各对话框的大标题
            f = QFont(SERIF)
            f.setPointSizeF(16)
            f.setWeight(QFont.Weight.Black)
            return f
        f = QFont(UI)
        f.setPointSizeF(_fs(point_size, 10.5, 11.5))
        f.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
        return f

    def title_font():
        return label_font(20, True)

    def app_qss() -> str:
        return f"""
            QMessageBox {{ background-color: {PAPER}; }}
            QMessageBox QLabel {{ color: {INK}; font-family: '{UI}'; font-size: 10.5pt; background: transparent; }}
            QMessageBox QPushButton {{
                background: #ffffff; color: {INK}; border: 1px solid {LINE}; border-radius: 8px;
                padding: 6px 18px; min-width: 64px; font-family: '{UI}'; font-size: 10.5pt;
            }}
            QMessageBox QPushButton:hover {{ background: {CARD}; }}
            QMessageBox QPushButton:default {{ background: {TEAL}; color: #ffffff; border: none; }}
            QMenu {{ background: #ffffff; border: 1px solid {LINE}; border-radius: 8px; padding: 4px; color: {INK}; }}
            QMenu::item {{ padding: 6px 16px; border-radius: 6px; }}
            QMenu::item:selected {{ background: {TEAL_SOFT}; color: {DEEP}; }}
        """ + tooltip_qss()

    return {
        "qss_url": qss_url, "button_qss": button_qss, "line_edit_qss": line_edit_qss,
        "combo_qss": combo_qss, "spinbox_qss": spinbox_qss, "groupbox_qss": groupbox_qss,
        "scrollbar_qss": scrollbar_qss, "progress_qss": progress_qss, "log_qss": log_qss,
        "dialog_container_qss": dialog_container_qss, "checkbox_qss": checkbox_qss,
        "radio_qss": radio_qss, "tooltip_qss": tooltip_qss, "slider_qss": slider_qss,
        "label_font": label_font, "title_font": title_font, "app_qss": app_qss,
    }


def install_into_legacy_theme(legacy) -> bool:
    """把新主题写进项目原有的 ui.theme 模块（只在新界面构建成功后调用一次）。

    旧界面 / 新界面构建失败回退时都不会走到这里，所以原主题不需要还原。"""
    global _INSTALLED
    from PyQt6.QtWidgets import QApplication
    if _INSTALLED:
        return True
    fonts = resolve_fonts()
    values = _palette(fonts)
    values.update(_make_builders(fonts, ensure_assets(), ensure_icons(), getattr(legacy, "qss_url")))
    missing = [k for k in dir(legacy) if k.isupper() and k not in values]
    if missing:
        print(f"[治幕新界面] 这些旧主题颜色没有对应的新值，保持原样: {missing}")
    for k, v in values.items():
        setattr(legacy, k, v)
    app = QApplication.instance()
    if app is not None:
        f = QFont(fonts["ui"])
        f.setPointSizeF(10.5)
        app.setFont(f)
        app.setStyleSheet((app.styleSheet() or "") + values["app_qss"]())
    _INSTALLED = True
    return True
