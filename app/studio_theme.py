"""Semantic colors and native widget styling for Avunote's two appearances."""
from __future__ import annotations

from string import Template

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPalette, QPen
from PySide6.QtWidgets import QComboBox

THEMES = ('system', 'light', 'dark')

COLORS = {
    'light': dict(
        canvas='#F7F7F4', rail='#EFEFEB', surface='#FFFFFF', inset='#F3F3F0',
        text='#222421', muted='#575B55', line='#DEDFD8', outline='#888E83',
        brand='#5140B2', action='#5844C4', action_hover='#4937A9', action_ink='#FFFFFF',
        brand_soft='#EEEBFA', brand_line='#DAD3F1', focus='#5B43C9',
        hover='#EFEFEB', pressed='#E6E7E1', disabled='#F0F0EC', disabled_ink='#70756D',
        good='#205C49', good_bg='#EAF3ED', warn='#77511E', warn_bg='#FBF0DF',
        danger='#A0354C', danger_bg='#FBEAF0', thumb='#A3AA9D',
        hero='#F3F3F0', wave='#8D81B7', chat_reply='#FFFFFF',
    ),
    'dark': dict(
        canvas='#191B19', rail='#151715', surface='#212420', inset='#1B1E1B',
        text='#F2F3EF', muted='#BABFB5', line='#373C35', outline='#777E72',
        brand='#CBBFFF', action='#C6B9FF', action_hover='#D6CDFF', action_ink='#251C43',
        brand_soft='#332D45', brand_line='#54486B', focus='#CDBDFF',
        hover='#2A2D27', pressed='#343930', disabled='#282C26', disabled_ink='#A4AA9E',
        good='#A8DCC1', good_bg='#273B30', warn='#F3D09D', warn_bg='#3A3124',
        danger='#FFBBC8', danger_bg='#402B32', thumb='#6F786A',
        hero='#212420', wave='#8475A8', chat_reply='#212420',
    ),
}


class ChevronComboBox(QComboBox):
    """Theme the disclosure mark while retaining Qt's native popup and keyboard handling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setProperty('customChevron', True)
        self.setMinimumHeight(44)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self.palette().color(QPalette.ColorRole.ButtonText), 1.6,
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        x = 14 if self.layoutDirection() == Qt.LayoutDirection.RightToLeft else self.width()-15
        y = self.height()//2
        painter.drawLine(x-4, y-2, x, y+2)
        painter.drawLine(x, y+2, x+4, y-2)


def resolve_theme(choice, color_scheme=None):
    if choice in {'light', 'dark'}:
        return choice
    return 'dark' if str(color_scheme).lower().endswith('dark') else 'light'


def native_palette(theme):
    colors = COLORS[theme]
    palette = QPalette()
    for role, key in (
        (QPalette.ColorRole.Window, 'canvas'), (QPalette.ColorRole.WindowText, 'text'),
        (QPalette.ColorRole.Base, 'surface'), (QPalette.ColorRole.AlternateBase, 'inset'),
        (QPalette.ColorRole.Text, 'text'), (QPalette.ColorRole.PlaceholderText, 'muted'),
        (QPalette.ColorRole.Button, 'surface'), (QPalette.ColorRole.ButtonText, 'text'),
        (QPalette.ColorRole.Highlight, 'action'), (QPalette.ColorRole.HighlightedText, 'action_ink'),
        (QPalette.ColorRole.Link, 'brand'), (QPalette.ColorRole.ToolTipBase, 'surface'),
        (QPalette.ColorRole.ToolTipText, 'text'),
    ):
        palette.setColor(role, QColor(colors[key]))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(colors['disabled_ink']))
    return palette


_STYLE = Template("""
QWidget {font-family: "Segoe UI"; font-size: 14px; color: $text;}
QMainWindow, QWidget#shell, QWidget#page, QDialog, QMessageBox {background: $canvas;}
QFrame#rail {background: $rail; $rail_border: 1px solid $line;}
QFrame#toolStrip, QFrame#captureDock, QFrame#modelCard, QFrame#editorSurface {
    background: $surface; border: 1px solid $line; border-radius: 13px;
}
QFrame#chatSide {background: $rail; border: 1px solid $line; border-radius: 12px;}
QFrame#chatComposer {background: $surface; border: 1px solid $outline; border-radius: 16px;}
QFrame#disclosure {background: $inset; border-radius: 8px;}
QFrame#chatReference {background: $inset; border: 1px solid $line; border-radius: 10px;}
QLabel#heading {font-size: 27px; font-weight: 700;}
QLabel#cardTitle, QLabel#libraryTitle, QLabel#sectionTitle {font-size: 16px; font-weight: 650;}
QLabel#muted, QLabel#fieldLabel, QLabel#modelStatus, QLabel#modelNotice {color: $muted; font-size: 13px;}
QLabel#fieldLabel {font-weight: 600;}
QLabel#emptyGlyph {background: $brand_soft; border: 1px solid $brand_line; border-radius: 18px;}
QLabel#modelNotice {padding: 5px 8px; border-radius: 7px;}
QLabel#modelNotice[tone="ready"], QLabel#modelStatus[tone="ready"] {color: $good;}
QLabel#modelNotice[tone="warning"], QLabel#modelStatus[tone="warning"] {color: $warn;}
QLabel#modelNotice[tone="error"], QLabel#modelStatus[tone="error"] {color: $danger;}
QLabel#modelNotice[tone="info"], QLabel#modelStatus[tone="info"] {color: $brand;}
QLabel#modelNotice[tone="warning"] {background: $warn_bg;}
QLabel#modelNotice[tone="error"] {background: $danger_bg;}
QLabel#modelNotice[tone="info"] {background: $brand_soft;}
QLabel#modelNotice[tone="ready"] {background: $good_bg;}

