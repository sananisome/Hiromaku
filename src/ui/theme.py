"""
应用全局主题：调色板与 QSS 片段的唯一来源。

所有界面颜色集中在这里，各窗口/对话框通过构建函数取片段，
不要再在业务代码里硬编码色值。
"""

import os
from PyQt6.QtGui import QColor

from utils.file_utils import resource_path

# ---------- 调色板 ----------
ACCENT          = "#F0A4B8"   # 樱花粉：主按钮 / 聚焦边框 / 组标题
ACCENT_HOVER    = "#F5B7C6"
ACCENT_PRESSED  = "#E393A8"
ON_ACCENT       = "#3A2530"   # 粉色底上的文字

TEXT_PRIMARY    = "#EEF0F6"
TEXT_SECONDARY  = "#AAB0C0"

PANEL_BG        = "rgba(22, 25, 35, 185)"
PANEL_BORDER    = "rgba(255, 255, 255, 26)"

INPUT_BG        = "rgba(255, 255, 255, 16)"
INPUT_BG_HOVER  = "rgba(255, 255, 255, 24)"
INPUT_BG_FOCUS  = "rgba(255, 255, 255, 32)"
INPUT_BORDER    = "rgba(255, 255, 255, 30)"

BTN_NEUTRAL_BG      = "rgba(255, 255, 255, 32)"
BTN_NEUTRAL_HOVER   = "rgba(255, 255, 255, 48)"
BTN_NEUTRAL_PRESSED = "rgba(255, 255, 255, 22)"
BTN_NEUTRAL_BORDER  = "rgba(255, 255, 255, 42)"

# 浅色圆钮（顶部图标按钮：图标本身是深色线稿，需要浅底）
BTN_ICON_LIGHT_BG      = "rgba(233, 238, 247, 195)"
BTN_ICON_LIGHT_HOVER   = "rgba(246, 249, 255, 230)"
BTN_ICON_LIGHT_PRESSED = "rgba(212, 219, 232, 235)"
ON_ICON_LIGHT          = "#2A2F3A"

SUCCESS         = "#7FC8A9"   # 薄荷绿：云端获取 / 确认
SUCCESS_HOVER   = "#93D6BA"
SUCCESS_PRESSED = "#6AB495"
ON_SUCCESS      = "#17332B"

DANGER          = "#E8827C"   # 柔红：关闭 / 停止 / 取消
DANGER_HOVER    = "#F0968F"
DANGER_PRESSED  = "#D96F68"
ON_DANGER       = "#3B1E1C"

BTN_DISABLED_BG     = "rgba(255, 255, 255, 10)"
BTN_DISABLED_TEXT   = "rgba(255, 255, 255, 70)"

POPUP_BG        = "rgba(28, 31, 42, 245)"
POPUP_BORDER    = "rgba(255, 255, 255, 30)"
POPUP_SELECTION = "rgba(240, 164, 184, 90)"
POPUP_HOVER     = "rgba(255, 255, 255, 18)"

LOG_BG          = "rgba(10, 12, 18, 140)"
LOG_TEXT        = "#DDE3EE"

DIALOG_BG       = "rgba(22, 25, 35, 235)"
DIALOG_BORDER   = "rgba(255, 255, 255, 24)"

PROGRESS_CHUNK_A = "#F0A4B8"
PROGRESS_CHUNK_B = "#B49BE0"

# 背景图上叠加的暗化渐变（让面板文字在任意背景图上都可读）
SCRIM_TOP       = QColor(10, 13, 20, 45)
SCRIM_BOTTOM    = QColor(10, 13, 20, 115)

# 描边标签（CustomLabel 系列）默认色
LABEL_MAIN      = QColor(238, 240, 246)
LABEL_STROKE    = QColor(0, 0, 0, 120)
TITLE_MAIN      = QColor(245, 247, 250)
TITLE_STROKE    = QColor(10, 13, 20, 170)

CHECKBOX_BORDER = "#F0A4B8"

