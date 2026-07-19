# -*- coding: utf-8 -*-
"""
styles.py
---------
集中管理整個軟體的「視覺設計系統」：色彩 token、字型、圓角、間距，
以及組合出完整的 QSS（Qt Style Sheet）字串。

設計理念：
    這是一個「計算檔案指紋、找出重複檔案」的工具，所以配色刻意選用
    沉穩、精確、帶點科技感的「墨綠 / 藍綠 (teal)」作為主色調，避免落入
    常見 AI 生成介面的老套配色（例如：暖色米白+赤陶色、或純黑+螢光綠）。

    「刪除」是這個工具唯一具破壞性的動作，因此危險色（紅色）被嚴格保留
    只用在刪除按鈕與警告訊息上，其餘地方完全不使用紅色，讓使用者一看到
    紅色就直覺知道「這是要刪除東西」。

    每個「重複檔案群組」會使用整列底色區分。十種底色循環使用，
    第 11 組會重新使用第 1 組的底色；不屬於任何群組的檔案則使用
    中性的白色／灰色（深色模式為兩種深灰色）交替顯示。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

# --------------------------------------------------------------------------
# 色彩 Token
# --------------------------------------------------------------------------

LIGHT_TOKENS: Dict[str, str] = {
    "bg": "#F7F9F9",
    "surface": "#FFFFFF",
    "surface_alt": "#F1F5F4",
    "surface_hover": "#EAF2F1",
    "border": "#DCE3E2",
    "border_strong": "#B9C6C4",
    "text_primary": "#122622",
    "text_secondary": "#5B6B68",
    "text_disabled": "#A7B4B2",
    "accent": "#0F766E",
    "accent_hover": "#0B5D56",
    "accent_pressed": "#0A4E48",
    "accent_soft": "#DCF4F1",
    "accent_text_on": "#FFFFFF",
    "danger": "#D7402A",
    "danger_hover": "#B7331F",
    "danger_soft": "#FBE4E0",
    "danger_text_on": "#FFFFFF",
    "success": "#1E8E5A",
    "success_soft": "#DEF3E7",
    "warning": "#B7791F",
    "warning_soft": "#FBF0DB",
    "shadow_border": "#CBD5D4",
    "spin_button": "#D6E0DE",
    "spin_button_hover": "#C3D0CE",
    "spin_button_pressed": "#AEBFBC",
    "spin_button_border": "#9EAFAC",
    # Selected rows use one unified color that is deliberately darker than
    # every pastel duplicate-group background.
    "table_selection_bg": "#365F73",
    "table_selection_text": "#FFFFFF",
    "table_selection_border": "#274553",
}

DARK_TOKENS: Dict[str, str] = {
    "bg": "#0E1716",
    "surface": "#16211F",
    "surface_alt": "#1D2A28",
    "surface_hover": "#243330",
    "border": "#2B3937",
    "border_strong": "#3C4C49",
    "text_primary": "#EAF2F0",
    "text_secondary": "#93A6A2",
    "text_disabled": "#4B5C59",
    "accent": "#33C9BB",
    "accent_hover": "#5AD7CB",
    "accent_pressed": "#22B2A4",
    "accent_soft": "#1C3B37",
    "accent_text_on": "#06201D",
    "danger": "#E8664F",
    "danger_hover": "#EF8571",
    "danger_soft": "#3A211D",
    "danger_text_on": "#2A0D07",
    "success": "#4ED08E",
    "success_soft": "#153A29",
    "warning": "#E3B152",
    "warning_soft": "#3A2E12",
    "shadow_border": "#0A1211",
    "spin_button": "#3B4D49",
    "spin_button_hover": "#4D625E",
    "spin_button_pressed": "#2F403D",
    "spin_button_border": "#667D78",
    # A brighter cool blue remains clearly visible against all dark group
    # backgrounds without resembling the ten-color group palette.
    "table_selection_bg": "#3D7EA6",
    "table_selection_text": "#FFFFFF",
    "table_selection_border": "#82C7F0",
}

# 重複檔案整列底色的 10 色循環色盤：(背景色, 文字色)。
# 深色模式使用對應的深色底／淺色字組合。
_GROUP_PALETTE_LIGHT = [
    # The foreground deliberately stays neutral. Group identity is communicated
    # by the row background, not by changing the text color.
    ("#C8F0E9", "#122622"),  # teal
    ("#D4E6FF", "#122622"),  # blue
    ("#E4D9FF", "#122622"),  # violet
    ("#FFE4A8", "#122622"),  # amber
    ("#FFD2DC", "#122622"),  # rose
    ("#CDEBD8", "#122622"),  # emerald
    ("#D5DAFF", "#122622"),  # indigo
    ("#FFD9BB", "#122622"),  # orange
    ("#EACFF4", "#122622"),  # purple
    ("#D8E9C7", "#122622"),  # lime
]

_GROUP_PALETTE_DARK = [
    # Dark-mode text also remains neutral and readable across every group.
    ("#174B45", "#EAF2F0"),  # teal
    ("#244467", "#EAF2F0"),  # blue
    ("#44376A", "#EAF2F0"),  # violet
    ("#5A431D", "#EAF2F0"),  # amber
    ("#5D303B", "#EAF2F0"),  # rose
    ("#24503A", "#EAF2F0"),  # emerald
    ("#373E68", "#EAF2F0"),  # indigo
    ("#5B3923", "#EAF2F0"),  # orange
    ("#51345B", "#EAF2F0"),  # purple
    ("#3B512B", "#EAF2F0"),  # lime
]

_UNGROUPED_ROWS_LIGHT = [
    ("#FFFFFF", "#122622"),
    ("#E5EAE9", "#122622"),
]

_UNGROUPED_ROWS_DARK = [
    ("#121B1A", "#EAF2F0"),
    ("#25302E", "#EAF2F0"),
]


FONT_FAMILY_UI = (
    '"Microsoft JhengHei UI", "Segoe UI", "PingFang TC", "Noto Sans CJK TC", '
    '"Helvetica Neue", Arial, sans-serif'
)
FONT_FAMILY_MONO = 'Consolas, "Cascadia Mono", "SF Mono", Menlo, "Courier New", monospace'

RADIUS = "8px"
RADIUS_SM = "5px"
RADIUS_LG = "12px"


def get_tokens(theme: str) -> Dict[str, str]:
    return DARK_TOKENS if theme == "dark" else LIGHT_TOKENS


def get_group_color(theme: str, group_index: int) -> Tuple[str, str]:
    """Return the row background/text colors for a duplicate group."""
    palette = _GROUP_PALETTE_DARK if theme == "dark" else _GROUP_PALETTE_LIGHT
    return palette[(max(1, group_index) - 1) % len(palette)]


def get_ungrouped_row_color(theme: str, alternate_index: int) -> Tuple[str, str]:
    """Return neutral alternating row colors for files outside duplicate groups."""
    palette = _UNGROUPED_ROWS_DARK if theme == "dark" else _UNGROUPED_ROWS_LIGHT
    return palette[max(0, alternate_index) % len(palette)]


def build_stylesheet(theme: str = "light", assets_dir: str | Path | None = None) -> str:
    """組合出完整的 QSS 字串。使用 $TOKEN$ 樣板 + 字串取代，避免跟 QSS
    本身大量的花括號 {} 產生 Python f-string 逸出字元衝突。"""
    tk = get_tokens(theme)
    asset_root = Path(assets_dir) if assets_dir is not None else Path()
    icon_suffix = "dark" if theme == "dark" else "light"
    spin_up_icon = (asset_root / f"spin_up_{icon_suffix}.svg").resolve().as_posix() if assets_dir is not None else ""
    spin_down_icon = (asset_root / f"spin_down_{icon_suffix}.svg").resolve().as_posix() if assets_dir is not None else ""

    template = """
    * {
        font-family: $FONT_UI$;
        font-size: 13px;
        color: $text_primary$;
        outline: none;
    }

    QMainWindow, QDialog {
        background-color: $bg$;
    }

    QWidget#centralWidget {
        background-color: $bg$;
    }

    /* ---------- 卡片容器 ---------- */
    QFrame[class="card"] {
        background-color: $surface$;
        border: 1px solid $border$;
        border-radius: 10px;
    }

    QFrame[class="statCard"] {
        background-color: $surface$;
        border: 1px solid $border$;
        border-radius: 10px;
    }
    QLabel[class="statValue"] {
        font-size: 20px;
        font-weight: 700;
        color: $text_primary$;
    }
    QLabel[class="statLabel"] {
        font-size: 11px;
        color: $text_secondary$;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    QLabel[class="statValueDanger"] {
        font-size: 20px;
        font-weight: 700;
        color: $danger$;
    }

    /* ---------- 拖放區 ---------- */
    QFrame#dropZone {
        background-color: $surface$;
        border: 2px dashed $border_strong$;
        border-radius: 12px;
    }
    QFrame#dropZone[dragActive="true"] {
        background-color: $accent_soft$;
        border: 2px dashed $accent$;
    }
    QLabel#dropZoneTitle {
        font-size: 15px;
        font-weight: 700;
        color: $text_primary$;
    }
    QLabel#dropZoneSubtitle {
        font-size: 12px;
        color: $text_secondary$;
    }
    QLabel#dropZoneIcon {
        font-size: 30px;
    }

    /* ---------- 按鈕 ---------- */
    QPushButton {
        background-color: $surface$;
        border: 1px solid $border_strong$;
        border-radius: $RADIUS$;
        padding: 7px 14px;
        font-weight: 600;
        color: $text_primary$;
    }
    QPushButton:hover {
        background-color: $surface_hover$;
        border-color: $border_strong$;
    }
    QPushButton:pressed {
        background-color: $surface_alt$;
    }
    QPushButton:disabled {
        color: $text_disabled$;
        background-color: $surface$;
        border-color: $border$;
    }

    QPushButton[class="primary"] {
        background-color: $accent$;
        border: 1px solid $accent$;
        color: $accent_text_on$;
    }
    QPushButton[class="primary"]:hover {
        background-color: $accent_hover$;
        border-color: $accent_hover$;
    }
    QPushButton[class="primary"]:pressed {
        background-color: $accent_pressed$;
        border-color: $accent_pressed$;
    }
    QPushButton[class="primary"]:disabled {
        background-color: $surface_alt$;
        border-color: $border$;
        color: $text_disabled$;
    }

    QPushButton[class="danger"] {
        background-color: $danger$;
        border: 1px solid $danger$;
        color: $danger_text_on$;
    }
    QPushButton[class="danger"]:hover {
        background-color: $danger_hover$;
        border-color: $danger_hover$;
    }
    QPushButton[class="danger"]:disabled {
        background-color: $surface_alt$;
        border-color: $border$;
        color: $text_disabled$;
    }

    QPushButton[class="flat"] {
        background-color: transparent;
        border: none;
        color: $accent$;
        padding: 4px 6px;
        font-weight: 600;
        text-align: left;
    }
    QPushButton[class="flat"]:hover {
        color: $accent_hover$;
        text-decoration: underline;
    }

    /* ---------- 輸入元件 ---------- */
    QLineEdit, QComboBox, QSpinBox {
        background-color: $surface$;
        border: 1px solid $border_strong$;
        border-radius: $RADIUS$;
        padding: 6px 10px;
        color: $text_primary$;
        selection-background-color: $accent$;
        selection-color: $accent_text_on$;
    }
    QSpinBox {
        padding-right: 28px;
    }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
        border: 1px solid $accent$;
    }
    QComboBox::drop-down {
        border: none;
        width: 22px;
    }
    QComboBox QAbstractItemView {
        background-color: $surface$;
        border: 1px solid $border$;
        selection-background-color: $accent_soft$;
        selection-color: $accent$;
        outline: none;
    }

    QSpinBox::up-button, QSpinBox::down-button {
        subcontrol-origin: border;
        width: 22px;
        background-color: $spin_button$;
        border-left: 1px solid $spin_button_border$;
    }
    QSpinBox::up-button {
        subcontrol-position: top right;
        border-top-right-radius: $RADIUS$;
        border-bottom: 1px solid $spin_button_border$;
    }
    QSpinBox::down-button {
        subcontrol-position: bottom right;
        border-bottom-right-radius: $RADIUS$;
        border-top: 1px solid $spin_button_border$;
    }
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {
        background-color: $spin_button_hover$;
    }
    QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {
        background-color: $spin_button_pressed$;
    }
    QSpinBox::up-arrow {
        image: url("$SPIN_UP_ICON$");
        width: 9px;
        height: 6px;
    }
    QSpinBox::down-arrow {
        image: url("$SPIN_DOWN_ICON$");
        width: 9px;
        height: 6px;
    }

    QCheckBox {
        spacing: 8px;
        color: $text_primary$;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1.5px solid $border_strong$;
        background-color: $surface$;
    }
    QCheckBox::indicator:checked {
        background-color: $accent$;
        border-color: $accent$;
    }
    QCheckBox::indicator:disabled {
        border-color: $border$;
    }

    /* ---------- 表格 ---------- */
    QTableWidget {
        background-color: $surface$;
        alternate-background-color: $surface_alt$;
        border: 1px solid $border$;
        border-radius: 10px;
        gridline-color: $border$;
        selection-background-color: $accent_soft$;
        selection-color: $text_primary$;
    }
    QTableWidget::item {
        padding: 5px 8px;
        border: none;
    }
    QTableWidget::item:selected {
        background-color: $accent_soft$;
        color: $text_primary$;
    }
    QHeaderView::section {
        background-color: $surface$;
        color: $text_secondary$;
        font-weight: 700;
        padding: 8px;
        border: none;
        border-bottom: 2px solid $border$;
        border-right: 1px solid $border$;
    }
    QTableCornerButton::section {
        background-color: $surface$;
        border: none;
        border-bottom: 2px solid $border$;
    }

    /* ---------- 捲軸 ---------- */
    QScrollBar:vertical {
        background: transparent;
        width: 11px;
        margin: 2px;
    }
    QScrollBar::handle:vertical {
        background: $border_strong$;
        border-radius: 5px;
        min-height: 24px;
    }
    QScrollBar::handle:vertical:hover {
        background: $text_disabled$;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar:horizontal {
        background: transparent;
        height: 11px;
        margin: 2px;
    }
    QScrollBar::handle:horizontal {
        background: $border_strong$;
        border-radius: 5px;
        min-width: 24px;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }

    /* ---------- 進度條 ---------- */
    QProgressBar {
        background-color: $surface_alt$;
        border: none;
        border-radius: 6px;
        height: 10px;
        text-align: center;
        color: transparent;
    }
    QProgressBar::chunk {
        background-color: $accent$;
        border-radius: 6px;
    }

    /* ---------- 選單 / 狀態列 ---------- */
    QMenuBar {
        background-color: $bg$;
        border-bottom: 1px solid $border$;
        padding: 2px;
    }
    QMenuBar::item {
        padding: 6px 10px;
        border-radius: $RADIUS_SM$;
        background: transparent;
    }
    QMenuBar::item:selected {
        background-color: $surface_hover$;
    }
    QMenu {
        background-color: $surface$;
        border: 1px solid $border$;
        border-radius: 8px;
        padding: 4px;
    }
    QMenu::item {
        padding: 7px 24px 7px 12px;
        border-radius: $RADIUS_SM$;
    }
    QMenu::item:selected {
        background-color: $accent_soft$;
        color: $text_primary$;
    }
    QMenu::separator {
        height: 1px;
        background: $border$;
        margin: 4px 6px;
    }

    QStatusBar {
        background-color: $bg$;
        border-top: 1px solid $border$;
        color: $text_secondary$;
    }

    QLabel[class="sectionTitle"] {
        font-size: 13px;
        font-weight: 700;
        color: $text_primary$;
    }
    QLabel[class="muted"] {
        color: $text_secondary$;
    }
    QLabel[class="hint"] {
        color: $text_secondary$;
        font-size: 11px;
    }

    QToolTip {
        background-color: $text_primary$;
        color: $surface$;
        border: none;
        padding: 6px 8px;
        border-radius: 6px;
    }

    QSplitter::handle {
        background-color: $border$;
    }
    """

    css = template
    for key, value in tk.items():
        css = css.replace(f"${key}$", value)
    css = css.replace("$SPIN_UP_ICON$", spin_up_icon)
    css = css.replace("$SPIN_DOWN_ICON$", spin_down_icon)
    css = css.replace("$FONT_UI$", FONT_FAMILY_UI)
    css = css.replace("$RADIUS_SM$", RADIUS_SM)
    css = css.replace("$RADIUS_LG$", RADIUS_LG)
    css = css.replace("$RADIUS$", RADIUS)
    return css

# Extra HashSieve table/scrollbar polish is included in build_stylesheet by replacement below.
