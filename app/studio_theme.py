"""Avunote "Signal" design system: monochrome instrument surfaces with one tally accent."""
from __future__ import annotations

import os
from pathlib import Path
from string import Template
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFontDatabase, QPainter, QPalette, QPen
from PySide6.QtWidgets import QComboBox

THEMES = ('system', 'light', 'dark')

# signal is the single tally accent (record, live state, progress, focus);
# brand is its text-safe variant for links and accent captions.
COLORS = {
    'light': dict(
        canvas='#FFFFFF', rail='#F4F4F5', surface='#FFFFFF', inset='#FAFAFA',
        text='#0A0A0A', muted='#52525B', faint='#63636B', line='#E4E4E7', line_strong='#D4D4D8',
        outline='#85858E', brand='#B83A06', action='#0A0A0A', action_hover='#2A2A2E', action_ink='#FFFFFF',
        signal='#FF4F0F', signal_hover='#FF6A33', signal_ink='#0A0A0A',
        brand_soft='#FFF2EA', brand_line='#FFD3BD', focus='#E5480E',
        hover='#EFEFF1', pressed='#E4E4E7', disabled='#F4F4F5', disabled_ink='#85858E',
        good='#13733A', good_bg='#EEF9F1', warn='#8A5200', warn_bg='#FFF6E0',
        danger='#BE1E1E', danger_bg='#FFF0EF', thumb='#C9C9CF',
        hero='#FFFFFF', wave='#C9C9CF', chat_reply='#FFFFFF', chat_user='#F4F4F5',
    ),
    'dark': dict(
        canvas='#0B0B0C', rail='#111113', surface='#18181B', inset='#0F0F10',
        text='#F4F4F5', muted='#A1A1AA', faint='#8E8E96', line='#222225', line_strong='#303035',
        outline='#6E6E77', brand='#FF8A50', action='#F4F4F5', action_hover='#FFFFFF', action_ink='#0A0A0A',
        signal='#FF5A1F', signal_hover='#FF7440', signal_ink='#0A0A0A',
        brand_soft='#2A160C', brand_line='#5A2A12', focus='#FF6A2B',
        hover='#1C1C1F', pressed='#26262A', disabled='#161618', disabled_ink='#71717A',
        good='#5BE08C', good_bg='#0E2416', warn='#FBC23C', warn_bg='#2A1F06',
        danger='#FF8A8A', danger_bg='#2C1212', thumb='#3F3F46',
        hero='#111113', wave='#3A3A40', chat_reply='#0B0B0C', chat_user='#1A1A1D',
    ),
}

_FONTS_LOADED = False


def asset_root():
    return Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent


def load_fonts():
    """Register the bundled Vazirmatn family once; Latin UI uses Windows' own Segoe faces."""
    global _FONTS_LOADED
    if _FONTS_LOADED:
        return
    _FONTS_LOADED = True
    for path in sorted((asset_root()/'assets'/'fonts').glob('*.ttf')):
        QFontDatabase.addApplicationFont(str(path))


def font_roles(rtl=False):
    load_fonts()
    available = set(QFontDatabase.families())

    def first(*names):
        return next((name for name in names if name in available), names[-1])

    if rtl:
        ui = display = first('Vazirmatn', 'Segoe UI')
    else:
        ui = first('Segoe UI Variable Text', 'Segoe UI')
        display = first('Segoe UI Variable Display', 'Segoe UI')
    return {'ui_font': ui, 'display_font': display, 'mono_font': first('Cascadia Mono', 'Consolas'),
            'script_font': first('Vazirmatn', 'Segoe UI')}