# ---------- 原先散落在各对话框里的字面量（收进来，换主题时一起换） ----------
ON_SELECTION            = "#FFFFFF"                    # 列表/下拉选中项文字
LIST_HOVER              = "rgba(255, 255, 255, 18)"    # 列表项悬停
SELECTION_BG            = "rgba(240, 164, 184, 150)"   # 文本选区
TEXT_FOCUS_BG           = "rgba(16, 19, 28, 200)"      # 多行输入框聚焦底色
TEXT_FOCUS_BG_STRONG    = "rgba(16, 19, 28, 220)"      # 编辑弹窗的多行输入框聚焦底色
HINT_TEXT               = "rgba(238, 240, 246, 200)"   # 次要提示文字
SEPARATOR               = "rgba(255, 255, 255, 55)"    # 分隔线
SPLITTER                = "rgba(255, 255, 255, 40)"    # QSplitter 把手
INPUT_DISABLED_BG       = "rgba(255, 255, 255, 8)"     # 置灰输入框
INPUT_DISABLED_BORDER   = "rgba(255, 255, 255, 18)"
TEXT_LOCKED_BG          = "rgba(255, 255, 255, 10)"    # 已锁定（只读）的多行文本
ERROR_SOFT_BG           = "rgba(232, 130, 124, 30)"    # 出错的输入框
ERROR_SOFT_TEXT         = "rgba(255, 205, 200, 220)"
ERROR_SOFT_BORDER       = "rgba(232, 130, 124, 120)"
PROFILE_CURRENT_BG      = QColor(240, 164, 184, 90)    # LLM 列表里「当前使用」的配置

SLIDER_GROOVE                 = "rgba(255, 255, 255, 40)"
SLIDER_GROOVE_DISABLED        = "rgba(255, 255, 255, 18)"
SLIDER_SUBPAGE_DISABLED       = "rgba(255, 255, 255, 30)"
SLIDER_HANDLE                 = ACCENT
SLIDER_HANDLE_BORDER          = ACCENT_HOVER
SLIDER_HANDLE_DISABLED        = "rgba(255, 255, 255, 60)"
SLIDER_HANDLE_DISABLED_BORDER = "rgba(255, 255, 255, 30)"

# 对话框右上角关闭按钮
CLOSE_BG        = DANGER
CLOSE_FG        = ON_DANGER
CLOSE_HOVER_BG  = DANGER_HOVER
CLOSE_HOVER_FG  = ON_DANGER

# 主窗口拖拽遮罩
OVERLAY_SCRIM   = "rgba(10, 12, 18, 170)"
OVERLAY_AREA_BG = "rgba(22, 25, 35, 220)"
OVERLAY_BORDER  = ACCENT
OVERLAY_TEXT    = TEXT_PRIMARY


def label_font(point_size: int, bold: bool = True):
    """对话框标签字体：应用默认字体族 + 指定字号（各对话框的 _label_font 都走这里）。"""
    from PyQt6.QtGui import QFont
    font = QFont()
    font.setPointSize(point_size)
    font.setBold(bold)
    return font


def title_font():
    """对话框标题字体。"""
    return label_font(20, True)


def slider_qss(with_disabled: bool = False) -> str:
    """水平滑块（SRT 参数 / LLM 温度、思考模式）。"""
    qss = f"""
        QSlider::groove:horizontal {{
            border: none; background: {SLIDER_GROOVE};
            height: 8px; border-radius: 4px;
        }}
        QSlider::sub-page:horizontal {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {PROGRESS_CHUNK_A}, stop:1 {PROGRESS_CHUNK_B});
            height: 8px; border-radius: 4px;
        }}
        QSlider::handle:horizontal {{
            background: {SLIDER_HANDLE}; border: 2px solid {SLIDER_HANDLE_BORDER};
            width: 16px; height: 16px; margin: -6px 0; border-radius: 10px;
        }}
    """
    if with_disabled:
        qss += f"""
        QSlider::groove:horizontal:disabled {{ background: {SLIDER_GROOVE_DISABLED}; }}
        QSlider::handle:horizontal:disabled {{
            background: {SLIDER_HANDLE_DISABLED};
            border: 2px solid {SLIDER_HANDLE_DISABLED_BORDER};
        }}
        QSlider::sub-page:horizontal:disabled {{ background: {SLIDER_SUBPAGE_DISABLED}; }}
        """
    return qss


