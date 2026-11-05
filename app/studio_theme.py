"""Small native theme layer; no web resources or application-state resets."""
from __future__ import annotations

import re

THEMES = ('system', 'light', 'dark')


def resolve_theme(choice, color_scheme=None):
    if choice in {'light', 'dark'}:
        return choice
    return 'dark' if str(color_scheme).lower().endswith('dark') else 'light'


def stylesheet(light_style, resolved):
    extra = '''
QDialog, QMessageBox {background:#ffffff; color:#102240;}
QLineEdit, QPlainTextEdit, QListWidget {background:#ffffff; color:#102240; border:1px solid #dce1ed; border-radius:8px; padding:8px;}
QLineEdit:focus, QPlainTextEdit:focus {border:2px solid #6754e8;}
QCheckBox {spacing:8px;}
QCheckBox::indicator {width:18px; height:18px;}
QToolButton {min-height:32px; padding:4px 8px;}
'''
    style = light_style + extra
    if resolved != 'dark':
        return style
    colors = {
        '#f7f8fc':'#0f1420', '#ffffff':'#171f2e', '#102240':'#eef2fb',
        '#e5e8f0':'#303b50', '#f0edff':'#292344', '#e1dcff':'#514674',
        '#f8f8fc':'#1c2536', '#6754e8':'#a08bff', '#5c6b82':'#b4bfd1',
        '#5140c3':'#d0c5ff', '#243751':'#e1e8f6', '#dce1ed':'#39465e',
        '#f4f2ff':'#302943', '#b5aaef':'#9c8acc', '#f6f7fa':'#1d2636',
        '#8994a8':'#8a98ad', '#5541d4':'#b5a4ff', '#eeebfa':'#302943',
        '#8e85b5':'#a098bb', '#e1dcf3':'#49415f', '#fff1f2':'#3c2430',
        '#e5adb9':'#8a4d65', '#a42d4d':'#ffb3c8', '#66748c':'#b8c3d6',
        '#f7f6fc':'#242d3f', '#eeebff':'#302749', '#5944d0':'#c9bdff',
        '#5741cf':'#c9bdff', '#e4deff':'#403455', '#4730c4':'#ded5ff',
        '#e1dcff':'#514674', '#eeedf6':'#303849', '#ebeaf5':'#303849',
        '#edf0f5':'#30394a', '#fafbfe':'#1b2536', '#f0f2f8':'#253145',
        '#ccd1e2':'#4b5970',
    }
    style = re.sub(r'#[0-9a-fA-F]{6}', lambda m: colors.get(m.group().lower(), m.group()), style)
    # The light purple action on a dark canvas needs dark foreground, not white.
    return style + '''
QPushButton#primary {background:#a08bff; color:#101322; border-color:#a08bff;}
QPushButton#primary:hover {background:#b5a4ff;}
QPushButton#primary:disabled {background:#342d48; color:#a098bb; border-color:#49415f;}
QTextEdit {selection-background-color:#5e4a96; selection-color:#ffffff;}
'''