QPushButton, QToolButton {
    background: $surface; color: $text; border: 1px solid $outline;
    border-radius: 8px; padding: 7px 12px; font-weight: 550;
}
QPushButton:hover, QToolButton:hover {background: $hover; border-color: $text;}
QPushButton:pressed, QToolButton:pressed {background: $pressed;}
QPushButton#primary {background: $action; color: $action_ink; border-color: $action; font-weight: 650;}
QPushButton#primary:hover {background: $action_hover; border-color: $action_hover;}
QPushButton#primary:pressed {background: $brand_soft; color: $brand; border-color: $brand;}
QPushButton#accent {background: $brand_soft; color: $brand; border-color: $brand_line; font-weight: 600;}
QPushButton#accent:hover {border-color: $brand;}
QPushButton#danger {background: $danger_bg; color: $danger; border-color: $danger;}
QPushButton#link, QPushButton#quiet, QPushButton#nav {background: transparent; border: 1px solid transparent;}
QPushButton#link {color: $brand;}
QPushButton#quiet, QPushButton#nav {color: $muted;}
QPushButton#quiet:hover, QPushButton#nav:hover, QPushButton#link:hover {background: $hover; color: $text;}
QPushButton#quiet:checked {background: $brand_soft; color: $brand;}
QPushButton#nav {text-align: $alignment; padding: 8px 9px; font-weight: 600;}
QPushButton#nav:checked {background: $surface; border-color: $line; color: $brand;}
QPushButton:disabled, QPushButton#primary:disabled, QPushButton#accent:disabled, QToolButton:disabled {
    background: $disabled; color: $disabled_ink; border-color: $line;
}
QPushButton#quiet:disabled, QPushButton#link:disabled {
    background: transparent; color: $disabled_ink; border-color: transparent;
}
QPushButton:focus, QToolButton:focus, QPushButton#nav:focus, QPushButton#link:focus,
QPushButton#quiet:focus, QPushButton#accent:focus, QPushButton#danger:focus,
QPushButton#secondary:focus {border: 2px solid $focus;}
QPushButton#primary:focus {border: 2px solid $action_ink;}

QComboBox, QLineEdit, QPlainTextEdit, QListWidget, QTextBrowser {
    background: $surface; color: $text; border: 1px solid $outline; border-radius: 8px;
    selection-background-color: $action; selection-color: $action_ink;
}
QComboBox {min-height: 24px; padding: 8px 10px;}
QComboBox::drop-down {border: 0; width: 26px;}
QComboBox[customChevron="true"]::down-arrow {image: none;}
QComboBox QAbstractItemView, QMenu {
    background: $surface; color: $text; border: 1px solid $outline; padding: 4px;
    selection-background-color: $brand_soft; selection-color: $text; outline: 0;
}
QComboBox QAbstractItemView::item {min-height: 28px; padding: 4px;}
QMenu::item {padding: 7px 20px 7px 10px;}
QMenu::item:selected {background: $brand_soft; color: $text;}
QMenu::item:disabled {color: $disabled_ink;}
QComboBox:disabled, QLineEdit:disabled, QPlainTextEdit:disabled {background: $disabled; color: $disabled_ink;}
QLineEdit, QPlainTextEdit {padding: 8px 10px;}
QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus, QListWidget:focus, QTextBrowser:focus,
QTextEdit:focus, QTableWidget:focus {border: 2px solid $focus;}
QCheckBox {spacing: 8px; padding: 4px 0;}
QCheckBox::indicator {width: 18px; height: 18px;}

QWidget#transcriptEmpty, QTextEdit#transcript {background: $inset; border: 0; border-radius: 9px;}
QTextEdit#transcript {font-size: 18px; selection-background-color: $action; selection-color: $action_ink;}
QTextEdit#transcript:focus {border: 2px solid $focus;}
QTextBrowser#chatMessages {background: $canvas; border: 0; font-size: 15px;}
QTextBrowser#chatMessages:focus {border: 2px solid $focus;}
QPlainTextEdit#chatInput {background: $surface; border: 1px solid transparent; font-size: 15px;}
QPlainTextEdit#chatInput:focus {border-color: $focus;}
QListWidget#conversationList {background: $rail; border: 1px solid transparent; padding: 3px;}
QListWidget#conversationList:focus {border-color: $focus;}
QListWidget#conversationList::item {border-radius: 7px; padding: 6px 8px;}
QListWidget#conversationList::item:selected {background: $brand_soft; color: $text;}
QListWidget#conversationList::item:hover:!selected {background: $hover;}
QSplitter::handle {background: $line;}
QSplitter::handle:horizontal {width: 3px;}
QProgressBar {background: $brand_soft; border: 0; border-radius: 3px; min-height: 6px; max-height: 6px;}
QProgressBar::chunk {background: $action; border-radius: 3px;}
QScrollArea {background: transparent; border: 0;}
QTableWidget {
    background: $surface; alternate-background-color: $inset;
    border: 1px solid $line; border-radius: 10px; gridline-color: $line;
    selection-background-color: $brand_soft; selection-color: $text;
}
QHeaderView::section {background: $rail; color: $muted; padding: 10px; border: 0; font-weight: 600;}
QTableWidget::item {padding: 8px;}
QScrollBar:vertical {background: $inset; width: 10px; margin: 0;}
QScrollBar::handle:vertical {background: $thumb; border-radius: 4px; min-height: 28px; margin: 1px;}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {height: 0;}
QToolTip {background: $surface; color: $text; border: 1px solid $outline; padding: 7px;}
""")


def stylesheet(resolved, rtl=False):
    return _STYLE.substitute(
        COLORS[resolved], alignment='right' if rtl else 'left',
        rail_border='border-left' if rtl else 'border-right',
    )