def app_qss() -> str:
    """应用级补充样式（弹出的 QMessageBox 等）。旧主题不需要，返回空串。"""
    return ""


def qss_url(filename: str) -> str:
    """把 assets 里的图片转成 QSS url()，找不到时返回 none。"""
    path = resource_path(filename)
    if path and os.path.exists(path):
        return "url('" + os.path.abspath(path).replace(os.sep, '/') + "')"
    return "none"


def button_qss(variant: str = "neutral", *, sel: str = "QPushButton",
               font_family: str = "", font_size: int = 10,
               padding: str = "6px 15px", radius: int = 6, bold: bool = True) -> str:
    """按钮样式。variant: primary(粉) / success(薄荷) / danger(红) / neutral(半透明)。"""
    weight = "bold" if bold else "normal"
    family = f"font-family: '{font_family}';" if font_family else ""
    if variant == "primary":
        bg = (f"background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
              f"stop:0 {ACCENT_HOVER}, stop:1 {ACCENT});")
        hover = f"background: {ACCENT_HOVER};"
        pressed = f"background: {ACCENT_PRESSED};"
        color = ON_ACCENT
        border = f"border: 1px solid rgba(240, 164, 184, 110);"
    elif variant == "success":
        bg = (f"background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
              f"stop:0 {SUCCESS_HOVER}, stop:1 {SUCCESS});")
        hover = f"background: {SUCCESS_HOVER};"
        pressed = f"background: {SUCCESS_PRESSED};"
        color = ON_SUCCESS
        border = f"border: 1px solid rgba(127, 200, 169, 110);"
    elif variant == "danger":
        bg = (f"background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
              f"stop:0 {DANGER_HOVER}, stop:1 {DANGER});")
        hover = f"background: {DANGER_HOVER};"
        pressed = f"background: {DANGER_PRESSED};"
        color = ON_DANGER
        border = f"border: 1px solid rgba(232, 130, 124, 110);"
    elif variant == "icon_light":
        bg = f"background-color: {BTN_ICON_LIGHT_BG};"
        hover = f"background-color: {BTN_ICON_LIGHT_HOVER};"
        pressed = f"background-color: {BTN_ICON_LIGHT_PRESSED};"
        color = ON_ICON_LIGHT
        border = "border: none;"
    else:
        bg = f"background-color: {BTN_NEUTRAL_BG};"
        hover = f"background-color: {BTN_NEUTRAL_HOVER};"
        pressed = f"background-color: {BTN_NEUTRAL_PRESSED};"
        color = TEXT_PRIMARY
        border = f"border: 1px solid {BTN_NEUTRAL_BORDER};"
    return f"""
        {sel} {{
            {bg} color: {color}; {border} border-radius: {radius}px;
            padding: {padding}; font-size: {font_size}pt; font-weight: {weight}; {family}
        }}
        {sel}:hover {{ {hover} }}
        {sel}:pressed {{ {pressed} }}
        {sel}:disabled {{ background: {BTN_DISABLED_BG}; color: {BTN_DISABLED_TEXT}; border: 1px solid {BTN_NEUTRAL_BORDER}; }}
    """


def line_edit_qss(font_family: str = "", font_size: int = 11, sel: str = "QLineEdit") -> str:
    family = f"font-family: '{font_family}';" if font_family else ""
    return f"""
        {sel} {{
            background-color: {INPUT_BG}; color: {TEXT_PRIMARY};
            border: 1px solid {INPUT_BORDER}; border-radius: 5px;
            padding: 6px; font-size: {font_size}pt; {family} min-height: 1.8em;
        }}
        {sel}:hover {{ background-color: {INPUT_BG_HOVER}; border: 1px solid {ACCENT}; }}
        {sel}:focus {{ background-color: {INPUT_BG_FOCUS}; border: 1px solid {ACCENT}; }}
        {sel}:disabled {{ background-color: rgba(255, 255, 255, 8); color: {BTN_DISABLED_TEXT}; }}
    """


