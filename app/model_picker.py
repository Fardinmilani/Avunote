"""A model combo popup with separate, keyboard-accessible download actions."""

from dataclasses import dataclass
from string import Template

from PySide6.QtCore import QEvent, QPoint, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton,
                               QScrollArea, QSizePolicy, QToolButton, QVBoxLayout, QWidget)

from studio_theme import COLORS
from ui_i18n import tr

ACTIVE = frozenset({'resolving', 'downloading', 'verifying'})


@dataclass(frozen=True)
class ModelChoice:
    key: str
    title: str
    detail: str
    status: str
    state: str
    ready: bool
    percent: float


_STYLE = Template("""
QFrame#modelPickerPopup {
    background: $surface; border: 1px solid $outline; border-radius: 10px;
}
QWidget#modelPickerContent {background: $surface;}
QFrame#modelPickerRow {background: $surface; border: 0;}
QLabel#modelChoiceTitle {color: $text; font-size: 14px; font-weight: 600;}
QLabel#modelChoiceStatus {color: $muted; font-size: 12px;}
QPushButton#modelChoiceSelect {
    background: $surface; border: 1px solid transparent; border-radius: 8px;
    color: $text; text-align: $alignment; padding: 9px; font-weight: 600;
}
QPushButton#modelChoiceSelect:checked {background: $brand_soft; color: $brand;}
QPushButton#modelChoiceSelect:hover {background: $hover;}
QToolButton#modelDownloadAction {
    background: $brand_soft; border: 1px solid $line; border-radius: 8px; padding: 0;
}
QToolButton#modelDownloadAction:hover {background: $hover; border-color: $brand;}
QToolButton#modelDownloadAction:disabled {background: $disabled; border-color: $line;}
QToolButton#modelDownloadAction:focus, QPushButton#modelChoiceSelect:focus {
    border: 2px solid $focus;
}
QProgressBar#modelChoiceProgress {
    background: $line; border: 0; border-radius: 2px; min-height: 4px; max-height: 4px;
}
QProgressBar#modelChoiceProgress::chunk {background: $brand; border-radius: 2px;}
""")