def animations_enabled():
    """Honor Windows' "Show animations" accessibility switch (reduced motion)."""
    if os.name != 'nt':
        return True
    try:
        import ctypes
        value = ctypes.c_int(1)
        if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(value), 0):
            return bool(value.value)
    except (AttributeError, OSError):
        pass
    return True


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
        painter.setPen(QPen(self.palette().color(QPalette.ColorRole.ButtonText), 1.4,
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
        x = 16 if self.layoutDirection() == Qt.LayoutDirection.RightToLeft else self.width()-17
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
        (QPalette.ColorRole.Base, 'surface'), (QPalette.ColorRole.AlternateBase, 'rail'),
        (QPalette.ColorRole.Text, 'text'), (QPalette.ColorRole.PlaceholderText, 'faint'),
        (QPalette.ColorRole.Button, 'surface'), (QPalette.ColorRole.ButtonText, 'text'),
        (QPalette.ColorRole.Highlight, 'signal'), (QPalette.ColorRole.HighlightedText, 'signal_ink'),
        (QPalette.ColorRole.Link, 'brand'), (QPalette.ColorRole.ToolTipBase, 'text'),
        (QPalette.ColorRole.ToolTipText, 'canvas'),
    ):
        palette.setColor(role, QColor(colors[key]))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(colors['disabled_ink']))
    return palette