def combo_qss(font_family: str = "", arrow_url: str = "none", font_size: int = 10,
              sel: str = "QComboBox") -> str:
    family = f"font-family: '{font_family}';" if font_family else ""
    return f"""
        {sel} {{
            background-color: {INPUT_BG}; color: {TEXT_PRIMARY};
            border: 1px solid {INPUT_BORDER}; border-radius: 5px;
            padding: 5px 8px; font-size: {font_size}pt; {family} min-height: 2.8em;
        }}
        {sel}:hover {{ background-color: {INPUT_BG_HOVER}; border-color: {ACCENT}; }}
        {sel}:focus, {sel}:on {{ background-color: {INPUT_BG_FOCUS}; border-color: {ACCENT}; }}
        {sel}:disabled {{ background-color: rgba(255, 255, 255, 8); color: {BTN_DISABLED_TEXT}; }}
        {sel}::drop-down {{
            subcontrol-origin: padding; subcontrol-position: center right;
            width: 22px; border: none;
        }}
        {sel}::down-arrow {{ image: {arrow_url}; width: 9px; height: 9px; }}
        {sel} QAbstractItemView {{
            background-color: {POPUP_BG}; color: {TEXT_PRIMARY};
            border: 1px solid {POPUP_BORDER}; border-radius: 5px;
            padding: 4px; outline: 0px;
        }}
        {sel} QAbstractItemView::item {{
            padding: 8px 10px; min-height: 2.2em; border-radius: 3px; background-color: transparent;
        }}
        {sel} QAbstractItemView::item:selected {{
            background-color: {POPUP_SELECTION}; color: #FFFFFF;
        }}
        {sel} QAbstractItemView::item:hover {{ background-color: {POPUP_HOVER}; color: {TEXT_PRIMARY}; }}
    """


def spinbox_qss(font_family: str = "", up_url: str = "none", down_url: str = "none",
                font_size: int = 11, sel: str = "QSpinBox") -> str:
    family = f"font-family: '{font_family}';" if font_family else ""
    return f"""
        {sel}, QDoubleSpinBox {{
            background-color: {INPUT_BG}; color: {TEXT_PRIMARY};
            border: 1px solid {INPUT_BORDER}; border-radius: 5px;
            padding: 5px 8px; font-size: {font_size}pt; {family} min-height: 1.8em;
        }}
        {sel}:hover, QDoubleSpinBox:hover {{ background-color: {INPUT_BG_HOVER}; border-color: {ACCENT}; }}
        {sel}:focus, QDoubleSpinBox:focus {{ background-color: {INPUT_BG_FOCUS}; border-color: {ACCENT}; }}
        {sel}::up-button, QDoubleSpinBox::up-button {{
            subcontrol-origin: border; subcontrol-position: top right;
            width: 20px; border: none; background: transparent;
        }}
        {sel}::down-button, QDoubleSpinBox::down-button {{
            subcontrol-origin: border; subcontrol-position: bottom right;
            width: 20px; border: none; background: transparent;
        }}
        {sel}::up-arrow, QDoubleSpinBox::up-arrow {{ image: {up_url}; width: 9px; height: 9px; }}
        {sel}::down-arrow, QDoubleSpinBox::down-arrow {{ image: {down_url}; width: 9px; height: 9px; }}
    """