def _action_icon(action, foreground, disabled):
    icon = QIcon()
    for mode, color in ((QIcon.Mode.Normal, foreground), (QIcon.Mode.Disabled, disabled)):
        for scale in (1, 2):
            image = QPixmap(20 * scale, 20 * scale)
            image.setDevicePixelRatio(scale)
            image.fill(Qt.GlobalColor.transparent)
            with QPainter(image) as painter:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setPen(QPen(QColor(color), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                if action == 'pause':
                    painter.drawLine(7, 5, 7, 15)
                    painter.drawLine(13, 5, 13, 15)
                else:
                    painter.drawLine(10, 3, 10, 13)
                    painter.drawLine(6, 9, 10, 13)
                    painter.drawLine(10, 13, 14, 9)
                    painter.drawLine(4, 17, 16, 17)
            icon.addPixmap(image, mode)
    return icon


class _ModelRow(QFrame):
    def __init__(self, popup, key):
        super().__init__()
        self.setObjectName('modelPickerRow')
        self.setProperty('modelKey', key)
        self.key = key
        self.choice = None
        self.command = None
        self.icon_state = None
        self.theme = None
        self.selected = None
        self.active_key = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.select_button = QPushButton()
        self.select_button.setObjectName('modelChoiceSelect')
        self.select_button.setCheckable(True)
        self.select_button.setMinimumHeight(44)
        self.select_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.select_button.clicked.connect(lambda: popup.combo.select_model(key))
        self.select_button.installEventFilter(popup)
        layout.addWidget(self.select_button)

        self.pending = QWidget()
        controls = QHBoxLayout(self.pending)
        controls.setContentsMargins(9, 4, 5, 4)
        controls.setSpacing(12)
        captions = QVBoxLayout()
        captions.setSpacing(3)
        self.title = QLabel()
        self.title.setObjectName('modelChoiceTitle')
        self.status = QLabel()
        self.status.setObjectName('modelChoiceStatus')
        for label in (self.title, self.status):
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setWordWrap(True)
            captions.addWidget(label)
        self.progress = QProgressBar()
        self.progress.setObjectName('modelChoiceProgress')
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        captions.addWidget(self.progress)
        controls.addLayout(captions, 1)

        self.action = QToolButton()
        self.action.setObjectName('modelDownloadAction')
        self.action.setFixedSize(44, 44)
        self.action.setIconSize(QSize(20, 20))
        self.action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.action.clicked.connect(lambda: popup.combo.downloadRequested.emit(key, self.command))
        self.action.installEventFilter(popup)
        controls.addWidget(self.action, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.pending)

    def sync(self, choice, selected, active_key, theme):
        if (choice, selected, active_key, theme) == (self.choice, self.selected, self.active_key, self.theme):
            return
        self.choice, self.selected, self.active_key, self.theme = choice, selected, active_key, theme
        self.select_button.setVisible(choice.ready)
        self.pending.setVisible(not choice.ready)
        if choice.ready:
            self.select_button.setText(choice.title.replace('&', '&&'))
            self.select_button.setAccessibleName(f"{tr('استفاده از مدل')} · {choice.title}")
            self.select_button.setToolTip(f'{choice.title}\n{choice.detail}')
            self.select_button.setChecked(selected)
            return

        self.title.setText(choice.title)
        self.status.setText(choice.status)
        self.progress.setVisible(choice.state in ACTIVE or choice.state == 'paused')
        self.progress.setValue(int(choice.percent))
        self.progress.setAccessibleName(choice.status)
        self.command = 'pause' if choice.state in ACTIVE else 'start'
        caption = (
            'توقف موقت' if self.command == 'pause' else
            'ادامه دانلود' if choice.state in {'paused', 'error'} else 'دانلود مدل'
        )
        description = f'{tr(caption)} · {choice.title}'
        blocked = active_key is not None and active_key != choice.key
        if blocked:
            description += f"\n{tr('یک مدل دیگر در حال دانلود است.')}"
        self.pending.setToolTip(description)
        self.action.setAccessibleName(description)
        self.action.setToolTip(description)
        self.action.setEnabled(not blocked and choice.state != 'cancelled-pending')
        icon_state = self.command, theme
        if icon_state != self.icon_state:
            colors = COLORS[theme]
            self.action.setIcon(_action_icon(self.command, colors['brand'], colors['disabled_ink']))
            self.icon_state = icon_state

    def button(self):
        return self.select_button if self.choice.ready else self.action


class _ModelPopup(QFrame):
    def __init__(self, combo):
        super().__init__(combo, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.combo = combo
        self.setObjectName('modelPickerPopup')
        self.style_key = None
        self.rows = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content = QWidget()
        self.content.setObjectName('modelPickerContent')
        self.rows_layout = QVBoxLayout(self.content)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(3)
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)

    def sync(self, choices, active_key, theme):
        rtl = self.combo.layoutDirection() == Qt.LayoutDirection.RightToLeft
        self.setLayoutDirection(self.combo.layoutDirection())
        self.setAccessibleName(self.combo.accessibleName())
        style_key = (theme, rtl)
        if style_key != self.style_key:
            self.setStyleSheet(_STYLE.substitute(COLORS[theme], alignment='right' if rtl else 'left'))
            self.style_key = style_key
        if tuple(self.rows) != tuple(choice.key for choice in choices):
            for row in self.rows.values():
                self.rows_layout.removeWidget(row)
                row.hide()
                row.deleteLater()
            self.rows.clear()
            for choice in choices:
                row = _ModelRow(self, choice.key)
                self.rows[choice.key] = row
                self.rows_layout.addWidget(row)
        for choice in choices:
            self.rows[choice.key].sync(choice, choice.key == self.combo.currentData(), active_key, theme)

    def place(self):
        combo = self.combo
        available = combo.screen().availableGeometry().adjusted(6, 6, -6, -6)
        anchor = combo.mapToGlobal(QPoint(0, 0))
        width = min(max(combo.width(), 418), available.width())
        self.resize(width, 320)
        self.rows_layout.activate()
        desired = min(max(54, self.rows_layout.sizeHint().height() + 14), 330)
        below = available.bottom() - anchor.y() - combo.height() - 4
        above = anchor.y() - available.top() - 4
        use_below = below >= desired or below >= above
        height = min(desired, max(54, below if use_below else above), available.height())
        x = anchor.x()
        if combo.layoutDirection() == Qt.LayoutDirection.RightToLeft:
            x += combo.width() - width
        x = max(available.left(), min(x, available.right() - width + 1))
        y = anchor.y() + combo.height() + 4 if use_below else anchor.y() - height - 4
        y = max(available.top(), min(y, available.bottom() - height + 1))
        self.setGeometry(x, y, width, height)

    def focus_current(self):
        row = self.rows.get(self.combo.currentData())
        buttons = self._buttons()
        button = row.button() if row else buttons[0] if buttons else None
        if button:
            self._focus(button)
        else:
            self.setFocus()

    def _buttons(self):
        return [row.button() for row in self.rows.values() if row.choice is not None and row.button().isEnabled()]

    def _focus(self, button):
        button.setFocus(Qt.FocusReason.PopupFocusReason)
        self.scroll.ensureWidgetVisible(button, 0, 6)

    def focusNextPrevChild(self, next):
        buttons = self._buttons()
        if not buttons:
            return super().focusNextPrevChild(next)
        focus = self.focusWidget()
        index = buttons.index(focus) if focus in buttons else -1 if next else 0
        self._focus(buttons[(index + (1 if next else -1)) % len(buttons)])
        return True

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                return self.focusNextPrevChild(key == Qt.Key.Key_Down)
            if key in (Qt.Key.Key_Home, Qt.Key.Key_End):
                buttons = self._buttons()
                if buttons:
                    self._focus(buttons[0] if key == Qt.Key.Key_Home else buttons[-1])
                    return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                watched.click()
                return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.combo.hidePopup()
            self.combo.setFocus(Qt.FocusReason.PopupFocusReason)
            event.accept()
        else:
            super().keyPressEvent(event)


class ModelPopupMixin:
    """Retain the combo's installed-only selection model and draw actions in its popup."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._model_popup = None
        self._model_choices = ()
        self._model_theme = 'light'
        self._active_download_key = None

    def set_model_rows(self, choices, active_key, theme):
        self._model_choices = tuple(choices)
        self._model_theme = theme
        self._active_download_key = active_key
        if self._model_popup is not None and self._model_popup.isVisible():
            if self._model_choices:
                self._sync_popup()
            else:
                self.hidePopup()

    def _sync_popup(self):
        self._model_popup.sync(self._model_choices, self._active_download_key, self._model_theme)

    def showPopup(self):
        if not self._model_choices or not self.isEnabled():
            return
        if self._model_popup is None:
            self._model_popup = _ModelPopup(self)
        self._sync_popup()
        self._model_popup.place()
        self._model_popup.show()
        self._model_popup.focus_current()

    def hidePopup(self):
        if self._model_popup is not None:
            self._model_popup.hide()
        super().hidePopup()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_F4, Qt.Key.Key_Down, Qt.Key.Key_Up,
                           Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.showPopup()
            event.accept()
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        # A wheel over the closed picker should still scroll the studio.
        event.ignore()

    def select_model(self, key):
        index = self.findData(key)
        if index < 0 or not self.model().item(index).isEnabled():
            return
        self.setCurrentIndex(index)
        self.hidePopup()
        self.setFocus(Qt.FocusReason.PopupFocusReason)
        self.activated.emit(index)
        self.textActivated.emit(self.itemText(index))