_STYLE = Template("""
QWidget {font-family: "$ui_font"; font-size: 14px; color: $text;}
QMainWindow, QWidget#shell, QWidget#page, QStackedWidget#workspace, QDialog, QMessageBox {background: $canvas;}

QFrame#topBar {background: $canvas; border: 0; border-bottom: 1px solid $line;}
QFrame#console {background: $rail; border: 0; border-$end: 1px solid $line;}
QFrame#chatSide {background: $rail; border: 0;}
QWidget#consoleBody {background: $rail;}
QFrame#deck {background: $rail; border: 0; border-top: 1px solid $line;}
QFrame#rule {background: $line; border: 0; min-height: 1px; max-height: 1px;}
QFrame#modelCard {background: transparent; border: 0; border-bottom: 1px solid $line; border-radius: 0;}
QFrame#settingsRow {background: transparent; border: 0; border-top: 1px solid $line;}
QFrame#disclosure {background: $rail; border: 0; border-radius: 12px;}
QFrame#chatComposer {background: $rail; border: 1px solid $line; border-radius: 20px;}
QFrame#chatReference {background: transparent; border: 0; border-$start: 2px solid $signal; border-radius: 0;}

QLabel#heading {font-family: "$display_font"; font-size: 30px; font-weight: 600; color: $text;}
QLabel#display {font-family: "$display_font"; font-size: 24px; font-weight: 600; color: $text;}
QLabel#cardTitle, QLabel#libraryTitle, QLabel#sectionTitle {font-size: 15px; font-weight: 600;}
QLabel#muted, QLabel#modelStatus {color: $muted; font-size: 13px;}
QLabel#fieldLabel {color: $muted; font-size: 12px; font-weight: 600;}
QLabel#meta {font-family: "$mono_font"; font-size: 12px; color: $faint;}
QLabel#emptyGlyph {background: transparent; border: 0;}
QLabel#modelNotice {
    color: $muted; font-size: 13px; background: transparent; border: 0; border-radius: 0;
    border-$start: 2px solid $line_strong; padding: 3px 0; padding-$start: 12px;
}
QLabel#modelNotice[tone="ready"] {color: $good; border-$start-color: $good;}
QLabel#modelNotice[tone="warning"] {color: $warn; border-$start-color: $warn;}
QLabel#modelNotice[tone="error"] {color: $danger; border-$start-color: $danger;}
QLabel#modelNotice[tone="info"] {color: $brand; border-$start-color: $signal;}
QLabel#modelStatus[tone="ready"] {color: $good;}
QLabel#modelStatus[tone="warning"] {color: $warn;}
QLabel#modelStatus[tone="error"] {color: $danger;}
QLabel#modelStatus[tone="info"] {color: $brand;}

QPushButton, QToolButton {
    background: transparent; color: $text; border: 1px solid $line_strong;
    border-radius: 22px; padding: 0 18px; font-weight: 500;
}
QPushButton:hover, QToolButton:hover {background: $hover; border-color: $outline;}
QPushButton:pressed, QToolButton:pressed {background: $pressed;}
QPushButton#primary {background: $action; color: $action_ink; border-color: $action; font-weight: 600;}
QPushButton#primary:hover {background: $action_hover; border-color: $action_hover;}
QPushButton#record {
    background: $signal; color: $signal_ink; border: 1px solid $signal; border-radius: 26px;
    font-weight: 600; font-size: 15px;
}
QPushButton#record:hover {background: $signal_hover; border-color: $signal_hover;}
QPushButton#danger {background: transparent; color: $danger; border-color: $danger; border-radius: 22px;}
QPushButton#danger:hover {background: $danger_bg;}
QPushButton#accent {background: transparent; color: $text; border-color: $signal; font-weight: 600;}
QPushButton#accent:hover {background: $brand_soft;}
QPushButton#link, QPushButton#quiet {background: transparent; border: 1px solid transparent;}
QPushButton#link {color: $brand; border-radius: 8px; padding: 0 6px; text-align: $alignment;}
QPushButton#quiet {color: $muted; padding: 0 12px;}
QPushButton#quiet:hover, QPushButton#link:hover {background: $hover; color: $text;}
QPushButton#quiet:checked {background: $surface; color: $text; border-color: $line_strong;}
QPushButton#nav {
    background: transparent; color: $muted; border: 0; border-radius: 0;
    border-bottom: 2px solid transparent; border-top: 2px solid transparent;
    padding: 0 10px; margin: 0 2px; font-weight: 600;
}
QPushButton#nav:hover {color: $text;}
QPushButton#nav:checked {color: $text; border-bottom-color: $signal;}
QPushButton:disabled, QPushButton#primary:disabled, QPushButton#record:disabled,
QPushButton#accent:disabled, QPushButton#danger:disabled, QToolButton:disabled {
    background: $disabled; color: $disabled_ink; border-color: $line;
}
QPushButton#quiet:disabled, QPushButton#link:disabled, QPushButton#nav:disabled {
    background: transparent; color: $disabled_ink; border-color: transparent;
}
QPushButton:focus, QToolButton:focus, QPushButton#primary:focus, QPushButton#accent:focus,
QPushButton#danger:focus, QPushButton#quiet:focus, QPushButton#link:focus {border: 2px solid $focus;}
QPushButton#record:focus {border: 2px solid $text;}
QPushButton#nav:focus {color: $text; border-top: 2px solid $focus;}

QComboBox, QLineEdit, QPlainTextEdit {
    background: $rail; color: $text; border: 1px solid transparent; border-bottom: 1px solid $outline;
    border-radius: 0; border-top-left-radius: 6px; border-top-right-radius: 6px;
    selection-background-color: $signal; selection-color: $signal_ink;
}
QFrame#console QComboBox, QFrame#deck QComboBox, QFrame#chatSide QComboBox, QDialog QLineEdit {background: $surface;}
QComboBox {min-height: 24px; padding: 8px 12px;}
QComboBox:hover, QLineEdit:hover {border-bottom-color: $text;}
QComboBox::drop-down {border: 0; width: 30px;}
QComboBox[customChevron="true"]::down-arrow {image: none;}
QComboBox QAbstractItemView, QMenu {
    background: $surface; color: $text; border: 1px solid $line_strong; padding: 6px;
    selection-background-color: $hover; selection-color: $text; outline: 0;
}
QComboBox QAbstractItemView::item {min-height: 32px; padding: 4px 8px;}
QMenu::item {padding: 8px 24px 8px 12px; border-radius: 6px;}
QMenu::item:selected {background: $hover; color: $text;}
QMenu::item:disabled {color: $disabled_ink;}
QMenu::separator {height: 1px; background: $line; margin: 6px 4px;}
QComboBox:disabled, QLineEdit:disabled, QPlainTextEdit:disabled {
    background: $disabled; color: $disabled_ink; border-bottom-color: $line_strong;
}
QLineEdit, QPlainTextEdit {padding: 8px 12px;}
QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus {border-bottom: 2px solid $focus;}
QComboBox QLineEdit, QComboBox QLineEdit:focus, QComboBox QLineEdit:hover, QComboBox QLineEdit:disabled {
    background: transparent; border: 0; padding: 0; min-height: 0;
}
QListWidget:focus, QTextBrowser:focus, QTableWidget:focus {border: 1px solid $focus;}
QCheckBox {spacing: 10px; padding: 4px 0;}
QCheckBox::indicator {width: 18px; height: 18px;}
QCheckBox:focus {color: $text; border-bottom: 2px solid $focus;}

QWidget#transcriptEmpty {background: transparent;}
QTextEdit#transcript {
    background: transparent; border: 0; border-radius: 0; font-size: 19px;
    selection-background-color: $signal; selection-color: $signal_ink;
}
QTextEdit#transcript[script="rtl"] {font-family: "$script_font"; font-size: 20px;}
QTextEdit#transcript:focus {border: 0; border-$start: 2px solid $focus;}
QTextBrowser#chatMessages {background: $canvas; border: 0; font-size: 15px;}
QTextBrowser#chatMessages:focus {border: 0; border-$start: 2px solid $focus;}
QPlainTextEdit#chatInput {background: transparent; border: 0; border-radius: 12px; font-size: 15px;}
QPlainTextEdit#chatInput:focus {background: $surface; border: 0;}
QFrame#chatReference QPlainTextEdit {background: transparent; border: 0; color: $muted;}
QListWidget#conversationList {background: transparent; border: 1px solid transparent; padding: 0;}
QListWidget#conversationList::item {border-radius: 10px; padding: 8px 10px; color: $muted; border: 1px solid transparent;}
QListWidget#conversationList::item:selected {background: $surface; color: $text; border: 1px solid $line_strong;}
QListWidget#conversationList::item:hover:!selected {background: $hover; color: $text;}
QSplitter::handle {background: $line;}
QSplitter::handle:horizontal {width: 1px;}
QProgressBar {background: $line; border: 0; border-radius: 0; min-height: 3px; max-height: 3px;}
QProgressBar::chunk {background: $signal; border-radius: 0;}
QScrollArea {background: transparent; border: 0;}
QTableWidget {
    background: $canvas; border: 0; gridline-color: transparent;
    selection-background-color: $rail; selection-color: $text;
}
QTableWidget::item {padding: 0 12px; border-bottom: 1px solid $line;}
QTableWidget::item:selected {background: $rail; color: $text; border-bottom: 1px solid $signal;}
QHeaderView::section {
    background: $canvas; color: $faint; padding: 10px 12px; border: 0;
    border-bottom: 1px solid $line_strong; font-size: 12px; font-weight: 600;
}
QTableCornerButton::section {background: $canvas; border: 0;}
QScrollBar:vertical {background: transparent; width: 10px; margin: 0;}
QScrollBar::handle:vertical {background: $thumb; border-radius: 3px; min-height: 32px; margin: 2px;}
QScrollBar:horizontal {background: transparent; height: 10px; margin: 0;}
QScrollBar::handle:horizontal {background: $thumb; border-radius: 3px; min-width: 32px; margin: 2px;}
QScrollBar::add-line, QScrollBar::sub-line {width: 0; height: 0;}
QScrollBar::add-page, QScrollBar::sub-page {background: transparent;}
QToolTip {background: $text; color: $canvas; border: 0; padding: 6px 10px;}
""")


def stylesheet(resolved, rtl=False):
    return _STYLE.substitute(
        COLORS[resolved], **font_roles(rtl), alignment='right' if rtl else 'left',
        start='right' if rtl else 'left', end='left' if rtl else 'right',
    )