def groupbox_qss(font_family: str = "", title_size: int = 15, sel: str = "QGroupBox") -> str:
    family = f"font-family: '{font_family}';" if font_family else ""
    return f"""
        {sel} {{
            font-weight: bold; font-size: {title_size}pt; {family}
            border: 1px solid {PANEL_BORDER}; border-radius: 8px;
            margin-top: 12px; background-color: {PANEL_BG};
        }}
        {sel}::title {{
            subcontrol-origin: margin; subcontrol-position: top left;
            left: 15px; padding: 2px 5px; color: {ACCENT};
            font-weight: bold; {family}
        }}
    """


def scrollbar_qss() -> str:
    return f"""
        QScrollBar:vertical {{
            background: transparent; width: 10px; margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: rgba(255, 255, 255, 45); border-radius: 5px; min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{ background: rgba(255, 255, 255, 75); }}
        QScrollBar:horizontal {{
            background: transparent; height: 10px; margin: 2px;
        }}
        QScrollBar::handle:horizontal {{
            background: rgba(255, 255, 255, 45); border-radius: 5px; min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{ background: rgba(255, 255, 255, 75); }}
        QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; width: 0px; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    """


def progress_qss(sel: str = "QProgressBar") -> str:
    return f"""
        {sel} {{
            border: 1px solid {PANEL_BORDER}; border-radius: 5px;
            text-align: center; background: {LOG_BG}; height: 22px;
            color: {TEXT_PRIMARY}; font-weight: bold;
        }}
        {sel}::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {PROGRESS_CHUNK_A}, stop:1 {PROGRESS_CHUNK_B});
            border-radius: 4px;
        }}
    """


def log_qss(font_family: str = "", font_size: int = 11, sel: str = "QTextEdit") -> str:
    family = f"font-family: '{font_family}';" if font_family else ""
    return f"""
        {sel} {{
            background-color: {LOG_BG}; border: 1px solid {PANEL_BORDER};
            border-radius: 5px; color: {LOG_TEXT}; font-size: {font_size}pt; {family}
        }}
    """


def dialog_container_qss(object_name: str) -> str:
    return f"""
        QWidget#{object_name} {{
            background-color: {DIALOG_BG};
            border-radius: 12px;
            border: 1px solid {DIALOG_BORDER};
        }}
    """


def checkbox_qss(check_url: str = "none", sel: str = "QCheckBox",
                 font_family: str = "", font_size: int = 0) -> str:
    family = f"font-family: '{font_family}';" if font_family else ""
    size = f"font-size: {font_size}pt;" if font_size else ""
    return f"""
        {sel} {{ color: {TEXT_PRIMARY}; background: transparent; spacing: 8px; {family} {size} }}
        {sel}::indicator {{
            width: 18px; height: 18px;
            border: 2px solid {CHECKBOX_BORDER}; border-radius: 4px;
            background-color: transparent;
        }}
        {sel}::indicator:checked {{
            background-image: {check_url};
            background-position: center; background-repeat: no-repeat;
            border-color: {CHECKBOX_BORDER};
        }}
        {sel}::indicator:hover {{ border-color: {ACCENT_HOVER}; }}
    """


def radio_qss(sel: str = "QRadioButton", font_size: int = 0) -> str:
    size = f"font-size: {font_size}pt;" if font_size else ""
    return f"""
        {sel} {{ color: {TEXT_PRIMARY}; background: transparent; {size} }}
        {sel}::indicator {{
            width: 18px; height: 18px; border-radius: 10px;
            border: 2px solid {CHECKBOX_BORDER}; background: transparent;
        }}
        {sel}::indicator:checked {{
            background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                stop:0 {ACCENT} stop:0.55 {ACCENT} stop:0.65 transparent);
            border-color: {ACCENT};
        }}
        {sel}::indicator:hover {{ border-color: {ACCENT_HOVER}; }}
        {sel}:disabled {{ color: {BTN_DISABLED_TEXT}; }}
    """


def tooltip_qss() -> str:
    return f"""
        QToolTip {{
            background-color: {POPUP_BG}; color: {TEXT_PRIMARY};
            border: 1px solid {POPUP_BORDER}; border-radius: 4px; padding: 4px 8px;
        }}
    """
