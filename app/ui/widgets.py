# -*- coding: utf-8 -*-
"""
widgets.py
----------
一些小型、可重複使用的自訂元件，讓 main_window.py 的版面配置程式碼
更簡潔。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPalette
from PySide6.QtWidgets import (
    QApplication, QFrame, QLabel, QStyle, QStyledItemDelegate,
    QStyleOptionViewItem, QTableWidgetItem, QVBoxLayout,
)

from .styles import get_tokens


# Custom model roles used by RowColorDelegate. Using explicit roles plus a
# delegate makes row backgrounds reliable even when the active Qt platform
# style or a QSS item selector would otherwise paint over QTableWidgetItem's
# BackgroundRole.
ROW_BACKGROUND_ROLE = int(Qt.UserRole) + 101
ROW_FOREGROUND_ROLE = int(Qt.UserRole) + 102


class RowColorDelegate(QStyledItemDelegate):
    """Paint stable row colors and a unified selection fill.

    Unselected rows use their duplicate-group background (or the neutral
    white/gray zebra background for files outside any group).  Selected rows
    temporarily use one theme-specific selection color across the whole row.
    When the selection is cleared, Qt repaints the row and the original stored
    group/zebra color becomes visible again automatically.

    The delegate suppresses the platform style's own selection painting so the
    result is identical on Windows light/dark themes and cannot be overridden by
    a QSS ``item:selected`` rule.
    """

    def __init__(self, theme_getter, parent=None):
        super().__init__(parent)
        self._theme_getter = theme_getter

    def paint(self, painter, option, index) -> None:  # noqa: N802 (Qt API)
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        theme = self._theme_getter() if callable(self._theme_getter) else str(self._theme_getter)
        tokens = get_tokens(theme)
        selected = bool(option.state & QStyle.State_Selected)

        stored_background = QColor(index.data(ROW_BACKGROUND_ROLE) or tokens["surface"])
        stored_foreground = QColor(index.data(ROW_FOREGROUND_ROLE) or tokens["text_primary"])

        # A selected row deliberately uses one unified fill.  Because the
        # original group/zebra colors remain stored in the model roles, simply
        # deselecting the row restores them on the next repaint.
        if selected:
            background = QColor(tokens["table_selection_bg"])
            foreground = QColor(tokens["table_selection_text"])
        else:
            background = stored_background
            foreground = stored_foreground

        painter.save()
        painter.fillRect(option.rect, background)

        # Let Qt draw text/alignment/fonts but prevent the native/QSS selection
        # brush from replacing the explicitly chosen background above.
        opt.state &= ~QStyle.State_Selected
        opt.backgroundBrush = QBrush(background)
        opt.palette.setBrush(QPalette.Base, QBrush(background))
        opt.palette.setBrush(QPalette.AlternateBase, QBrush(background))
        opt.palette.setBrush(QPalette.Text, QBrush(foreground))
        opt.palette.setBrush(QPalette.WindowText, QBrush(foreground))
        opt.palette.setBrush(QPalette.Highlight, QBrush(background))
        opt.palette.setBrush(QPalette.HighlightedText, QBrush(foreground))

        style = option.widget.style() if option.widget is not None else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, opt, painter, option.widget)

        if selected:
            # A subtle boundary keeps adjacent selected rows legible while the
            # unified fill remains the primary selection indicator.
            border = QColor(tokens["table_selection_border"])
            painter.setPen(border)
            rect = option.rect.adjusted(0, 0, -1, -1)
            painter.drawLine(rect.topLeft(), rect.topRight())
            painter.drawLine(rect.bottomLeft(), rect.bottomRight())
            if index.column() == 0:
                painter.drawLine(rect.topLeft(), rect.bottomLeft())
            if index.column() == index.model().columnCount() - 1:
                painter.drawLine(rect.topRight(), rect.bottomRight())
        painter.restore()


class NumericTableWidgetItem(QTableWidgetItem):
    """
    表格欄位若顯示的是「格式化後的文字」（例如檔案大小顯示成 "1.50 MB"、
    時間顯示成 "2026-01-01 12:00:00"），預設點擊表頭排序時 Qt 會用「文字」
    做字典順序排序，而不是我們想要的「數值/時間」順序。

    這個類別讓建立時多帶一個 sort_value（原始的 bytes 數字 / timestamp），
    排序時改用 sort_value 比較大小，畫面上仍然顯示格式化後的文字。
    """

    def __init__(self, display_text: str, sort_value):
        super().__init__(display_text)
        self.sort_value = sort_value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            return self.sort_value < other.sort_value
        return super().__lt__(other)


class StatCard(QFrame):
    """
    右上角統計列使用的小卡片，例如：「檔案總數 128」「可釋放空間 512 MB」。
    """

    def __init__(self, caption: str, value: str = "0", danger: bool = False, parent=None):
        super().__init__(parent)
        self.setProperty("class", "statCard")
        self._danger = danger

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)

        self.value_label = QLabel(value)
        self.value_label.setProperty("class", "statValueDanger" if danger else "statValue")

        self.caption_label = QLabel(caption)
        self.caption_label.setProperty("class", "statLabel")

        layout.addWidget(self.value_label)
        layout.addWidget(self.caption_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)

    def set_caption(self, caption: str) -> None:
        self.caption_label.setText(caption)

    def refresh_style(self) -> None:
        """在切換主題（重新套用 QSS）後，強制刷新這個元件的樣式。"""
        for widget in (self, self.value_label, self.caption_label):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

