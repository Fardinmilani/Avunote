"""Local-first desktop speech studio and opt-in model library."""
import array
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QSize, QUrl, QSignalBlocker
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QIcon, QPixmap, QDesktopServices, QTextOption, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
                               QVBoxLayout, QHBoxLayout, QComboBox, QTextEdit,
                               QFileDialog, QMessageBox, QProgressBar, QStackedWidget,
                               QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
                               QSizePolicy, QGraphicsColorizeEffect)
from model_catalog import (CATALOG, LANGUAGES, get_model, models_for_language,
                           find_local_model, data_root, register_local_root)
from model_downloads import DownloadManager
from model_picker import ModelChoice, ModelPopupMixin
from ui_i18n import (tr, set_language, current_language, UI_LANGUAGES,
                     RTL_LANGUAGES, register_speech_languages, language_title)
from studio_theme import (COLORS, THEMES, ChevronComboBox, animations_enabled, asset_root, load_fonts,
                          native_palette, resolve_theme, stylesheet as theme_stylesheet)
from atomic_files import atomic_write_text, read_text_shared
from app_updates import running_version
from studio_icons import icon

register_speech_languages(LANGUAGES)

FORMATS = {'.wav', '.mp3', '.m4a', '.ogg'}
MODEL_STATES = {
    'idle': 'دانلود نشده', 'resolving': 'آماده‌سازی دانلود', 'downloading': 'در حال دانلود',
    'paused': 'متوقف موقت؛ برای ادامه آماده است', 'verifying': 'بررسی صحت فایل‌ها',
    'completed': 'آماده استفاده آفلاین', 'cancelled': 'دانلود لغو شد',
    'cancelled-pending': 'در حال لغو دانلود', 'error': 'دانلود کامل نشد',
}
DOWNLOAD_IN_PROGRESS = {'resolving', 'downloading', 'verifying'}


class Waveform(QWidget):
    def __init__(self):
        super().__init__()
        self.values = [.02] * 72
        self.active = False
        self.dark = False
        self.setMinimumHeight(40)
        self.setAccessibleName('نمودار سطح صدای میکروفون')

    def push(self, level):
        self.values = self.values[1:] + [max(.02, min(1., level*4))]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = COLORS['dark' if self.dark else 'light']
        middle = self.height()/2
        painter.setPen(QPen(QColor(colors['line_strong']), 1))
        painter.drawLine(0, int(middle), self.width(), int(middle))
        spacing = self.width()/len(self.values)
        painter.setPen(QPen(QColor(colors['signal'] if self.active else colors['wave']), max(1.5, spacing*.42),
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        for index, level in enumerate(self.values):
            height = max(2, level * (self.height()-4))
            x = index*spacing + spacing/2
            painter.drawLine(int(x), int(middle - height/2), int(x), int(middle + height/2))


class TallyLight(QWidget):
    """A broadcast-style tally lamp: dark when idle, signal while recording, ink while processing."""

    def __init__(self):
        super().__init__()
        self.state = 'idle'
        self.dark = False
        self.lit = True
        self.setFixedSize(12, 12)
        self.blink = QTimer(self)
        self.blink.setInterval(650)
        self.blink.timeout.connect(self._toggle)

    def _toggle(self):
        self.lit = not self.lit
        self.update()

    def set_state(self, state):
        if state == self.state:
            return
        self.state = state
        self.lit = True
        if state == 'live' and animations_enabled():
            self.blink.start()
        else:
            self.blink.stop()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = COLORS['dark' if self.dark else 'light']
        color = QColor(colors['signal'] if self.state == 'live' else
                       colors['text'] if self.state == 'busy' else colors['line_strong'])
        if not self.lit:
            color.setAlphaF(.3)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(1, 1, 10, 10)


class Recorder(QThread):
    ready = Signal()
    level = Signal(float)
    recorded = Signal(str, float)
    failed = Signal(str)

    def __init__(self, device, path):
        super().__init__()
        self.device = device
        self.path = Path(path)
        self.stop_event = threading.Event()

    def run(self):
        try:
            import sounddevice as sd
            import wave
            rate = int(sd.query_devices(self.device, 'input')['default_samplerate'])
            samples = 0
            # Blocking reads in a dedicated thread: no disk writes inside an audio callback.
            with sd.RawInputStream(device=self.device, samplerate=rate, channels=1, dtype='int16',
                                   blocksize=1024, latency='high') as stream:
                with wave.open(str(self.path), 'wb') as file:
                    file.setnchannels(1)
                    file.setsampwidth(2)
                    file.setframerate(rate)
                    self.ready.emit()
                    while not self.stop_event.is_set():
                        block, overflowed = stream.read(1024)
                        if overflowed:
                            raise RuntimeError('میکروفون بخشی از صدا را از دست داد؛ ضبط را در سیستم کم‌بارتر تکرار کنید.')
                        file.writeframesraw(bytes(block))
                        values = array.array('h', bytes(block))
                        rms = math.sqrt(sum(value*value for value in values)/max(1, len(values)))/32768
                        self.level.emit(rms)
                        samples += len(values)
            if samples < rate*.25:
                raise RuntimeError('ضبط خیلی کوتاه بود؛ حداقل یک ثانیه صحبت کنید.')
            self.recorded.emit(str(self.path), samples/rate)
        except Exception as exc:
            self.failed.emit(str(exc))


class ComboBox(ChevronComboBox):
    """Keep a clear vector disclosure mark with the custom light Qt stylesheet."""
    SOURCE_ROLE = int(Qt.ItemDataRole.UserRole) + 101
    TOOLTIP_ROLE = int(Qt.ItemDataRole.UserRole) + 102

    def setItemData(self, index, value, role=Qt.ItemDataRole.UserRole):
        if role == Qt.ItemDataRole.ToolTipRole:
            super().setItemData(index, value, self.TOOLTIP_ROLE)
            super().setItemData(index, tr(value), role)
        else:
            super().setItemData(index, value, role)

    def addItem(self, text, userData=None):
        super().addItem(str(text), userData)
        self.setItemData(self.count()-1, str(text), self.SOURCE_ROLE)
        self.retranslate()

    def retranslate(self):
        for index in range(self.count()):
            source = self.itemData(index, self.SOURCE_ROLE)
            if source is None:
                continue
            if self.property('localeSelector'):
                target = source
            elif self.property('speechSelector'):
                item = next((x for x in LANGUAGES if x['code'] == self.itemData(index)), None)
                target = language_title(item) if item else tr(source)
            else:
                target = tr(source)
            self.setItemText(index, target)
            tooltip = self.itemData(index, self.TOOLTIP_ROLE)
            if tooltip is not None:
                super().setItemData(index, tr(tooltip), Qt.ItemDataRole.ToolTipRole)

class ModelComboBox(ModelPopupMixin, ComboBox):
    downloadRequested = Signal(str, str)


class LocalLabel(QLabel):
    def __init__(self, text):
        super().__init__(tr(text))
        self.source_text = text

    def setText(self, text):
        self.source_text = text
        super().setText(str(text) if self.property('literalText') else tr(text))

    def retranslate(self):
        self.setText(self.source_text)
        if hasattr(self, 'source_tooltip'):
            super().setToolTip(tr(self.source_tooltip))

    def setToolTip(self, text):
        self.source_tooltip = text
        super().setToolTip(tr(text))


class LocalButton(QPushButton):
    def __init__(self, text):
        super().__init__(tr(text).replace('&', '&&'))
        self.source_text = text

    def setText(self, text):
        self.source_text = text
        super().setText(tr(text).replace('&', '&&'))

    def retranslate(self):
        self.setText(self.source_text)
        if hasattr(self, 'source_tooltip'):
            super().setToolTip(tr(self.source_tooltip))

    def setToolTip(self, text):
        self.source_tooltip = text
        super().setToolTip(tr(text))


def storage_root():
    path = Path(data_root())
    (path/'results').mkdir(parents=True, exist_ok=True)
    (path/'recordings').mkdir(exist_ok=True)
    return path


def label(text, name=None):
    widget = LocalLabel(text)
    widget.setWordWrap(True)
    widget.setAlignment(Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignVCenter)
    if name:
        widget.setObjectName(name)
    return widget


def button(text, callback, name=None, symbol=None):
    widget = LocalButton(text)
    widget.setMinimumHeight(44)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.clicked.connect(callback)
    if name:
        widget.setObjectName(name)
    if symbol:
        widget.setProperty('symbol', symbol)
        widget.setIcon(icon(symbol, COLORS['light'][ICON_ROLES.get(name, 'muted')]))
        widget.setIconSize(QSize(18, 18))
    return widget


ICON_ROLES = {'primary': 'action_ink', 'record': 'signal_ink', 'accent': 'brand', 'link': 'brand',
              'danger': 'danger', 'secondary': 'text'}


def rule():
    line = QFrame()
    line.setObjectName('rule')
    line.setFixedHeight(1)
    return line



class Studio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = storage_root()
        self.downloads = DownloadManager()
        self.download_widgets = {}
        self.last_library_poll = 0
        self.model_readiness = {}
        self.saved_settings = {}
        try:
            self.saved_settings = json.loads(read_text_shared(self.data/'settings.json'))
            if not isinstance(self.saved_settings, dict):
                self.saved_settings = {}
        except (OSError, ValueError):
            pass
        self.ui_language = self.saved_settings.get('ui_language', 'en')
        if self.ui_language not in dict(UI_LANGUAGES):
            self.ui_language = 'en'
        set_language(self.ui_language)
        self.theme_choice = self.saved_settings.get('theme', 'system')
        if self.theme_choice not in THEMES:
            self.theme_choice = 'system'
        self.resolved_theme = resolve_theme(self.theme_choice, QApplication.styleHints().colorScheme())
        self.star_prompt_seen = bool(self.saved_settings.get('star_prompt_seen', False))
        self.allow_star_prompt = (os.environ.get('AVUNOTE_SUPPRESS_PROMPTS') or os.environ.get('VOXRIVA_SUPPRESS_PROMPTS')) != '1'
        self.process = None
        self.recorder = None
        self.recording = False
        self.mic_ready = False
        self.busy = False
        self.cancelled = False
        self.output = None
        self.last_audio = None
        self.raw_text = ''
        self.started = 0
        self.run_model = None
        self.run_language = 'azb'
        self.recording_target = 'studio'
        self.transcription_target = 'studio'
        self.ai_output = None
        self.closing = False
        self.updates = None
        self.version_text = f'Avunote {running_version()}'
        self.setWindowTitle(tr('Avunote — استودیوی گفتار آفلاین'))
        self.setWindowIcon(QIcon(self.brand_pixmap(True)))
        self.resize(1280, 880)
        self.setMinimumSize(940, 660)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.ui_language in RTL_LANGUAGES else Qt.LayoutDirection.LeftToRight)
        self.setAcceptDrops(True)
        self.build()
        self.centralWidget().setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.centralWidget().setFocus(Qt.FocusReason.OtherFocusReason)
        self.apply_theme()
        QApplication.styleHints().colorSchemeChanged.connect(self.system_theme_changed)
        QShortcut(QKeySequence('Ctrl+O'), self, activated=self.choose_file)
        QShortcut(QKeySequence('Escape'), self, activated=self.cancel)
        QShortcut(QKeySequence('Ctrl+,'), self, activated=lambda: self.show_page(4))
        for number, page in ((1, 0), (2, 3), (3, 2), (4, 1)):
            QShortcut(QKeySequence(f'Ctrl+{number}'), self, activated=lambda page=page: self.show_page(page))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(150)
        self.refresh_devices()
        self.refresh_history()
        index = self.language.findData(self.saved_settings.get('language', 'azb'))
        with QSignalBlocker(self.language):
            self.language.setCurrentIndex(max(0, index))
        self.language_changed()
        self.refresh_library()
        self.retranslate_ui()

    def brand_pixmap(self, mark_only=False):
        asset = 'avunote-mark.png' if mark_only else 'avunote-logo-transparent.png'
        return QPixmap(str(asset_root()/'assets'/asset))

    def build(self):
        shell = QWidget()
        shell.setObjectName('shell')
        self.setCentralWidget(shell)
        outer = QVBoxLayout(shell)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        bar = QFrame()
        bar.setObjectName('topBar')
        bar.setFixedHeight(60)
        top = QHBoxLayout(bar)
        top.setContentsMargins(24, 0, 14, 0)
        top.setSpacing(0)
        self.brand_label = QLabel()
        self.brand_label.setAccessibleName('Avunote')
        self.brand_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        brand = self.brand_pixmap().scaled(204, 56, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)
        brand.setDevicePixelRatio(2)
        self.brand_label.setPixmap(brand)
        top.addWidget(self.brand_label)
        top.addSpacing(10)
        self.tally = TallyLight()
        top.addWidget(self.tally, 0, Qt.AlignmentFlag.AlignVCenter)
        top.addSpacing(26)

        self.studio_nav = button('استودیوی گفتار', lambda: self.show_page(0), 'nav')
        self.history_nav = button('تاریخچه', lambda: self.show_page(1), 'nav')
        self.library_nav = button('کتابخانه مدل‌ها', lambda: self.show_page(2), 'nav')
        self.ai_nav = button('گفت‌وگوی AI', lambda: self.show_page(3), 'nav')
        self.settings_nav = button('Settings', lambda: self.show_page(4), 'nav', 'gear')
        self.navigation = (self.studio_nav, self.history_nav, self.library_nav, self.ai_nav, self.settings_nav)
        for item in self.navigation:
            item.setCheckable(True)
            item.setFixedHeight(60)
        for shortcut, item in enumerate((self.studio_nav, self.ai_nav, self.library_nav, self.history_nav), 1):
            item.setToolTip(f'Ctrl+{shortcut}')
            top.addWidget(item)
        top.addStretch()
        self.update_indicator = button('Update available', self.open_updates, 'accent', 'download')
        self.update_indicator.setMinimumHeight(36)
        self.update_indicator.setMaximumHeight(36)
        self.update_indicator.hide()
        top.addWidget(self.update_indicator, 0, Qt.AlignmentFlag.AlignVCenter)
        top.addSpacing(12)
        version = label(self.version_text, 'meta')
        version.setWordWrap(False)
        top.addWidget(version, 0, Qt.AlignmentFlag.AlignVCenter)
        top.addSpacing(6)
        top.addWidget(self.settings_nav)
        outer.addWidget(bar)

        self.pages = QStackedWidget()
        self.pages.setObjectName('workspace')
        outer.addWidget(self.pages, 1)
        self.build_studio()
        self.build_history()
        self.build_library()

        from ai_panel import AIPage
        self.ai_page = AIPage(lambda: self.raw_text, parent=self)
        if hasattr(self.ai_page, 'record_requested'):
            self.ai_page.record_requested.connect(self.record_chat_voice)
            self.ai_page.audio_requested.connect(self.choose_chat_audio)
            self.ai_page.settings_requested.connect(lambda: self.show_page(0))
            self.ai_page.cancel_voice_requested.connect(self.cancel)
        self.pages.addWidget(self.ai_page)
        self.build_settings()
        self.studio_nav.setChecked(True)

    @staticmethod
    def title_row(title, *actions):
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(label(title, 'heading'), 1)
        for action in actions:
            row.addWidget(action)
        return row

    @staticmethod
    def field(layout, title, control):
        group = QVBoxLayout()
        group.setSpacing(6)
        caption = label(title, 'fieldLabel')
        caption.setBuddy(control)
        group.addWidget(caption)
        group.addWidget(control)
        layout.addLayout(group)
        return caption

    @staticmethod
    def page_layout(page, spacing=18):
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 24)
        layout.setSpacing(spacing)
        return layout

    def build_studio(self):
        page = QWidget()
        page.setObjectName('page')
        split = QHBoxLayout(page)
        split.setContentsMargins(0, 0, 0, 0)
        split.setSpacing(0)

        console = QFrame()
        console.setObjectName('console')
        console.setFixedWidth(320)
        column = QVBoxLayout(console)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName('consoleBody')
        config = QVBoxLayout(body)
        config.setContentsMargins(24, 26, 24, 16)
        config.setSpacing(16)
        self.language = ComboBox()
        self.language.setProperty('speechSelector', True)
        self.language.setMinimumContentsLength(12)
        self.language.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        for item in LANGUAGES:
            self.language.addItem(item['title'], item['code'])
        self.language.currentIndexChanged.connect(self.language_changed)
        self.model = ModelComboBox()
        self.model.downloadRequested.connect(self.download_action)
        self.model.setAccessibleName('مدل تشخیص گفتار')
        self.model.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.model.setMinimumContentsLength(16)
        self.model.setIconSize(QSize(18, 18))
        self.model.setPlaceholderText(tr('هیچ مدل نصب‌شده‌ای نیست'))
        self.model.currentIndexChanged.connect(self.selection_changed)
        self.field(config, 'زبان گفتار', self.language)
        self.field(config, 'مدل', self.model)

        self.model_notice = label('وضعیت مدل در حال بررسی است.', 'modelNotice')
        config.addWidget(self.model_notice)
        self.library_button = button('دریافت مدل', self.open_selected_library, 'accent', 'download')
        config.addWidget(self.library_button)
        config.addWidget(rule())
        self.advanced_button = button('گزینه‌های پردازش', self.toggle_processing_options, 'quiet', 'tune')
        self.advanced_button.setCheckable(True)
        config.addWidget(self.advanced_button, 0, Qt.AlignmentFlag.AlignLeading)
        self.build_processing_options(config)
        config.addStretch()
        settings_scroll.setWidget(body)
        column.addWidget(settings_scroll, 1)

        dock = QFrame()
        dock.setObjectName('deck')
        dock_layout = QVBoxLayout(dock)
        dock_layout.setContentsMargins(24, 18, 24, 22)
        dock_layout.setSpacing(10)
        self.wave = Waveform()
        self.wave.setFixedHeight(40)
        self.wave.hide()
        dock_layout.addWidget(self.wave)
        self.record_button = button('شروع ضبط', self.toggle_recording, 'record', 'mic')
        self.record_button.setFixedHeight(52)
        dock_layout.addWidget(self.record_button)
        self.choose_button = button('Open audio', self.choose_file, 'secondary', 'folder')
        self.choose_button.setToolTip('WAV · MP3 · M4A · OGG  ·  Ctrl+O')
        dock_layout.addWidget(self.choose_button)
        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        self.devices = ComboBox()
        self.devices.setMinimumContentsLength(8)
        self.devices.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.devices.currentTextChanged.connect(self.devices.setToolTip)
        input_row.addWidget(self.devices, 1)
        self.refresh_button = button('', self.refresh_devices, 'quiet', 'refresh')
        self.refresh_button.setFixedWidth(44)
        self.refresh_button.setToolTip('بازخوانی میکروفون‌ها')
        input_row.addWidget(self.refresh_button)
        dock_layout.addLayout(input_row)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.hide()
        dock_layout.addWidget(self.progress)
        self.status = label('آماده برای شنیدن؛ فایل یا میکروفون را انتخاب کنید.', 'muted')
        dock_layout.addWidget(self.status)
        self.source_name = label('', 'meta')
        self.source_name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.source_name.hide()
        dock_layout.addWidget(self.source_name)
        self.cancel_button = button('توقف تبدیل', self.cancel, 'danger', 'stop')
        self.cancel_button.hide()
        dock_layout.addWidget(self.cancel_button)
        column.addWidget(dock)
        split.addWidget(console)

        document = QWidget()
        document.setObjectName('page')
        main = QVBoxLayout(document)
        main.setContentsMargins(40, 30, 40, 22)
        main.setSpacing(14)
        self.copy_button = button('کپی', self.copy_text, 'quiet', 'copy')
        self.save_button = button('ذخیره متن', self.save_text, 'quiet', 'download')
        self.retry_button = button('تبدیل دوباره', self.retry, 'quiet', 'refresh')
        self.ai_button = button('Ask AI', self.discuss_transcript, 'accent', 'chat')
        self.result_model = label('', 'meta')
        self.result_model.setProperty('literalText', True)
        self.result_model.setWordWrap(False)
        main.addLayout(self.title_row('استودیوی گفتار', self.result_model))
        main.addSpacing(6)
        caption = QHBoxLayout()
        caption.setSpacing(4)
        caption.addWidget(label('Transcript', 'fieldLabel'), 1)
        for action in (self.copy_button, self.save_button, self.retry_button, self.ai_button):
            action.setEnabled(False)
            caption.addWidget(action)
        main.addLayout(caption)
        main.addWidget(rule())

        self.text = QTextEdit()
        self.text.setObjectName('transcript')
        self.text.setReadOnly(True)
        self.text.document().setDocumentMargin(14)
        transcript_view = QStackedWidget()
        transcript_view.setMinimumHeight(160)
        empty_view = QWidget()
        empty_view.setObjectName('transcriptEmpty')
        empty = QVBoxLayout(empty_view)
        empty.setContentsMargins(14, 14, 14, 14)
        empty.setSpacing(10)
        self.transcript_glyph = QLabel()
        self.transcript_glyph.setObjectName('emptyGlyph')
        self.transcript_glyph.setFixedSize(72, 72)
        self.transcript_glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.addStretch()
        empty.addWidget(self.transcript_glyph, 0, Qt.AlignmentFlag.AlignHCenter)
        title = label('No transcript yet', 'display')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.addWidget(title)
        hint = label('برای شروع، فایل صوتی انتخاب کنید یا ضبط کنید.', 'muted')
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.addWidget(hint)
        formats = label('WAV · MP3 · M4A · OGG  ·  Ctrl+O', 'meta')
        formats.setProperty('literalText', True)
        formats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.addWidget(formats)
        empty.addStretch()
        transcript_view.addWidget(empty_view)
        transcript_view.addWidget(self.text)
        self.text.textChanged.connect(
            lambda: transcript_view.setCurrentIndex(0 if self.text.document().isEmpty() else 1))
        main.addWidget(transcript_view, 1)

        self.metrics_label = label('', 'meta')
        main.addWidget(self.metrics_label)
        self.result_model.hide()
        self.metrics_label.hide()
        self.text.textChanged.connect(
            lambda: self.result_model.setVisible(not self.text.document().isEmpty()))
        self.text.textChanged.connect(
            lambda: self.metrics_label.setVisible(not self.text.document().isEmpty()))
        split.addWidget(document, 1)
        self.pages.addWidget(page)

    def build_processing_options(self, parent_layout):
        self.processing_options = QWidget()
        grid = QVBoxLayout(self.processing_options)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(14)
        self.mode = ComboBox()
        self.mode.addItem('دقت بیشتر', 5)
        self.mode.addItem('سریع‌تر', 1)
        self.compute_device = ComboBox()
        for title, key in [('خودکار؛ در صورت خطا CPU', 'auto'), ('CPU', 'cpu'),
                           ('NVIDIA CUDA', 'cuda'), ('NPU؛ در صورت ناسازگاری CPU', 'npu')]:
            self.compute_device.addItem(title, key)
        index = self.compute_device.findData(self.saved_settings.get('device', 'auto'))
        self.compute_device.setCurrentIndex(max(0, index))
        self.chunk_seconds = ComboBox()
        for seconds in (10, 15, 20, 25, 30):
            self.chunk_seconds.addItem(f'{seconds} s', seconds)
        index = self.chunk_seconds.findData(self.saved_settings.get('chunk_seconds', 20))
        self.chunk_seconds.setCurrentIndex(index if index >= 0 else 2)
        self.field(grid, 'حالت پردازش', self.mode)
        self.field(grid, 'دستگاه پردازش', self.compute_device)
        self.field(grid, 'مدت هر بخش صوت', self.chunk_seconds)
        self.compute_notice = label('', 'muted')
        grid.addWidget(self.compute_notice)
        self.compute_device.currentIndexChanged.connect(self.compute_choice_changed)
        self.chunk_seconds.currentIndexChanged.connect(lambda *_: self.save_settings())
        self.processing_options.hide()
        parent_layout.addWidget(self.processing_options)

    def build_history(self):
        page = QWidget()
        page.setObjectName('page')
        layout = self.page_layout(page)
        folder = button('پوشه متن‌ها و ضبط‌ها',
                        lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.data))),
                        'quiet', 'folder')
        reload = button('بازخوانی', self.refresh_history, 'quiet', 'refresh')
        layout.addLayout(self.title_row('تاریخچه', folder, reload))
        self.history_view = QStackedWidget()
        empty = QWidget()
        empty.setObjectName('page')
        empty_layout = QVBoxLayout(empty)
        empty_layout.setSpacing(12)
        empty_layout.addStretch()
        self.history_glyph = QLabel()
        self.history_glyph.setObjectName('emptyGlyph')
        self.history_glyph.setFixedSize(72, 72)
        self.history_glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.history_glyph, 0, Qt.AlignmentFlag.AlignHCenter)
        empty_title = label('No transcripts yet', 'display')
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)
        empty_layout.addStretch()
        self.history_view.addWidget(empty)
        self.table = QTableWidget(0, 5)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignVCenter)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.verticalHeader().hide()
        self.table.cellDoubleClicked.connect(self.load_history)
        self.history_view.addWidget(self.table)
        layout.addWidget(self.history_view, 1)
        self.open_history_button = button('Open transcript', self.open_history_selection, 'primary', 'file')
        self.open_history_button.setEnabled(False)
        self.table.itemSelectionChanged.connect(
            lambda: self.open_history_button.setEnabled(self.table.currentRow() >= 0))
        QShortcut(QKeySequence('Return'), self.table, activated=self.open_history_selection,
                  context=Qt.ShortcutContext.WidgetShortcut)
        layout.addWidget(self.open_history_button, 0, Qt.AlignmentFlag.AlignTrailing)
        self.pages.addWidget(page)

    def open_history_selection(self):
        row = self.table.currentRow()
        if row >= 0:
            self.load_history(row, 0)

    def build_settings(self):
        page = QWidget()
        page.setObjectName('page')
        layout = self.page_layout(page, 0)
        layout.addLayout(self.title_row('Settings'))
        layout.addSpacing(26)
        self.theme_selector = ComboBox()
        for title, key in [('هماهنگ با سیستم', 'system'), ('روشن', 'light'), ('تاریک', 'dark')]:
            self.theme_selector.addItem(title, key)
        self.theme_selector.setCurrentIndex(self.theme_selector.findData(self.theme_choice))
        self.theme_selector.currentIndexChanged.connect(self.theme_changed)
        self.interface_language = ComboBox()
        self.interface_language.setProperty('localeSelector', True)
        for code, native in UI_LANGUAGES:
            self.interface_language.addItem(native, code)
        self.interface_language.setCurrentIndex(self.interface_language.findData(self.ui_language))
        self.interface_language.currentIndexChanged.connect(self.interface_changed)
        sections = QWidget()
        sections.setObjectName('page')
        sections.setMaximumWidth(820)
        rows = QVBoxLayout(sections)
        rows.setContentsMargins(0, 0, 0, 0)
        rows.setSpacing(0)

        def setting(title, control, detail=None):
            row = QFrame()
            row.setObjectName('settingsRow')
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 18, 0, 18)
            line.setSpacing(24)
            text = QVBoxLayout()
            text.setSpacing(4)
            caption = label(title, 'cardTitle')
            caption.setBuddy(control)
            text.addWidget(caption)
            if detail is not None:
                text.addWidget(detail)
            line.addLayout(text, 1)
            control.setFixedWidth(300)
            line.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
            rows.addWidget(row)

        setting('ظاهر برنامه', self.theme_selector)
        setting('زبان رابط کاربری', self.interface_language)
        setting('Updates', button('Check for updates', self.open_updates, 'secondary', 'refresh'),
                label(self.version_text, 'meta'))
        about = QFrame()
        about.setObjectName('settingsRow')
        about_row = QHBoxLayout(about)
        about_row.setContentsMargins(0, 14, 0, 0)
        about_row.addWidget(button('درباره و مجوزها', self.about, 'link'), 0, Qt.AlignmentFlag.AlignLeading)
        about_row.addStretch()
        rows.addWidget(about)
        holder = QHBoxLayout()
        holder.addWidget(sections, 1)
        holder.addStretch(0)
        layout.addLayout(holder)
        layout.addStretch()
        self.pages.addWidget(page)

    def update_controller(self):
        if self.updates is None:
            from update_panel import UpdateController
            self.updates = UpdateController(self, request_close=self.close_for_update)
            self.updates.available.connect(lambda version: self.update_indicator.show())
        return self.updates

    def open_updates(self):
        self.update_controller().open_dialog()

    def close_for_update(self):
        chat_active = getattr(self.ai_page, '_active', lambda: False)
        return not (self.busy or self.recording or chat_active()) and self.close()


    def show_page(self, index):
        focus = QApplication.focusWidget()
        self.pages.setCurrentIndex(index)
        for page, navigation in enumerate(self.navigation):
            navigation.setChecked(index == page)
        if focus in self.navigation:
            self.navigation[index].setFocus(Qt.FocusReason.OtherFocusReason)
        self.brand_label.update()
        if index == 1:
            self.refresh_history()
        if index == 2:
            self.refresh_library()

    def discuss_transcript(self):
        """Select context for the AI page; only its Send action may transmit it."""
        if not self.raw_text:
            return
        source = self.output.name if self.output else ''
        self.ai_page.set_transcript(self.raw_text, source)
        self.show_page(3)

    def toggle_processing_options(self, checked=False):
        self.processing_options.setVisible(bool(checked))

    def refresh_compute_options(self):
        if not self.model.currentData():
            self.compute_choice_changed()
            return
        try:
            from compute_devices import device_options
            options = device_options(self.model.currentData(), probe=False)
            by_key = {row.get('key', row.get('id')): row for row in options}
            for index in range(self.compute_device.count()):
                row = by_key.get(self.compute_device.itemData(index), {})
                if row.get('reason'):
                    self.compute_device.setItemData(index, row['reason'], Qt.ItemDataRole.ToolTipRole)
            self.compute_choice_changed()
        except (ImportError, TypeError, ValueError):
            pass

    def compute_choice_changed(self, *args):
        key = self.compute_device.currentData()
        model = get_model(self.model.currentData()) if self.model.currentData() else {}
        notices = {
            'auto': 'سازگاری شتاب‌دهنده هنگام اجرا بررسی می‌شود؛ مدل‌ها خودکار دانلود نمی‌شوند.',
            'cpu': 'پردازش محلی روی CPU انجام می‌شود.',
            'cuda': 'GPU به درایور و محیط CUDA سازگار نیاز دارد؛ در صورت خطا پردازش روی CPU ادامه می‌یابد.',
            'npu': 'NPU به مدل و محیط OpenVINO سازگار نیاز دارد؛ در صورت ناسازگاری CPU استفاده می‌شود.',
        }
        notice = 'این مدل همیشه روی CPU اجرا می‌شود.' if model.get('cpu_only') else notices.get(key, notices['auto'])
        self.compute_notice.setText(notice)
        detail = self.compute_device.itemData(self.compute_device.currentIndex(), Qt.ItemDataRole.ToolTipRole)
        if detail:
            self.compute_notice.setToolTip(detail)
        self.save_settings()

    def theme_changed(self, *args):
        self.theme_choice = self.theme_selector.currentData() or 'system'
        self.apply_theme()
        self.save_settings()

    def system_theme_changed(self, *args):
        if self.theme_choice == 'system':
            self.apply_theme()

    def color_action_icon(self, widget):
        symbol = widget.property('symbol')
        if not symbol:
            return
        colors = COLORS[self.resolved_theme]
        role = ICON_ROLES.get(widget.objectName(), 'muted')
        if widget is getattr(self, 'record_button', None) and self.recording:
            symbol = 'stop'
        artwork = icon(symbol, colors[role])
        artwork.addPixmap(icon(symbol, colors['disabled_ink']).pixmap(32, 32), QIcon.Mode.Disabled)
        widget.setIcon(artwork)

    def apply_theme(self):
        self.resolved_theme = resolve_theme(self.theme_choice, QApplication.styleHints().colorScheme())
        colors = COLORS[self.resolved_theme]
        self.setPalette(native_palette(self.resolved_theme))
        self.setStyleSheet(theme_stylesheet(self.resolved_theme, rtl=self.ui_language in RTL_LANGUAGES))
        for glyph in (self.transcript_glyph, self.history_glyph):
            glyph.setPixmap(icon('wave', colors['faint']).pixmap(56, 56))
        dark = self.resolved_theme == 'dark'
        self.wave.dark = self.tally.dark = dark
        self.wave.update()
        self.tally.update()
        for widget in self.findChildren(LocalButton):
            self.color_action_icon(widget)
        # The Signal direction renders the wordmark monochrome in ink on both themes.
        effect = self.brand_label.graphicsEffect()
        if not isinstance(effect, QGraphicsColorizeEffect):
            effect = QGraphicsColorizeEffect(self.brand_label)
            self.brand_label.setGraphicsEffect(effect)
        effect.setColor(QColor(colors['text']))
        effect.setStrength(1.0)
        self.setWindowIcon(QIcon(self.brand_pixmap(True)))
        if hasattr(self, 'ai_page') and hasattr(self.ai_page, 'apply_theme'):
            self.ai_page.apply_theme(self.resolved_theme)
        self.refresh_model_picker()

    def interface_changed(self, *args):
        code = self.interface_language.currentData()
        if not code:
            return
        self.ui_language = code
        set_language(code)
        self.retranslate_ui()
        self.save_settings()

    def retranslate_ui(self):
        """Update text in place; keep speech, recording and download state intact."""
        direction = Qt.LayoutDirection.RightToLeft if self.ui_language in RTL_LANGUAGES else Qt.LayoutDirection.LeftToRight
        QApplication.instance().setLayoutDirection(direction)
        self.setLayoutDirection(direction)
        self.apply_theme()
        self.setWindowTitle(tr('Avunote — استودیوی گفتار آفلاین'))
        for widget in self.findChildren(LocalLabel) + self.findChildren(LocalButton):
            widget.retranslate()
        for widget in self.findChildren(ComboBox):
            widget.retranslate()
        self.refresh_model_picker()
        for item in self.download_widgets.values():
            bar = item['bar']
            source = bar.property('sourceAccessibleName')
            if source:
                bar.setAccessibleName(tr(source))
        self.text.setPlaceholderText(tr('اینجا، صدای شما به کلمات تبدیل می‌شود…\n\nبرای شروع، یک فایل انتخاب کنید یا ضبط را بزنید.'))
        self.retry_button.setToolTip('همین فایل را با زبان و مدل انتخاب‌شده دوباره پردازش کنید.')
        self.table.setHorizontalHeaderLabels([tr(x) for x in ['فایل / ضبط', 'مدل', 'مدت صوت', 'زمان تبدیل', 'تاریخ']])
        for widget, source in [(self.language, 'زبان گفتار'), (self.model, 'مدل تشخیص گفتار'),
                               (self.mode, 'کیفیت پردازش'), (self.devices, 'انتخاب میکروفون'),
                               (self.text, 'متن خام خروجی مدل'), (self.wave, 'نمودار سطح صدای میکروفون'),
                               (self.refresh_button, 'بازخوانی میکروفون‌ها'),
                               (self.library_language, 'فیلتر زبان کتابخانه')]:
            widget.setAccessibleName(tr(source))
        self.interface_language.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.update_transcript_direction()
        self.brand_label.repaint()
        self.interface_language.repaint()
        if hasattr(self, 'ai_page') and hasattr(self.ai_page, 'retranslate_ui'):
            self.ai_page.retranslate_ui()
        if self.updates is not None:
            self.updates.retranslate_ui()
        self.update()

    def update_transcript_direction(self, language=None):
        code = language or (self.run_language if self.raw_text else self.language.currentData())
        direction = Qt.LayoutDirection.RightToLeft if code in {'azb', 'fa', 'ar', 'ur', 'he', 'ps', 'sd', 'yi'} else Qt.LayoutDirection.LeftToRight
        self.text.setLayoutDirection(direction)
        option = self.text.document().defaultTextOption()
        option.setTextDirection(direction)
        option.setAlignment(Qt.AlignmentFlag.AlignRight if direction == Qt.LayoutDirection.RightToLeft else Qt.AlignmentFlag.AlignLeft)
        self.text.document().setDefaultTextOption(option)
        script = 'rtl' if direction == Qt.LayoutDirection.RightToLeft else 'ltr'
        if self.text.property('script') != script:
            self.text.setProperty('script', script)
            self.text.style().unpolish(self.text)
            self.text.style().polish(self.text)

    def language_changed(self, *args):
        if not hasattr(self, 'model_notice'):
            return
        previous = self.model.currentData() or self.saved_settings.get('model')
        with QSignalBlocker(self.model):
            self.model.clear()
            for item in models_for_language(self.language.currentData()):
                key = item['key']
                self.model_readiness[key] = find_local_model(key) is not None
                self.model.addItem(f'{item["title"]}  ·  {item["size"]}', key)
            self.model.setCurrentIndex(-1)
            self.refresh_model_picker(preferred=previous)
        self.selection_changed()

    @staticmethod
    def model_status(item, snapshot, ready):
        state = snapshot.get('status', 'idle')
        if ready:
            state = 'completed'
        elif not isinstance(state, str) or state == 'completed' or state not in MODEL_STATES:
            # A download receipt can survive after the actual files are removed.
            state = 'idle'
        try:
            done = float(snapshot.get('bytes_done', 0) or 0)
            total = float(snapshot.get('bytes_total', 0) or item['bytes'])
        except (TypeError, ValueError):
            done, total = 0., float(item['bytes'])
        percent = max(0., min(100., 100*done/total)) if total > 0 else 0.
        return state, done, total, percent

    def refresh_model_picker(self, preferred=None):
        """Keep the available selection and visible download rows in sync."""
        combo = self.model
        combo.setPlaceholderText(tr('هیچ مدل نصب‌شده‌ای نیست'))
        if not combo.count():
            combo.set_model_rows((), None, self.resolved_theme)
            return False
        before = combo.currentData()
        active_key = self.downloads.active_key()
        standard_model = combo.model()
        activity = None
        installed = []
        choices = []
        with QSignalBlocker(combo):
            for index in range(combo.count()):
                key = combo.itemData(index)
                item = get_model(key)
                ready = self.model_readiness.get(key, False)
                state, _, _, percent = self.model_status(item, self.downloads.snapshot(key), ready)
                status = MODEL_STATES[state]
                if state in DOWNLOAD_IN_PROGRESS | {'paused'}:
                    status += f'  ·  {percent:.0f}%'
                if state in DOWNLOAD_IN_PROGRESS:
                    activity = status
                row = standard_model.item(index)
                if row.isEnabled() != ready:
                    row.setEnabled(ready)
                    row.setSelectable(ready)
                if ready:
                    installed.append(index)
                title = combo.itemData(index, ComboBox.SOURCE_ROLE)
                text = tr(title if ready else title + '  ·  ' + status)
                if row.text() != text:
                    row.setText(text)
                detail = tr(item['detail'])
                translated_status = tr(status)
                tooltip = detail + '\n' + translated_status
                if row.toolTip() != tooltip:
                    row.setToolTip(tooltip)
                choices.append(ModelChoice(key, tr(title), detail, translated_status, state, ready, percent))

            # An in-progress recording or transcription keeps the model it started with.
            if not (self.busy or self.recording) or before is None:
                default = 'whisper-base-full' if self.language.currentData() == 'azb' else 'multilingual-base'
                preferred_keys = (preferred, before, self.saved_settings.get('model'), default)
                selection = installed[0] if installed else -1
                for key in preferred_keys:
                    index = combo.findData(key)
                    if index in installed:
                        selection = index
                        break
                if combo.currentIndex() != selection:
                    combo.setCurrentIndex(selection)

        combo.set_model_rows(choices, active_key, self.resolved_theme)
        key = combo.currentData()
        ready = self.model_readiness.get(key, False)
        metadata = get_model(key) if key else {}
        if ready:
            notice = 'مدل آماده است؛ تبدیل بدون اینترنت انجام می‌شود.'
            if metadata.get('automatic_language'):
                notice += '  ·  زبان گفتار به‌صورت خودکار تشخیص داده می‌شود.'
            tone = 'ready'
        elif activity:
            notice = activity + '  ·  تبدیل گفتار پس از آماده‌شدن مدل فعال می‌شود.'
            tone = 'info'
        else:
            notice = 'Download a model using the icon in the list.'
            tone = 'warning'
        if self.model_notice.source_text != notice:
            self.model_notice.setText(notice)
        if self.model_notice.property('tone') != tone:
            self.model_notice.setProperty('tone', tone)
            self.model_notice.style().unpolish(self.model_notice)
            self.model_notice.style().polish(self.model_notice)
        self.library_button.setVisible(not ready)
        ready_prompt = 'آماده برای شنیدن؛ فایل یا میکروفون را انتخاب کنید.'
        waiting_prompt = 'تبدیل گفتار پس از آماده‌شدن مدل فعال می‌شود.'
        missing_prompt = 'ابتدا مدل این زبان را دریافت کنید یا پوشه مدل محلی را معرفی کنید.'
        idle_prompts = {'', ready_prompt, waiting_prompt, missing_prompt,
                        'مدل آماده است؛ فایل صوتی را انتخاب کنید یا ضبط را شروع کنید.'}
        if hasattr(self, 'status') and self.status.source_text in idle_prompts:
            footer = ready_prompt if ready else ''
            if self.status.source_text != footer:
                self.status.setText(footer)
        return before != key

    def selection_changed(self, *args):
        if not hasattr(self, 'model_notice'):
            return
        self.refresh_model_picker()
        self.controls()
        self.refresh_compute_options()
        self.update_transcript_direction()

    def save_settings(self):
        if not hasattr(self, 'compute_device') or not hasattr(self, 'chunk_seconds'):
            return False
        payload = dict(self.saved_settings)
        payload.update({'language': self.language.currentData(),
                        'ui_language': self.ui_language, 'theme': self.theme_choice,
                        'star_prompt_seen': self.star_prompt_seen,
                        'device': self.compute_device.currentData(),
                        'chunk_seconds': self.chunk_seconds.currentData()})
        key = self.model.currentData()
        if key and self.model_readiness.get(key):
            payload['model'] = key
        try:
            atomic_write_text(self.data/'settings.json', json.dumps(payload, ensure_ascii=False, indent=2))
            self.saved_settings = payload
            return True
        except OSError:
            return False

    def open_selected_library(self):
        index = self.library_language.findData(self.language.currentData())
        if index >= 0:
            self.library_language.setCurrentIndex(index)
        self.show_page(2)

    def build_library(self):
        page = QWidget()
        page.setObjectName('page')
        layout = self.page_layout(page, 16)
        local = button('افزودن مدل محلی', self.import_local_models, 'quiet', 'folder')
        layout.addLayout(self.title_row('کتابخانه مدل‌ها', local))
        filters = QHBoxLayout()
        filters.setSpacing(14)
        filter_label = label('زبان گفتار', 'fieldLabel')
        filter_label.setWordWrap(False)
        self.library_language = ComboBox()
        self.library_language.setProperty('speechSelector', True)
        self.library_language.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.library_language.setMinimumContentsLength(18)
        for item in LANGUAGES:
            self.library_language.addItem(item['title'], item['code'])
        filter_label.setBuddy(self.library_language)
        filters.addWidget(filter_label)
        filters.addWidget(self.library_language)
        filters.addStretch()
        layout.addLayout(filters)
        layout.addWidget(rule())
        self.library_scroll = QScrollArea()
        self.library_scroll.setWidgetResizable(True)
        self.library_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.library_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.library_body = QWidget()
        self.library_body.setObjectName('page')
        self.library_cards = QVBoxLayout(self.library_body)
        self.library_cards.setContentsMargins(0, 0, 4, 0)
        self.library_cards.setSpacing(0)
        self.library_scroll.setWidget(self.library_body)
        layout.addWidget(self.library_scroll, 1)
        self.library_footer = label('', 'muted')
        self.library_footer.hide()
        layout.addWidget(self.library_footer)
        self.pages.addWidget(page)
        self.library_language.currentIndexChanged.connect(self.rebuild_library)
        self.rebuild_library()

    def rebuild_library(self, *args):
        while self.library_cards.count():
            entry = self.library_cards.takeAt(0)
            if entry.widget():
                entry.widget().hide()
                entry.widget().deleteLater()
        self.download_widgets = {}
        language = self.library_language.currentData()
        for item in models_for_language(language):
            key = item['key']
            card = QFrame()
            card.setObjectName('modelCard')
            content = QVBoxLayout(card)
            content.setContentsMargins(2, 18, 2, 18)
            content.setSpacing(10)
            row = QHBoxLayout()
            row.setSpacing(8)
            summary = QVBoxLayout()
            summary.setSpacing(4)
            summary.addWidget(label(item['title'].replace('AZB · ', '').replace(' · چندزبانه', ''), 'libraryTitle'))
            summary.addWidget(label(' · '.join(filter(None, (item.get('family'), item['size']))), 'meta'))
            status = label('دانلود نشده', 'modelStatus')
            status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            summary.addWidget(status)
            row.addLayout(summary, 1)

            start = button('دانلود مدل', lambda checked=False, k=key: self.download_action(k, 'start'),
                           'secondary', 'download')
            pause = button('توقف موقت', lambda checked=False, k=key: self.download_action(k, 'pause'), 'quiet')
            cancel = button('لغو دانلود', lambda checked=False, k=key: self.download_action(k, 'cancel'), 'quiet')
            use = button('استفاده از مدل', lambda checked=False, k=key: self.use_model(k), 'accent')
            disclosure = button('', lambda: None, 'quiet', 'more')
            disclosure.setFixedWidth(44)
            disclosure.setCheckable(True)
            disclosure.setToolTip('جزئیات مدل و مجوزها')
            disclosure.setAccessibleName(tr('جزئیات مدل و مجوزها'))
            for action in (start, pause, cancel, use, disclosure):
                self.color_action_icon(action)
                row.addWidget(action, 0, Qt.AlignmentFlag.AlignVCenter)
            content.addLayout(row)

            bar = QProgressBar()
            bar.setObjectName('downloadProgress')
            bar.setRange(0, 1000)
            bar.setTextVisible(False)
            bar.setProperty('sourceAccessibleName', f'پیشرفت دانلود {item["title"]}')
            bar.setAccessibleName(tr(f'پیشرفت دانلود {item["title"]}'))
            content.addWidget(bar)

            details = QFrame()
            details.setObjectName('disclosure')
            details_layout = QVBoxLayout(details)
            details_layout.setContentsMargins(16, 12, 16, 12)
            details_layout.setSpacing(6)
            details_layout.addWidget(label(item['detail'], 'muted'))
            details_layout.addWidget(label(f'مجوز: {item.get("license", "مشاهده در منبع")}  ·  پردازش روی CPU', 'muted'))
            if item.get('automatic_language'):
                details_layout.addWidget(label('زبان گفتار به‌صورت خودکار تشخیص داده می‌شود.', 'muted'))
            if item['backend'] == 'transformers':
                details_layout.addWidget(label('مدل آذربایجانی جنوبی · مؤسسه Kartal Ol', 'muted'))
                details_layout.addWidget(button('Kartal Ol / GitHub', lambda: QDesktopServices.openUrl(QUrl('https://github.com/Kartalol')), 'link'))
            details_layout.addWidget(button('مشاهده منبع و شرایط مدل', lambda checked=False, url=item['url']: QDesktopServices.openUrl(QUrl(url)), 'link'))
            if item.get('license_url') and item['license_url'] != item['url']:
                details_layout.addWidget(button('مشاهده مجوز مدل', lambda checked=False, url=item['license_url']: QDesktopServices.openUrl(QUrl(url)), 'link'))
            details.hide()
            disclosure.toggled.connect(details.setVisible)
            content.addWidget(details)
            self.library_cards.addWidget(card)
            self.download_widgets[key] = {'bar': bar, 'status': status, 'start': start, 'pause': pause,
                                          'cancel': cancel, 'use': use}
        self.library_cards.addStretch(1)
        self.refresh_library()


    @staticmethod
    def format_bytes(value):
        value = max(0, float(value or 0))
        if value >= 1_000_000_000:
            return f'{value/1_000_000_000:.2f} GB'
        if value >= 1_000_000:
            return f'{value/1_000_000:.1f} MB'
        return f'{value/1000:.0f} KB'

    def refresh_library(self):
        readiness_changed = False
        for item in CATALOG:
            key = item['key']
            ready = find_local_model(key) is not None
            if self.model_readiness.get(key) != ready:
                self.model_readiness[key] = ready
                readiness_changed = True
            widgets = self.download_widgets.get(key)
            if not widgets:
                continue
            snapshot = self.downloads.snapshot(key)
            state, done, total, percent = self.model_status(item, snapshot, ready)
            active = state in DOWNLOAD_IN_PROGRESS
            widgets['bar'].setVisible(active or state == 'paused')
            widgets['bar'].setRange(0, 0 if state == 'resolving' else 1000)
            if state != 'resolving':
                widgets['bar'].setValue(1000 if ready else int(percent*10))
            status = MODEL_STATES[state]
            if active or state == 'paused':
                status += f'  ·  {percent:.1f}%  ·  {self.format_bytes(done)} / {self.format_bytes(total)}'
                speed = snapshot.get('speed_bps', 0) or 0
                if state == 'downloading' and speed:
                    status += f'  ·  {self.format_bytes(speed)}/s'
                    eta = snapshot.get('eta_seconds')
                    if eta is not None:
                        seconds = max(0, int(eta))
                        status += f'  ·  حدود {seconds//60:02d}:{seconds%60:02d} باقی‌مانده'
            if state == 'error':
                status += '\n' + str(snapshot.get('error') or 'اتصال و فضای دیسک را بررسی کنید؛ امکان تلاش دوباره وجود دارد.')
            if ready:
                status += '  ·  نیازی به دانلود دوباره نیست'
            status_label = widgets['status']
            if status_label.source_text != status:
                status_label.setText(status)
            tone = 'ready' if ready else 'info' if active else 'error' if state == 'error' else 'warning'
            if status_label.property('tone') != tone:
                status_label.setProperty('tone', tone)
                status_label.style().unpolish(status_label)
                status_label.style().polish(status_label)
            widgets['start'].setVisible(not ready and not active and state != 'cancelled-pending')
            widgets['start'].setText('ادامه دانلود' if state in {'paused', 'error'} else 'دانلود مدل')
            widgets['start'].setEnabled(not active and state != 'cancelled-pending')
            widgets['pause'].setVisible(active)
            widgets['pause'].setEnabled(state in {'resolving', 'downloading', 'verifying'})
            widgets['cancel'].setVisible(not ready and (active or state == 'paused'))
            widgets['cancel'].setEnabled(active or state == 'paused')
            widgets['use'].setVisible(ready)
            widgets['use'].setEnabled(ready and not self.busy and not self.recording)
        selection_changed = self.refresh_model_picker()
        if self.model.count() and (readiness_changed or selection_changed):
            self.selection_changed()

    def download_action(self, key, action):
        try:
            current = self.downloads.snapshot(key).get('status', 'idle')
            if action == 'start' and current in {'paused', 'error'}:
                self.downloads.resume(key)
            else:
                getattr(self.downloads, action)(key)
        except Exception as exc:
            self.error(str(exc))
        self.refresh_library()

    def use_model(self, key):
        if self.busy or self.recording or find_local_model(key) is None:
            return
        language = self.library_language.currentData()
        index = self.language.findData(language)
        self.language.setCurrentIndex(index)
        self.model_readiness[key] = True
        self.refresh_model_picker(preferred=key)
        index = self.model.findData(key)
        if index < 0 or self.model.currentData() != key:
            return
        self.selection_changed()
        self.show_page(0)
        self.status.setText('مدل آماده است؛ فایل صوتی را انتخاب کنید یا ضبط را شروع کنید.')

    def import_local_models(self):
        directory = QFileDialog.getExistingDirectory(self, tr('انتخاب پوشه مدل یا پوشه مدل‌های نسخه قبلی'))
        if not directory:
            return
        try:
            count = register_local_root(Path(directory))
            self.library_footer.setText(f'{count} مدل محلی شناسایی شد؛ فایل‌ها جابه‌جا یا دوباره دانلود نمی‌شوند.')
            self.library_footer.show()
        except Exception as exc:
            self.error(str(exc))
        self.refresh_library()

    def refresh_devices(self):
        if self.busy or self.recording:
            return
        self.devices.clear()
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            hosts = sd.query_hostapis()
            default = sd.default.device[0]
            for index, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    host = hosts[device['hostapi']]['name']
                    self.devices.addItem(f'{device["name"]} · {host}', index)
                    if index == default:
                        self.devices.setCurrentIndex(self.devices.count()-1)
            if not self.devices.count():
                self.devices.addItem('میکروفون پیدا نشد', None)
            self.record_button.setEnabled(self.devices.currentData() is not None)
        except Exception as exc:
            self.devices.addItem('میکروفون در دسترس نیست', None)
            self.record_button.setEnabled(False)
            self.devices.setToolTip(str(exc))
        self.controls()

    def controls(self):
        idle = not self.busy and not self.recording
        model_key = self.model.currentData()
        ready = self.model_readiness.get(model_key, False)
        model = get_model(model_key) if model_key else {}
        for item in [self.language, self.model, self.mode, self.devices, self.refresh_button,
                     self.compute_device, self.chunk_seconds]:
            item.setEnabled(idle)
        self.compute_device.setEnabled(idle and not model.get('cpu_only'))
        self.mode.setToolTip(tr('این مدل روش تشخیص ثابتی دارد. این گزینه فقط روی بخش‌بندی صوت اثر می‌گذارد.')
                             if model.get('fixed_decoder') else '')
        self.choose_button.setEnabled(idle and ready)
        self.record_button.setEnabled(not self.busy and (ready or self.recording) and self.devices.currentData() is not None)
        self.retry_button.setEnabled(idle and ready and self.last_audio is not None)
        self.cancel_button.setEnabled(self.busy and not self.cancelled)
        self.cancel_button.setVisible(self.busy)
        self.progress.setVisible(self.busy)
        self.wave.setVisible(self.recording)
        self.tally.set_state('live' if self.recording else 'busy' if self.busy else 'idle')
        self.tally.setToolTip(self.status.text())
        self.tally.setAccessibleName(self.status.text())
        self.ai_button.setEnabled(bool(self.raw_text))
        if hasattr(self, 'ai_page') and hasattr(self.ai_page, 'set_speech_settings'):
            model_text = self.model.currentText() or tr('هیچ مدل نصب‌شده‌ای نیست')
            summary = ' · '.join(filter(None, [self.language.currentText(), model_text, self.devices.currentText()]))
            self.ai_page.set_speech_settings(summary, ready=ready and idle,
                                            microphone_available=self.devices.currentData() is not None)

    def record_chat_voice(self):
        if self.recording and self.recording_target != 'ai':
            return
        self.toggle_recording(target='ai')

    def choose_chat_audio(self):
        if self.busy or self.recording:
            return
        if not self.model_readiness.get(self.model.currentData(), False):
            self.open_selected_library()
            return
        path, _ = QFileDialog.getOpenFileName(self, tr('انتخاب ویس'), '', 'Audio (*.wav *.mp3 *.m4a *.ogg)')
        if path:
            self.start_transcription(Path(path), target='ai')

    def active_output(self):
        return self.ai_output if self.transcription_target == 'ai' else self.output

    def choose_file(self):
        if self.busy or self.recording:
            return
        if self.pages.currentIndex() == 3:
            self.choose_chat_audio()
            return
        if not self.model_readiness.get(self.model.currentData(), False):
            self.open_selected_library()
            return
        path, _ = QFileDialog.getOpenFileName(self, tr('انتخاب ویس'), '', 'Audio (*.wav *.mp3 *.m4a *.ogg)')
        if path:
            self.start_transcription(Path(path))

    def retry(self):
        if self.last_audio:
            self.start_transcription(self.last_audio)

    def start_transcription(self, audio, target='studio'):
        if self.busy or self.recording:
            return
        if not self.model.currentData() or find_local_model(self.model.currentData()) is None:
            self.status.setText('ابتدا مدل این زبان را دریافت کنید یا پوشه مدل محلی را معرفی کنید.')
            if target == 'ai':
                self.ai_page.voice_failed(tr('ابتدا مدل این زبان را دریافت کنید یا پوشه مدل محلی را معرفی کنید.'))
            self.open_selected_library()
            return
        audio = Path(audio)
        if not audio.is_file() or audio.suffix.lower() not in FORMATS:
            if target == 'ai':
                self.ai_page.voice_failed(tr('یک فایل WAV، MP3، M4A یا OGG معتبر انتخاب کنید.'))
            else:
                self.error('یک فایل WAV، MP3، M4A یا OGG معتبر انتخاب کنید.')
            return
        self.transcription_target = target
        self.run_model = self.model.currentData()
        speech_language = self.language.currentData()
        output = self.data/'results'/f'{audio.stem}-{self.run_model}-{time.strftime("%Y%m%d-%H%M%S")}-{uuid.uuid4().hex[:6]}.txt'
        if target == 'ai':
            self.ai_output = output
            self.ai_page.set_voice_state('transcribing')
        else:
            self.last_audio = audio.resolve()
            self.run_language = speech_language
            self.source_name.setProperty('literalText', True)
            self.source_name.setText(audio.name)
            self.source_name.show()
            self.source_name.setToolTip(str(audio))
            self.result_model.setText(self.model.currentText())
            self.output = output
            self.raw_text = ''
            self.ai_button.setEnabled(False)
            self.text.clear()
            self.copy_button.setEnabled(False)
            self.save_button.setEnabled(False)
            self.show_page(0)
        self.started = time.monotonic()
        self.cancelled = False
        self.progress.setRange(0, 0)
        self.busy = True
        if getattr(sys, 'frozen', False):
            command = [sys.executable]
        else:
            command = [sys.executable, str(Path(__file__).resolve().parent/'entrypoint.py')]
        command += ['--worker', str(audio.resolve()), '--output', str(output), '--model', self.run_model,
                    '--beams', str(self.mode.currentData()), '--language', speech_language,
                    '--device', self.compute_device.currentData(),
                    '--chunk-seconds', str(self.chunk_seconds.currentData())]
        try:
            self.process = subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except OSError as exc:
            self.busy = False
            self.process = None
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            if target == 'ai':
                self.ai_page.voice_failed(str(exc))
                self.transcription_target = 'studio'
            else:
                self.error(str(exc))
        self.controls()

    def toggle_recording(self, target='studio'):
        if self.recording:
            self.record_button.setText('در حال پایان ضبط…')
            self.record_button.setEnabled(False)
            self.recorder.stop_event.set()
            if self.recording_target == 'ai':
                self.ai_page.set_voice_state('stopping')
            return
        if self.busy or self.devices.currentData() is None:
            return
        if not self.model.currentData() or find_local_model(self.model.currentData()) is None:
            if target == 'ai':
                self.ai_page.voice_failed(tr('ابتدا مدل این زبان را دریافت کنید یا پوشه مدل محلی را معرفی کنید.'))
            self.open_selected_library()
            return
        path = self.data/'recordings'/f'voice-{time.strftime("%Y%m%d-%H%M%S")}-{uuid.uuid4().hex[:6]}.wav'
        self.recording_target = target
        self.recorder = Recorder(self.devices.currentData(), path)
        self.recorder.level.connect(self.wave.push)
        self.recorder.ready.connect(self.record_ready)
        self.recorder.recorded.connect(self.record_finished)
        self.recorder.failed.connect(self.record_error)
        self.recording = True
        if target == 'ai':
            self.ai_page.set_voice_state('preparing')
        self.mic_ready = False
        self.started = time.monotonic()
        self.wave.active = True
        self.record_button.setText('آماده‌سازی میکروفون…')
        self.record_button.setObjectName('danger')
        self.color_action_icon(self.record_button)
        self.record_button.style().unpolish(self.record_button)
        self.record_button.style().polish(self.record_button)
        self.controls()
        self.record_button.setEnabled(False)
        try:
            self.recorder.start()
        except Exception as exc:
            self.record_error(str(exc))

    def record_ready(self):
        if self.closing or not self.recording:
            return
        self.mic_ready = True
        self.started = time.monotonic()
        self.record_button.setText('پایان ضبط و تبدیل')
        self.record_button.setEnabled(True)
        if self.recording_target == 'ai':
            self.ai_page.set_voice_state('recording')

    def reset_recording(self):
        self.recording = False
        self.mic_ready = False
        self.wave.active = False
        self.wave.update()
        self.record_button.setText('شروع ضبط')
        self.record_button.setObjectName('record')
        self.color_action_icon(self.record_button)
        self.record_button.style().unpolish(self.record_button)
        self.record_button.style().polish(self.record_button)
        self.controls()

    def record_finished(self, path, duration):
        if self.closing or not self.recording:
            return
        target = self.recording_target
        self.reset_recording()
        self.start_transcription(Path(path), target=target)

    def record_error(self, detail):
        if self.closing or not self.recording:
            return
        self.reset_recording()
        if self.recording_target == 'ai':
            self.ai_page.voice_failed(tr(detail))
            return
        self.status.setText('ضبط انجام نشد؛ میکروفون و اجازه دسترسی در تنظیمات ویندوز را بررسی کنید.')
        self.error(detail)

    def tick(self):
        if self.closing:
            return
        now = time.monotonic()
        if now - self.last_library_poll > .8:
            self.last_library_poll = now
            self.refresh_library()
        if self.recording:
            if self.mic_ready:
                duration = int(time.monotonic()-self.started)
                self.status.setText(f'در حال ضبط  ·  {duration//60:02d}:{duration%60:02d}  ·  برای تبدیل، پایان ضبط را بزنید.')
                if self.recording_target == 'ai':
                    self.ai_page.set_voice_state('recording', f'{duration//60:02d}:{duration%60:02d}')
            else:
                self.status.setText('در حال آماده‌سازی میکروفون؛ پس از فعال‌شدن دکمه پایان ضبط، صحبت کنید.')
        elif self.busy and self.process:
            duration = int(time.monotonic()-self.started)
            phases = {'preparing': 'آماده‌سازی', 'decoding': 'خواندن صوت', 'loading': 'بارگذاری مدل',
                      'transcribing': 'تشخیص گفتار', 'done': 'ذخیره نتیجه', 'error': 'خطا',
                      'fallback': 'بازگشت به CPU'}
            phase = 'آماده‌سازی'
            try:
                progress = json.loads(read_text_shared(self.active_output().with_suffix('.progress.json')))
                phase = phases.get(progress['phase'], phase)
                if progress['phase'] == 'transcribing':
                    if isinstance(progress.get('fraction'), (int, float)):
                        self.progress.setRange(0, 1000)
                        self.progress.setValue(int(max(0, min(1, progress['fraction']))*1000))
                    elif progress.get('total'):
                        self.progress.setRange(0, progress['total'])
                        self.progress.setValue(progress.get('completed', 0))
                    if progress.get('total_is_estimate'):
                        phase += f'  ·  {progress.get("completed", 0)} / ~{progress.get("total", 0)}'
                    elif progress.get('total'):
                        phase += f' · بخش {progress.get("completed", 0)+1} از {progress["total"]}'
                    if progress.get('actual_device'):
                        phase += '  ·  ' + str(progress['actual_device']).upper()
                reasons = progress.get('fallback_reasons') or []
                if reasons:
                    self.status.setToolTip('\n'.join(str(x) for x in reasons))
                elif progress.get('reason'):
                    self.status.setToolTip(str(progress['reason']))
            except (OSError, ValueError, KeyError):
                pass
            self.status.setText(f'{phase}  ·  {duration} ثانیه گذشته است  ·  {self.run_model}')
            if self.transcription_target == 'ai':
                detail = f'{tr(phase)} · {duration}s'
                if self.progress.maximum() > 0:
                    detail += f' · {round(100*self.progress.value()/self.progress.maximum())}%'
                self.ai_page.set_voice_state('cancelling' if self.cancelled else 'transcribing', detail)
            if self.process.poll() is not None:
                self.complete()

    def complete(self):
        output = self.active_output()
        chat_voice = self.transcription_target == 'ai'
        returncode = self.process.returncode
        self.process = None
        self.busy = False
        self.progress.setRange(0, 100)
        if self.cancelled:
            self.progress.setValue(0)
            self.status.setText('تبدیل متوقف شد؛ می‌توانید فایل یا مدل دیگری انتخاب کنید.')
            if chat_voice:
                self.ai_page.set_voice_state('idle', tr('تبدیل متوقف شد؛ می‌توانید فایل یا مدل دیگری انتخاب کنید.'))
        else:
            try:
                metrics = json.loads(read_text_shared(output.with_suffix('.metrics.json')))
                if returncode or metrics.get('status') != 'success':
                    raise RuntimeError('\n'.join(metrics.get('errors', [])) or 'تبدیل کامل نشد.')
                if chat_voice:
                    self.ai_page.append_voice_transcript(read_text_shared(output), output.name)
                else:
                    self.display_result(output, metrics)
                self.progress.setValue(100)
                self.status.setText('تبدیل تمام شد؛ متن و گزارش خودکار ذخیره شدند.')
                if metrics.get('fallback_reasons'):
                    self.status.setText('تبدیل تمام شد؛ شتاب‌دهنده در دسترس نبود و CPU استفاده شد.')
                    self.status.setToolTip('\n'.join(str(x) for x in metrics['fallback_reasons']))
                QTimer.singleShot(1200, self.maybe_prompt_star)
            except Exception as exc:
                self.progress.setValue(0)
                log = output.with_suffix('.log')
                self.status.setText('تبدیل ناموفق بود؛ فایل گزارش برای عیب‌یابی نگه داشته شد.')
                if chat_voice:
                    self.ai_page.voice_failed(str(exc))
                else:
                    self.error(str(exc) + f'\n\nگزارش: {log}')
        self.transcription_target = 'studio'
        self.controls()
        self.refresh_history()

    def display_result(self, path, metrics):
        self.raw_text = read_text_shared(path)
        self.text.setPlainText(self.raw_text)
        self.update_transcript_direction(metrics.get('language'))
        self.copy_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.ai_button.setEnabled(True)
        self.output = path
        self.result_model.setText(metrics.get('subfolder') or metrics.get('model', ''))
        self.metrics_label.setText(f'صوت: {metrics.get("audio_seconds",0):.1f} ثانیه  ·  '
                                   f'تشخیص: {metrics.get("inference_seconds",0):.1f} ثانیه  ·  '
                                   f'کل: {metrics.get("total_seconds",0):.1f} ثانیه  ·  '
                                   f'RAM: {metrics.get("peak_rss_mib_sampled",0):.0f} MiB  ·  '
                                   f'{str(metrics.get("device", "cpu")).upper()}')
        notes = [*metrics.get('fallback_reasons', []), *metrics.get('warnings', [])]
        self.metrics_label.setToolTip('\n'.join(str(x) for x in notes))

    def maybe_prompt_star(self):
        """One optional invitation; never signs in or stars on the user's behalf."""
        if (self.star_prompt_seen or not self.allow_star_prompt or self.closing or
                not self.isVisible() or self.busy or self.recording or self.pages.currentIndex() != 0 or
                QApplication.platformName() == 'offscreen'):
            return
        self.star_prompt_seen = True
        # Persist before showing so closing the dialog or the app cannot repeat it.
        if not self.save_settings():
            self.star_prompt_seen = False
            return
        box = QMessageBox(self)
        box.setWindowTitle(tr('از Avunote حمایت کنید'))
        box.setText(tr('اگر Avunote برایتان مفید بود، می‌توانید به مخزن آن در گیت‌هاب ستاره بدهید. این پیشنهاد فقط یک‌بار نمایش داده می‌شود.'))
        open_button = box.addButton(tr('بازکردن مخزن گیت‌هاب'), QMessageBox.ButtonRole.ActionRole)
        box.addButton(tr('قبلاً ستاره داده‌ام'), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(tr('نه، ممنون'), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is open_button:
            QDesktopServices.openUrl(QUrl('https://github.com/Fardinmilani/Voxriva'))

    def copy_text(self):
        QApplication.clipboard().setText(self.raw_text)

    def save_text(self):
        name, _ = QFileDialog.getSaveFileName(self, tr('ذخیره متن خام'), str(self.output.name), 'Text (*.txt)')
        if name:
            try:
                Path(name).write_text(self.raw_text, encoding='utf-8')
            except OSError as exc:
                self.error(str(exc))

    def refresh_history(self):
        self.history_paths = []
        records = []
        for path in sorted((self.data/'results').glob('*.metrics.json'), key=lambda p:p.stat().st_mtime, reverse=True)[:200]:
            try:
                metrics = json.loads(read_text_shared(path))
                text_path = path.with_name(path.name.replace('.metrics.json', '.txt'))
                if metrics.get('status') == 'success' and text_path.exists():
                    records.append((text_path, metrics))
            except (OSError, ValueError):
                pass
        self.table.setRowCount(len(records))
        self.history_view.setCurrentIndex(1 if records else 0)
        self.open_history_button.setVisible(bool(records))
        self.open_history_button.setEnabled(False)
        for row, (path, metrics) in enumerate(records):
            self.history_paths.append(path)
            language = next((language_title(x) for x in LANGUAGES if x['code'] == metrics.get('language')), metrics.get('language', ''))
            values = [path.stem.split('-whisper')[0], metrics.get('subfolder') or metrics.get('model', ''), f'{metrics.get("audio_seconds",0):.1f}s',
                      f'{metrics.get("total_seconds",0):.1f}s', time.strftime('%Y-%m-%d %H:%M', time.localtime(path.stat().st_mtime))]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
                self.table.item(row, col).setToolTip(language)
            self.table.setRowHeight(row, 54)

    def load_history(self, row, column):
        if self.busy or self.recording:
            return
        path = self.history_paths[row]
        metrics = json.loads(read_text_shared(path.with_suffix('.metrics.json')))
        self.display_result(path, metrics)
        self.show_page(0)
        self.status.setText('نتیجه ذخیره‌شده از تاریخچه نمایش داده شد.')

    def cancel(self):
        if self.busy and self.process:
            if self.cancelled:
                return
            self.cancelled = True
            if self.transcription_target == 'ai':
                self.ai_page.set_voice_state('cancelling')
            # A long decode may have an FFmpeg child. Stop only this owned worker
            # tree so cancelling does not leave an orphan audio conversion behind.
            try:
                import psutil
                pid = self.process.pid
                if isinstance(pid, int) and self.process.poll() is None:
                    for child in psutil.Process(pid).children(recursive=True):
                        try:
                            child.terminate()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
            except Exception:
                pass
            self.process.terminate()
            self.controls()

    def dragEnterEvent(self, event):
        if not self.busy and not self.recording and event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].isLocalFile() and Path(urls[0].toLocalFile()).suffix.lower() in FORMATS:
                event.acceptProposedAction()

    def dropEvent(self, event):
        target = 'ai' if self.pages.currentIndex() == 3 else 'studio'
        self.start_transcription(Path(event.mimeData().urls()[0].toLocalFile()), target=target)
        event.acceptProposedAction()

    def error(self, text):
        QMessageBox.warning(self, tr('نیاز به بررسی'), tr(text))

    def about(self):
        box = QMessageBox(self)
        box.setWindowTitle(tr('درباره Avunote'))
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText('<b>Avunote</b><p>' + tr('توسعه‌دهنده برنامه') + ': <b>Fardin Milani</b><br>'
                    '<a href="https://github.com/Fardinmilani">GitHub / Fardinmilani</a> · '
                    '<a href="https://fardinmilani.ir">fardinmilani.ir</a><br>'
                    '<a href="https://github.com/Fardinmilani/Voxriva">Avunote / GitHub</a></p><p>' +
                    tr('برنامه متن‌باز است؛ مجوز کد اختصاصی برنامه MIT است.') + '</p><p>' +
                    tr('مدل‌های آذربایجانی جنوبی: مؤسسه Kartal Ol') + '<br>'
                    '<a href="https://github.com/Kartalol">github.com/Kartalol</a><br>' +
                    tr('طبق اعلام توسعه‌دهنده، مجوز مدل‌های آذربایجانی MIT است.') + ' ' +
                    tr('اعلان‌ها و مجوز هر مدل در کتابخانه و اسناد همراه حفظ شده‌اند.') + '</p><p>' +
                    tr('این برنامه از کتابخانه‌های Qt / PySide6 تحت LGPLv3 استفاده می‌کند.') + ' ' +
                    tr('اطلاعیه‌ها، متن مجوزها و منابع متناظر کتابخانه‌ها در پوشه Licenses قرار دارند.') + ' ' +
                    tr('حقوق تغییر و جایگزینی این کتابخانه‌ها محفوظ است.') + '</p><p>' +
                    tr('تشخیص گفتار محلی است. گفت‌وگوی ابری فقط با ارسال صریح کاربر، متن انتخابی را به سرویس تنظیم‌شده می‌فرستد.') + '</p>')
        open_button = box.addButton(tr('بازکردن مجوزها'), QMessageBox.ButtonRole.ActionRole)
        box.addButton(tr('بستن'), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is open_button:
            base = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(base/'Licenses')))

    def closeEvent(self, event):
        self.closing = True
        if self.recording:
            self.recorder.stop_event.set()
            if not self.recorder.wait(3000):
                self.closing = False
                event.ignore()
                return
            self.reset_recording()
            if self.recording_target == 'ai':
                self.ai_page.set_voice_state('idle', tr('تبدیل متوقف شد؛ می‌توانید فایل یا مدل دیگری انتخاب کنید.'))
        self.cancel()
        if self.process:
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.save_settings()
        if self.downloads.close() is False:
            self.closing = False
            self.status.setText('در حال توقف ایمن دانلود؛ چند لحظه دیگر دوباره برنامه را ببندید.')
            event.ignore()
            return
        if hasattr(self.ai_page, 'shutdown') and self.ai_page.shutdown() is False:
            self.closing = False
            event.ignore()
            return
        event.accept()


def launch(audio=None, preview=None, page=None):
    if os.name == 'nt':
        # Use the same explicit identity on every launch so taskbar icons group
        # under the new brand rather than the generic Python interpreter.
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('FardinMilani.Avunote')
    app = QApplication(sys.argv)
    app.setApplicationName('Avunote')
    app.setOrganizationName('Avunote')
    load_fonts()
    app.setFont(QFont('Segoe UI', 10))
    window = Studio()
    screen = app.primaryScreen().availableGeometry()
    window.resize(min(1280, screen.width()-40), min(880, screen.height()-60))
    window.show()
    if page is not None:
        window.show_page({'studio': 0, 'history': 1, 'library': 2, 'ai': 3, 'settings': 4}.get(str(page), 0))
    if audio:
        QTimer.singleShot(300, lambda: window.start_transcription(Path(audio)))
    if preview:
        window.allow_star_prompt = False
        def capture():
            window.grab().save(str(preview))
            window.close()
            app.quit()
        QTimer.singleShot(700, capture)
    elif getattr(sys, 'frozen', False) and window.allow_star_prompt:
        QTimer.singleShot(2000, lambda: window.update_controller().check_background())
    sys.exit(app.exec())
