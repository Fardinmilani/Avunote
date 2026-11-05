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
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QSize, QUrl
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QIcon, QPixmap, QDesktopServices, QTextOption, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
                               QVBoxLayout, QHBoxLayout, QGridLayout, QComboBox, QTextEdit,
                               QFileDialog, QMessageBox, QProgressBar, QStackedWidget,
                               QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
                               QSizePolicy, QGraphicsColorizeEffect)
from model_catalog import (CATALOG, LANGUAGES, get_model, models_for_language,
                           find_local_model, data_root, register_local_root)
from model_downloads import DownloadManager
from ui_i18n import (tr, set_language, current_language, UI_LANGUAGES,
                     RTL_LANGUAGES, register_speech_languages, language_title)
from studio_theme import THEMES, resolve_theme, stylesheet as theme_stylesheet

register_speech_languages(LANGUAGES)

FORMATS = {'.wav', '.mp3', '.m4a', '.ogg'}
GREEN = '#6754e8'


def icon(kind, color='#66748c'):
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color), 2.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    if kind == 'mic':
        painter.drawRoundedRect(12, 4, 8, 16, 4, 4)
        painter.drawArc(7, 8, 18, 18, 180*16, 180*16)
        painter.drawLine(16, 26, 16, 30)
        painter.drawLine(10, 30, 22, 30)
    elif kind == 'file':
        painter.drawRoundedRect(7, 4, 18, 24, 3, 3)
        painter.drawLine(11, 12, 21, 12)
        painter.drawLine(11, 17, 21, 17)
        painter.drawLine(11, 22, 17, 22)
    elif kind == 'stop':
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(8, 8, 16, 16, 3, 3)
    elif kind == 'library':
        for x in [5, 18]:
            for y in [5, 18]:
                painter.drawRoundedRect(x, y, 9, 9, 2, 2)
    elif kind == 'download':
        painter.drawLine(16, 4, 16, 22)
        painter.drawLine(9, 15, 16, 22)
        painter.drawLine(23, 15, 16, 22)
        painter.drawLine(6, 27, 26, 27)
    elif kind == 'refresh':
        painter.drawArc(6, 6, 20, 20, 40*16, 285*16)
        painter.drawLine(23, 5, 25, 12)
        painter.drawLine(25, 12, 18, 10)
    else:
        for x, height in [(5, 9), (10, 18), (16, 27), (22, 18), (27, 9)]:
            painter.drawLine(x, (32-height)//2, x, (32+height)//2)
    painter.end()
    return QIcon(pixmap)


class Waveform(QWidget):
    def __init__(self):
        super().__init__()
        self.values = [.04] * 54
        self.active = False
        self.dark = False
        self.setMinimumHeight(68)
        self.setAccessibleName('نمودار سطح صدای میکروفون')

    def push(self, level):
        self.values = self.values[1:] + [max(.035, min(1., level*4))]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        spacing = self.width()/len(self.values)
        painter.setPen(QPen(QColor(GREEN if self.active else ('#44516a' if self.dark else '#d9dfed')), max(2, spacing*.38),
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for index, level in enumerate(self.values):
            height = max(4, level * (self.height()-14))
            x = int(index*spacing + spacing/2)
            painter.drawLine(x, int((self.height()-height)/2), x, int((self.height()+height)/2))


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


class ComboBox(QComboBox):
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

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#66748c'), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        x = 14 if self.layoutDirection() == Qt.LayoutDirection.RightToLeft else self.width()-15
        y = self.height()//2
        painter.drawLine(x-4, y-2, x, y+2)
        painter.drawLine(x, y+2, x+4, y-2)


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
        widget.setIcon(icon(symbol, '#ffffff' if name == 'primary' else '#66748c'))
        widget.setIconSize(QSize(22, 22))
    return widget


STYLE = '''
QMainWindow, QWidget#shell, QWidget#page {background:#f7f8fc; color:#102240;}
QWidget {font-family:"Segoe UI"; font-size:14px; color:#102240;}
QFrame#rail {background:#ffffff; border:0; border-left:1px solid #e5e8f0;}
QFrame#card, QFrame#resultCard, QFrame#settings, QFrame#modelCard {background:#ffffff; border:1px solid #e5e8f0; border-radius:16px;}
QFrame#notice {background:#f0edff; border:1px solid #e1dcff; border-radius:11px;}
QFrame#disclosure {background:#f8f8fc; border:1px solid #e5e8f0; border-radius:8px;}
QLabel#eyebrow {font-size:12px; color:#6754e8; font-weight:600;}
QLabel#libraryTitle {font-size:18px; font-weight:700; color:#102240;}
QLabel#brand {font-size:24px; font-weight:700; color:#102240;}
QLabel#heading {font-size:27px; font-weight:700; color:#102240;}
QLabel#cardTitle {font-size:17px; font-weight:600; color:#102240;}
QLabel#muted {color:#5c6b82; font-size:13px;}
QLabel#badge {color:#5140c3; background:#f0edff; border-radius:9px; padding:7px 10px; font-size:12px;}
QLabel#metric {font-size:16px; color:#102240; font-weight:600;}
QPushButton {background:#ffffff; border:1px solid #dce1ed; border-radius:9px; padding:8px 12px; color:#243751;}
QPushButton:hover {background:#f4f2ff; border-color:#b5aaef;}
QPushButton:focus {border:2px solid #6754e8;}
QPushButton:disabled {background:#f6f7fa; color:#8994a8; border-color:#e5e8f0;}
QPushButton#primary {background:#6754e8; color:#ffffff; border-color:#6754e8; font-weight:600;}
QPushButton#primary:hover {background:#5541d4;}
QPushButton#primary:disabled {background:#eeebfa; color:#8e85b5; border-color:#e1dcf3;}
QPushButton#danger {background:#fff1f2; border-color:#e5adb9; color:#a42d4d;}
QPushButton#nav {text-align:right; border:0; background:transparent; color:#66748c; padding:12px 14px;}
QPushButton#nav:hover {background:#f7f6fc;}
QPushButton#nav:checked {background:#eeebff; color:#5944d0; font-weight:600;}
QPushButton#accent {background:#f0edff; border-color:#e1dcff; color:#5741cf;}
QPushButton#accent:hover {background:#e4deff;}
QPushButton#link {background:transparent; border:0; color:#6754e8; font-size:12px; padding:3px 0; text-align:left;}
QPushButton#link:hover {color:#4730c4; text-decoration:underline;}
QComboBox {background:#ffffff; border:1px solid #dce1ed; border-radius:9px; padding:9px 10px; min-height:22px;}
QComboBox:focus {border:2px solid #6754e8;}
QComboBox::drop-down {border:0; width:24px;}
QComboBox QAbstractItemView {background:#ffffff; color:#102240; selection-background-color:#eeebff; selection-color:#5140c3; border:1px solid #dce1ed;}
QTextEdit {background:#ffffff; border:0; color:#102240; font-size:19px; padding:12px; selection-background-color:#e1dcff; selection-color:#102240;}
QProgressBar {background:#eeedf6; border:0; border-radius:3px; min-height:5px; max-height:5px;}
QProgressBar::chunk {background:#6754e8; border-radius:3px;}
QProgressBar#downloadProgress {min-height:6px; max-height:6px; background:#ebeaf5;}
QScrollArea {background:transparent; border:0;}
QScrollArea > QWidget > QWidget {background:#f7f8fc;}
QTableWidget {background:#ffffff; border:1px solid #e5e8f0; border-radius:12px; gridline-color:#edf0f5; alternate-background-color:#fafbfe;}
QHeaderView::section {background:#f0f2f8; color:#5c6b82; padding:12px; border:0;}
QTableWidget::item {padding:10px;}
QScrollBar:vertical {background:#f7f8fc; width:8px; margin:0;}
QScrollBar::handle:vertical {background:#ccd1e2; border-radius:4px; min-height:30px;}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {height:0;}
QToolTip {background:#ffffff; color:#102240; border:1px solid #dce1ed; padding:8px;}
'''


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
            self.saved_settings = json.loads((self.data/'settings.json').read_text(encoding='utf-8'))
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
        self.allow_star_prompt = os.environ.get('VOXRIVA_SUPPRESS_PROMPTS') != '1'
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
        self.closing = False
        self.setWindowTitle(tr('Voxriva — استودیوی گفتار آفلاین'))
        self.setWindowIcon(QIcon(self.brand_pixmap(True)))
        self.resize(1280, 880)
        self.setMinimumSize(1000, 760)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.ui_language in RTL_LANGUAGES else Qt.LayoutDirection.LeftToRight)
        self.setAcceptDrops(True)
        self.build()
        self.apply_theme()
        QApplication.styleHints().colorSchemeChanged.connect(self.system_theme_changed)
        QShortcut(QKeySequence('Ctrl+O'), self, activated=self.choose_file)
        QShortcut(QKeySequence('Escape'), self, activated=self.cancel)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(150)
        self.refresh_devices()
        self.refresh_history()
        index = self.language.findData(self.saved_settings.get('language', 'azb'))
        self.language.setCurrentIndex(max(0, index))
        self.language_changed()
        index = self.model.findData(self.saved_settings.get('model', 'whisper-base-full'))
        if index >= 0:
            self.model.setCurrentIndex(index)
        self.selection_changed()
        self.refresh_library()
        self.retranslate_ui()

    def brand_pixmap(self, mark_only=False):
        base = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
        transparent = QPixmap(str(base/'assets/voxriva-logo-transparent.png'))
        if not transparent.isNull():
            # Supplied theme assets are tightly framed and already transparent.
            return transparent
        pixmap = QPixmap(str(base/'assets/voxriva-logo.png'))
        if pixmap.isNull():
            return QPixmap()
        w, h = pixmap.width(), pixmap.height()
        region = (.34, .24, .33, .37) if mark_only else (.19, .235, .63, .535)
        return pixmap.copy(int(w*region[0]), int(h*region[1]), int(w*region[2]), int(h*region[3]))

    def build(self):
        shell = QWidget()
        shell.setObjectName('shell')
        self.setCentralWidget(shell)
        outer = QHBoxLayout(shell)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        rail = QFrame()
        rail.setObjectName('rail')
        rail.setFixedWidth(216)
        navigation = QVBoxLayout(rail)
        navigation.setContentsMargins(14, 14, 14, 12)
        navigation.setSpacing(5)
        brand = QLabel()
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_image = self.brand_pixmap().scaled(256, 192, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        brand_image.setDevicePixelRatio(2)
        brand.setPixmap(brand_image)
        brand.setAccessibleName('Voxriva')
        brand.setFixedHeight(96)
        self.brand_label = brand
        navigation.addWidget(brand)
        tag = label('صدای شما. کلمات شما.', 'muted')
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        navigation.addWidget(tag)
        navigation.addSpacing(12)
        navigation.addWidget(label('فضای کار', 'eyebrow'))
        self.studio_nav = button('استودیوی گفتار', lambda: self.show_page(0), 'nav', 'wave')
        self.library_nav = button('زبان‌ها و مدل‌ها', lambda: self.show_page(2), 'nav', 'library')
        self.history_nav = button('تاریخچه', lambda: self.show_page(1), 'nav', 'file')
        self.ai_nav = button('گفت‌وگوی AI', lambda: self.show_page(3), 'nav', 'wave')
        for item in [self.studio_nav, self.library_nav, self.history_nav, self.ai_nav]:
            item.setCheckable(True)
            navigation.addWidget(item)
        self.studio_nav.setChecked(True)
        navigation.addStretch()
        privacy = label('تشخیص گفتار روی همین دستگاه است.', 'muted')
        privacy.setToolTip('صدای شما برای پردازش به اینترنت ارسال نمی‌شود.')
        navigation.addWidget(privacy)
        navigation.addSpacing(8)
        navigation.addWidget(label('ظاهر برنامه', 'muted'))
        self.theme_selector = ComboBox()
        for title, key in [('هماهنگ با سیستم', 'system'), ('روشن', 'light'), ('تاریک', 'dark')]:
            self.theme_selector.addItem(title, key)
        self.theme_selector.setCurrentIndex(self.theme_selector.findData(self.theme_choice))
        self.theme_selector.currentIndexChanged.connect(self.theme_changed)
        navigation.addWidget(self.theme_selector)
        navigation.addWidget(label('زبان رابط کاربری', 'muted'))
        self.interface_language = ComboBox()
        self.interface_language.setProperty('localeSelector', True)
        self.interface_language.setAccessibleName('Interface language')
        self.interface_language.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        for code, native in UI_LANGUAGES:
            self.interface_language.addItem(native, code)
        self.interface_language.setCurrentIndex(self.interface_language.findData(self.ui_language))
        self.interface_language.currentIndexChanged.connect(self.interface_changed)
        navigation.addWidget(self.interface_language)
        navigation.addWidget(button('درباره و مجوزها', self.about, 'link'))
        version = label('Voxriva 2.1', 'muted')
        version.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        navigation.addWidget(version)
        outer.addWidget(rail)
        self.pages = QStackedWidget()
        outer.addWidget(self.pages, 1)
        workspace = QWidget()
        workspace.setObjectName('page')
        main = QVBoxLayout(workspace)
        main.setContentsMargins(24, 24, 24, 22)
        main.setSpacing(16)
        heading_row = QHBoxLayout()
        headings = QVBoxLayout()
        headings.setSpacing(4)
        headings.addWidget(label('از گفتن تا نوشتن', 'eyebrow'))
        headings.addWidget(label('بگذار صدایت بنویسد.', 'heading'))
        headings.addWidget(label('فایل صوتی یا ضبط زنده؛ متن خام، خصوصی و به زبان خودتان.', 'muted'))
        heading_row.addLayout(headings, 1)
        heading_row.addWidget(label('آفلاین و خصوصی', 'badge'))
        main.addLayout(heading_row)
        settings_panel = QFrame()
        settings_panel.setObjectName('settings')
        config = QVBoxLayout(settings_panel)
        config.setContentsMargins(16, 12, 16, 10)
        config.setSpacing(8)
        fields = QGridLayout()
        fields.setHorizontalSpacing(12)
        self.language = ComboBox()
        self.language.setProperty('speechSelector', True)
        self.language.setAccessibleName('زبان گفتار')
        for item in LANGUAGES:
            self.language.addItem(item['title'], item['code'])
        self.language.currentIndexChanged.connect(self.language_changed)
        self.model = ComboBox()
        self.model.setAccessibleName('مدل تشخیص گفتار')
        self.model.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.model.currentIndexChanged.connect(self.selection_changed)
        self.mode = ComboBox()
        self.mode.setAccessibleName('کیفیت پردازش')
        self.mode.addItem('دقت بیشتر', 5)
        self.mode.addItem('سریع‌تر', 1)
        for col, (title, widget) in enumerate([('زبان گفتار', self.language), ('مدل', self.model), ('حالت پردازش', self.mode)]):
            fields.addWidget(label(title, 'muted'), 0, col)
            fields.addWidget(widget, 1, col)
        fields.setColumnStretch(0, 3)
        fields.setColumnStretch(1, 4)
        fields.setColumnStretch(2, 2)
        config.addLayout(fields)
        readiness = QHBoxLayout()
        self.model_notice = label('وضعیت مدل در حال بررسی است.', 'muted')
        readiness.addWidget(self.model_notice, 1)
        self.library_button = button('مدیریت مدل‌ها', self.open_selected_library, 'link')
        self.library_button.setMinimumHeight(30)
        readiness.addWidget(self.library_button)
        self.advanced_button = button('گزینه‌های پردازش', self.toggle_processing_options, 'link')
        self.advanced_button.setCheckable(True)
        self.advanced_button.setMinimumHeight(30)
        readiness.addWidget(self.advanced_button)
        config.addLayout(readiness)
        self.processing_options = QWidget()
        extra = QGridLayout(self.processing_options)
        extra.setContentsMargins(0, 2, 0, 0)
        extra.setHorizontalSpacing(12)
        self.compute_device = ComboBox()
        self.compute_device.setAccessibleName('Processing device')
        self.compute_device.addItem('خودکار؛ در صورت خطا CPU', 'auto')
        self.compute_device.addItem('CPU', 'cpu')
        self.compute_device.addItem('NVIDIA CUDA', 'cuda')
        self.compute_device.addItem('NPU؛ در صورت ناسازگاری CPU', 'npu')
        index = self.compute_device.findData(self.saved_settings.get('device', 'auto'))
        self.compute_device.setCurrentIndex(max(0, index))
        self.chunk_seconds = ComboBox()
        self.chunk_seconds.setAccessibleName('Audio chunk duration')
        for seconds in [10, 15, 20, 25, 30]:
            self.chunk_seconds.addItem(f'{seconds} s', seconds)
        index = self.chunk_seconds.findData(self.saved_settings.get('chunk_seconds', 20))
        self.chunk_seconds.setCurrentIndex(index if index >= 0 else 2)
        self.compute_device.currentIndexChanged.connect(self.compute_choice_changed)
        self.chunk_seconds.currentIndexChanged.connect(lambda *_: self.save_settings())
        extra.addWidget(label('دستگاه پردازش', 'muted'), 0, 0)
        extra.addWidget(label('مدت هر بخش صوت', 'muted'), 0, 1)
        extra.addWidget(self.compute_device, 1, 0)
        extra.addWidget(self.chunk_seconds, 1, 1)
        self.compute_notice = label('سازگاری شتاب‌دهنده هنگام اجرا بررسی می‌شود؛ مدل‌ها خودکار دانلود نمی‌شوند.', 'muted')
        extra.addWidget(self.compute_notice, 2, 0, 1, 2)
        config.addWidget(self.processing_options)
        self.processing_options.hide()
        main.addWidget(settings_panel)
        body = QHBoxLayout()
        body.setSpacing(16)
        inputs = QWidget()
        inputs.setMaximumWidth(330)
        input_layout = QVBoxLayout(inputs)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(14)
        record_card, record = self.card('ضبط مستقیم', '')
        record.setContentsMargins(16, 14, 16, 14)
        record.setSpacing(8)
        microphone_row = QHBoxLayout()
        microphone_row.setSpacing(8)
        self.devices = ComboBox()
        self.devices.setAccessibleName('انتخاب میکروفون')
        self.devices.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.devices.setMinimumContentsLength(12)
        self.devices.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        microphone_row.addWidget(self.devices, 1)
        self.refresh_button = button('', self.refresh_devices, symbol='refresh')
        self.refresh_button.setFixedSize(44, 44)
        self.refresh_button.setToolTip('بازخوانی میکروفون‌ها')
        microphone_row.addWidget(self.refresh_button)
        record.addLayout(microphone_row)
        self.wave = Waveform()
        self.wave.setMinimumHeight(26)
        self.wave.setMaximumHeight(30)
        record.addWidget(self.wave, 1)
        self.record_button = button('شروع ضبط', self.toggle_recording, 'primary', 'mic')
        record.addWidget(self.record_button)
        input_layout.addWidget(record_card, 1)
        file_card, files = self.card('فایل آماده دارید؟', '')
        files.setContentsMargins(16, 14, 16, 14)
        files.setSpacing(8)
        self.source_name = label('هنوز فایلی انتخاب نشده', 'muted')
        self.source_name.setMinimumHeight(20)
        files.addWidget(self.source_name)
        self.choose_button = button('انتخاب فایل صوتی', self.choose_file, symbol='file')
        self.choose_button.setToolTip('WAV · MP3 · M4A · OGG\n' + 'فایل را انتخاب کنید یا داخل پنجره رها کنید.')
        files.addWidget(self.choose_button)
        input_layout.addWidget(file_card)
        body.addWidget(inputs, 3)
        self.result_card = QFrame()
        self.result_card.setObjectName('resultCard')
        result = QVBoxLayout(self.result_card)
        result.setContentsMargins(18, 18, 18, 16)
        result.setSpacing(12)
        result_header = QHBoxLayout()
        result_header.addWidget(label('متن شما', 'cardTitle'), 1)
        self.result_model = label('خروجی خام مدل', 'muted')
        self.result_model.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        result_header.addWidget(self.result_model)
        result.addLayout(result_header)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setAccessibleName('متن خام خروجی مدل')
        self.text.setPlaceholderText('اینجا، صدای شما به کلمات تبدیل می‌شود…\n\nبرای شروع، یک فایل انتخاب کنید یا ضبط را بزنید.')
        option = self.text.document().defaultTextOption()
        option.setTextDirection(Qt.LayoutDirection.LayoutDirectionAuto)
        self.text.document().setDefaultTextOption(option)
        result.addWidget(self.text, 1)
        self.metrics_label = label('بدون ترجمه، اصلاح املا یا بازنویسی خودکار.', 'muted')
        result.addWidget(self.metrics_label)
        actions = QHBoxLayout()
        self.copy_button = button('کپی', self.copy_text)
        self.save_button = button('ذخیره متن', self.save_text)
        self.retry_button = button('تبدیل دوباره', self.retry, 'accent')
        self.retry_button.setToolTip('همین فایل را با زبان و مدل انتخاب‌شده دوباره پردازش کنید.')
        for action in [self.copy_button, self.save_button, self.retry_button]:
            action.setEnabled(False)
            actions.addWidget(action)
        result.addLayout(actions)
        self.ai_button = button('گفت‌وگو درباره این متن', self.discuss_transcript, 'link')
        self.ai_button.setEnabled(False)
        result.addWidget(self.ai_button)
        body.addWidget(self.result_card, 5)
        main.addLayout(body, 1)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        footer = QWidget()
        footer.setObjectName('page')
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(24, 8, 24, 14)
        footer_layout.setSpacing(8)
        footer_layout.addWidget(self.progress)
        status_line = QHBoxLayout()
        self.status = label('آماده برای شنیدن؛ فایل یا میکروفون را انتخاب کنید.', 'muted')
        status_line.addWidget(self.status, 1)
        self.cancel_button = button('توقف تبدیل', self.cancel)
        self.cancel_button.setEnabled(False)
        status_line.addWidget(self.cancel_button)
        footer_layout.addLayout(status_line)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(workspace)
        studio = QWidget()
        studio.setObjectName('page')
        studio_layout = QVBoxLayout(studio)
        studio_layout.setContentsMargins(0, 0, 0, 0)
        studio_layout.setSpacing(0)
        studio_layout.addWidget(scroll, 1)
        studio_layout.addWidget(footer)
        self.pages.addWidget(studio)
        history = QWidget()
        history.setObjectName('page')
        hist = QVBoxLayout(history)
        hist.setContentsMargins(24, 26, 24, 24)
        hist.setSpacing(16)
        hist.addWidget(label('کلمات شما، همیشه در دسترس', 'eyebrow'))
        hist.addWidget(label('تاریخچه و مقایسه', 'heading'))
        hist.addWidget(label('روی هر نتیجه دوبارکلیک کنید تا متن خام و آمار پردازش نمایش داده شود.', 'muted'))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['فایل / ضبط', 'مدل', 'مدت صوت', 'زمان تبدیل', 'تاریخ'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self.load_history)
        hist.addWidget(self.table, 1)
        history_actions = QHBoxLayout()
        history_actions.addWidget(button('بازخوانی', self.refresh_history))
        history_actions.addWidget(button('پوشه متن‌ها و ضبط‌ها', lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.data)))))
        hist.addLayout(history_actions)
        self.pages.addWidget(history)
        self.build_library()
        from ai_panel import AIPage
        self.ai_page = AIPage(lambda: self.raw_text, parent=self)
        self.pages.addWidget(self.ai_page)


    def card(self, title, description):
        card = QFrame()
        card.setObjectName('card')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)
        layout.addWidget(label(title, 'cardTitle'))
        if description:
            layout.addWidget(label(description, 'muted'))
        return card, layout

    def show_page(self, index):
        self.pages.setCurrentIndex(index)
        self.studio_nav.setChecked(index == 0)
        self.history_nav.setChecked(index == 1)
        self.library_nav.setChecked(index == 2)
        self.ai_nav.setChecked(index == 3)
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
        notices = {
            'auto': 'سازگاری شتاب‌دهنده هنگام اجرا بررسی می‌شود؛ مدل‌ها خودکار دانلود نمی‌شوند.',
            'cpu': 'پردازش محلی روی CPU انجام می‌شود.',
            'cuda': 'GPU به درایور و محیط CUDA سازگار نیاز دارد؛ در صورت خطا پردازش روی CPU ادامه می‌یابد.',
            'npu': 'NPU به مدل و محیط OpenVINO سازگار نیاز دارد؛ در صورت ناسازگاری CPU استفاده می‌شود.',
        }
        self.compute_notice.setText(notices.get(key, notices['auto']))
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

    def apply_theme(self):
        self.resolved_theme = resolve_theme(self.theme_choice, QApplication.styleHints().colorScheme())
        direction = Qt.LayoutDirection.RightToLeft if self.ui_language in RTL_LANGUAGES else Qt.LayoutDirection.LeftToRight
        alignment = 'right' if direction == Qt.LayoutDirection.RightToLeft else 'left'
        self.setStyleSheet(theme_stylesheet(STYLE, self.resolved_theme) + f'\nQPushButton#nav {{text-align:{alignment};}}')
        self.wave.dark = self.resolved_theme == 'dark'
        self.wave.update()
        for widget in self.findChildren(LocalButton):
            symbol = widget.property('symbol')
            if symbol:
                color = '#101322' if widget.objectName() == 'primary' and self.resolved_theme == 'dark' else (
                    '#ffffff' if widget.objectName() == 'primary' else '#b8c3d6' if self.resolved_theme == 'dark' else '#66748c')
                widget.setIcon(icon(symbol, color))
        if self.recording:
            self.record_button.setIcon(icon('stop', '#ffb3c8' if self.resolved_theme == 'dark' else '#a42d4d'))
        image = self.brand_pixmap().scaled(256, 192, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        image.setDevicePixelRatio(2)
        self.brand_label.setPixmap(image)
        if self.resolved_theme == 'dark':
            effect = self.brand_label.graphicsEffect()
            if not isinstance(effect, QGraphicsColorizeEffect):
                effect = QGraphicsColorizeEffect(self.brand_label)
                self.brand_label.setGraphicsEffect(effect)
            effect.setColor(QColor('#eef2ff'))
            effect.setStrength(1.0)
        else:
            # Qt owns/deletes the previous effect when it is detached.
            self.brand_label.setGraphicsEffect(None)
        self.setWindowIcon(QIcon(self.brand_pixmap(True)))
        if hasattr(self, 'ai_page') and hasattr(self.ai_page, 'apply_theme'):
            self.ai_page.apply_theme(self.resolved_theme)

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
        self.setWindowTitle(tr('Voxriva — استودیوی گفتار آفلاین'))
        for widget in self.findChildren(LocalLabel) + self.findChildren(LocalButton):
            widget.retranslate()
        for widget in self.findChildren(ComboBox):
            widget.retranslate()
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
        self.update()

    def update_transcript_direction(self, language=None):
        code = language or (self.run_language if self.raw_text else self.language.currentData())
        direction = Qt.LayoutDirection.RightToLeft if code in {'azb', 'fa', 'ar', 'ur', 'he', 'ps', 'sd', 'yi'} else Qt.LayoutDirection.LeftToRight
        self.text.setLayoutDirection(direction)
        option = self.text.document().defaultTextOption()
        option.setTextDirection(direction)
        option.setAlignment(Qt.AlignmentFlag.AlignRight if direction == Qt.LayoutDirection.RightToLeft else Qt.AlignmentFlag.AlignLeft)
        self.text.document().setDefaultTextOption(option)

    def language_changed(self, *args):
        if not hasattr(self, 'model_notice'):
            return
        previous = self.model.currentData()
        self.model.blockSignals(True)
        self.model.clear()
        for item in models_for_language(self.language.currentData()):
            self.model.addItem(f'{item["title"]}  ·  {item["size"]}', item['key'])
            self.model.setItemData(self.model.count()-1, item['detail'], Qt.ItemDataRole.ToolTipRole)
        index = self.model.findData(previous)
        if index < 0:
            # Base Full for AZB; Base balances speed/download size for other languages.
            preferred = 'whisper-base-full' if self.language.currentData() == 'azb' else 'multilingual-base'
            index = self.model.findData(preferred)
        self.model.setCurrentIndex(max(0, index))
        self.model.blockSignals(False)
        self.selection_changed()

    def selection_changed(self, *args):
        if not hasattr(self, 'model_notice') or not self.model.currentData():
            return
        key = self.model.currentData()
        ready = find_local_model(key) is not None
        self.model_readiness[key] = ready
        self.model_notice.setText('مدل آماده است؛ تبدیل بدون اینترنت انجام می‌شود.' if ready else
                                  'این مدل هنوز روی دستگاه نیست؛ از کتابخانه دانلود کنید یا مدل محلی را معرفی کنید.')
        self.library_button.setText('کتابخانه مدل‌ها' if ready else 'دریافت مدل')
        self.controls()
        self.refresh_compute_options()
        self.update_transcript_direction()
        self.save_settings()

    def save_settings(self):
        if not hasattr(self, 'language') or not self.model.currentData():
            return False
        payload = dict(self.saved_settings)
        payload.update({'language': self.language.currentData(), 'model': self.model.currentData(),
                        'ui_language': self.ui_language, 'theme': self.theme_choice,
                        'star_prompt_seen': self.star_prompt_seen,
                        'device': self.compute_device.currentData(),
                        'chunk_seconds': self.chunk_seconds.currentData()})
        try:
            temporary = self.data/'settings.json.tmp'
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
            os.replace(temporary, self.data/'settings.json')
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
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 22)
        layout.setSpacing(14)
        title_row = QHBoxLayout()
        title_text = QVBoxLayout()
        title_text.addWidget(label('مرز زبان را بردارید', 'eyebrow'))
        title_text.addWidget(label('به زبان خودتان.', 'heading'))
        title_text.addWidget(label('زبان را انتخاب کنید، مدل مناسب را دریافت کنید و آفلاین بنویسید.', 'muted'))
        title_row.addLayout(title_text, 1)
        title_row.addWidget(label(f'{len(LANGUAGES)} زبان در دسترس', 'badge'))
        layout.addLayout(title_row)
        filters = QHBoxLayout()
        filters.addWidget(label('زبان موردنظر'))
        self.library_language = ComboBox()
        self.library_language.setProperty('speechSelector', True)
        self.library_language.setAccessibleName('فیلتر زبان کتابخانه')
        for item in LANGUAGES:
            self.library_language.addItem(item['title'], item['code'])
        self.library_language.currentIndexChanged.connect(self.rebuild_library)
        filters.addWidget(self.library_language, 1)
        filters.addWidget(button('افزودن مدل محلی', self.import_local_models, symbol='file'))
        layout.addLayout(filters)
        self.library_note = label('مدل‌های آذربایجانی این بخش، مخصوص گونه رایج در ایران هستند.', 'muted')
        layout.addWidget(self.library_note)
        self.library_scroll = QScrollArea()
        self.library_scroll.setWidgetResizable(True)
        self.library_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.library_body = QWidget()
        self.library_body.setObjectName('page')
        self.library_cards = QGridLayout(self.library_body)
        self.library_cards.setContentsMargins(0, 0, 4, 0)
        self.library_cards.setSpacing(14)
        self.library_cards.setColumnStretch(0, 1)
        self.library_cards.setColumnStretch(1, 1)
        self.library_scroll.setWidget(self.library_body)
        layout.addWidget(self.library_scroll, 1)
        self.library_footer = label('مدل‌ها یک بار دانلود می‌شوند. پردازش فایل‌ها و ضبط‌های شما همیشه روی همین دستگاه انجام می‌شود.', 'muted')
        layout.addWidget(self.library_footer)
        self.pages.addWidget(page)
        self.rebuild_library()

    def rebuild_library(self, *args):
        while self.library_cards.count():
            item = self.library_cards.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self.download_widgets = {}
        language = self.library_language.currentData()
        self.library_note.setText('مدل‌های اختصاصی برای آذربایجانی رایج در ایران؛ به زبان خودتان و با خط اصلی مدل.'
                                  if language == 'azb' else
                                  'این مدل‌های چندزبانه روی CPU اجرا می‌شوند. با تغییر زبان، مدل دانلودشده دوباره دریافت نمی‌شود؛ دقت به زبان و کیفیت صدا بستگی دارد.')
        for index, item in enumerate(models_for_language(language)):
            key = item['key']
            card = QFrame()
            card.setObjectName('modelCard')
            content = QVBoxLayout(card)
            content.setContentsMargins(16, 14, 16, 14)
            content.setSpacing(8)
            headline = QHBoxLayout()
            heading = label(item['title'].replace('AZB · ', '').replace(' · چندزبانه', ''), 'libraryTitle')
            heading.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            headline.addWidget(heading, 1)
            size = label(item['size'], 'badge')
            size.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            headline.addWidget(size)
            content.addLayout(headline)
            description = label(item['detail'], 'muted')
            description.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            content.addWidget(description)
            bar = QProgressBar()
            bar.setObjectName('downloadProgress')
            bar.setRange(0, 1000)
            bar.setTextVisible(False)
            bar.setProperty('sourceAccessibleName', f'پیشرفت دانلود {item["title"]}')
            bar.setAccessibleName(tr(f'پیشرفت دانلود {item["title"]}'))
            content.addWidget(bar)
            status = label('آماده دریافت', 'muted')
            status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            content.addWidget(status)
            actions = QHBoxLayout()
            start = button('دانلود مدل', lambda checked=False, k=key: self.download_action(k, 'start'), 'primary', 'download')
            pause = button('توقف موقت', lambda checked=False, k=key: self.download_action(k, 'pause'))
            cancel = button('لغو دانلود', lambda checked=False, k=key: self.download_action(k, 'cancel'))
            use = button('استفاده از مدل', lambda checked=False, k=key: self.use_model(k), 'accent')
            for action in [start, pause, cancel, use]:
                actions.addWidget(action)
            content.addLayout(actions)
            disclosure = LocalButton('جزئیات مدل و مجوزها')
            disclosure.setObjectName('link')
            disclosure.setCursor(Qt.CursorShape.PointingHandCursor)
            disclosure.setMinimumHeight(28)
            disclosure.setCheckable(True)
            content.addWidget(disclosure)
            details = QFrame()
            details.setObjectName('disclosure')
            details_layout = QVBoxLayout(details)
            details_layout.setContentsMargins(10, 8, 10, 8)
            details_layout.addWidget(label(f'مجوز: {item.get("license", "مشاهده در منبع")}  ·  پردازش روی CPU', 'muted'))
            if item['backend'] == 'transformers':
                details_layout.addWidget(label('مدل آذربایجانی جنوبی · مؤسسه Kartal Ol', 'muted'))
                details_layout.addWidget(button('Kartal Ol / GitHub', lambda: QDesktopServices.openUrl(QUrl('https://github.com/Kartalol')), 'link'))
            details_layout.addWidget(button('مشاهده منبع و شرایط مدل', lambda checked=False, url=item['url']: QDesktopServices.openUrl(QUrl(url)), 'link'))
            details.hide()
            disclosure.toggled.connect(details.setVisible)
            content.addWidget(details)
            self.library_cards.addWidget(card, index//2, index%2)
            self.download_widgets[key] = {'bar': bar, 'status': status, 'start': start, 'pause': pause,
                                          'cancel': cancel, 'use': use}
        self.library_cards.setRowStretch((len(models_for_language(language))+1)//2, 1)
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
        labels = {'idle': 'آماده دریافت', 'resolving': 'آماده‌سازی دانلود', 'downloading': 'در حال دانلود',
                  'paused': 'متوقف موقت؛ برای ادامه آماده است', 'verifying': 'بررسی صحت فایل‌ها',
                  'completed': 'آماده استفاده آفلاین', 'cancelled': 'دانلود لغو شد', 'error': 'دانلود کامل نشد'}
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
            state = 'completed' if ready else snapshot.get('status', 'idle')
            active = state in {'resolving', 'downloading', 'verifying'}
            done = float(snapshot.get('bytes_done', 0) or 0)
            total = float(snapshot.get('bytes_total', item.get('bytes', 0)) or item.get('bytes', 0))
            percent = max(0., min(100., 100*done/total)) if total else 0.
            widgets['bar'].setRange(0, 0 if state == 'resolving' else 1000)
            if state != 'resolving':
                widgets['bar'].setValue(1000 if ready else int(percent*10))
            status = labels.get(state, state)
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
            widgets['status'].setText(status)
            widgets['start'].setVisible(not ready)
            widgets['start'].setText('ادامه دانلود' if state in {'paused', 'error'} else 'دانلود مدل')
            widgets['start'].setEnabled(not active and state != 'cancelled-pending')
            widgets['pause'].setVisible(active)
            widgets['pause'].setEnabled(state in {'resolving', 'downloading', 'verifying'})
            widgets['cancel'].setVisible(not ready and (active or state == 'paused'))
            widgets['cancel'].setEnabled(active or state == 'paused')
            widgets['use'].setVisible(ready)
            widgets['use'].setEnabled(ready and not self.busy and not self.recording)
        if readiness_changed and hasattr(self, 'model_notice'):
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
        if self.busy or self.recording:
            return
        language = self.library_language.currentData()
        index = self.language.findData(language)
        self.language.setCurrentIndex(index)
        index = self.model.findData(key)
        if index >= 0:
            self.model.setCurrentIndex(index)
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
        ready = self.model_readiness.get(self.model.currentData(), False)
        for item in [self.language, self.model, self.mode, self.devices, self.refresh_button,
                     self.compute_device, self.chunk_seconds]:
            item.setEnabled(idle)
        self.choose_button.setEnabled(idle and ready)
        self.record_button.setEnabled(not self.busy and (ready or self.recording) and self.devices.currentData() is not None)
        self.retry_button.setEnabled(idle and ready and self.last_audio is not None)
        self.cancel_button.setEnabled(self.busy and not self.cancelled)
        self.ai_button.setEnabled(bool(self.raw_text))

    def choose_file(self):
        if self.busy or self.recording:
            return
        path, _ = QFileDialog.getOpenFileName(self, tr('انتخاب ویس'), '', 'Audio (*.wav *.mp3 *.m4a *.ogg)')
        if path:
            self.start_transcription(Path(path))

    def retry(self):
        if self.last_audio:
            self.start_transcription(self.last_audio)

    def start_transcription(self, audio):
        if self.busy or self.recording:
            return
        if not self.model.currentData() or find_local_model(self.model.currentData()) is None:
            self.status.setText('ابتدا مدل این زبان را دریافت کنید یا پوشه مدل محلی را معرفی کنید.')
            self.open_selected_library()
            return
        audio = Path(audio)
        if not audio.is_file() or audio.suffix.lower() not in FORMATS:
            self.error('یک فایل WAV، MP3، M4A یا OGG معتبر انتخاب کنید.')
            return
        self.last_audio = audio.resolve()
        self.run_model = self.model.currentData()
        self.run_language = self.language.currentData()
        self.source_name.setProperty('literalText', True)
        self.source_name.setText(audio.name)
        self.source_name.setToolTip(str(audio))
        self.result_model.setText(self.model.currentText())
        self.output = self.data/'results'/f'{audio.stem}-{self.run_model}-{time.strftime("%Y%m%d-%H%M%S")}-{uuid.uuid4().hex[:6]}.txt'
        self.started = time.monotonic()
        self.cancelled = False
        self.raw_text = ''
        self.ai_button.setEnabled(False)
        self.text.clear()
        self.copy_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.show_page(0)
        self.busy = True
        if getattr(sys, 'frozen', False):
            command = [sys.executable]
        else:
            command = [sys.executable, str(Path(__file__).resolve().parent/'entrypoint.py')]
        command += ['--worker', str(self.last_audio), '--output', str(self.output), '--model', self.run_model,
                    '--beams', str(self.mode.currentData()), '--language', self.run_language,
                    '--device', self.compute_device.currentData(),
                    '--chunk-seconds', str(self.chunk_seconds.currentData())]
        try:
            self.process = subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except OSError as exc:
            self.busy = False
            self.process = None
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.error(str(exc))
        self.controls()

    def toggle_recording(self):
        if self.recording:
            self.record_button.setText('در حال پایان ضبط…')
            self.record_button.setEnabled(False)
            self.recorder.stop_event.set()
            return
        if self.busy or self.devices.currentData() is None:
            return
        if not self.model.currentData() or find_local_model(self.model.currentData()) is None:
            self.open_selected_library()
            return
        path = self.data/'recordings'/f'voice-{time.strftime("%Y%m%d-%H%M%S")}-{uuid.uuid4().hex[:6]}.wav'
        self.recorder = Recorder(self.devices.currentData(), path)
        self.recorder.level.connect(self.wave.push)
        self.recorder.ready.connect(self.record_ready)
        self.recorder.recorded.connect(self.record_finished)
        self.recorder.failed.connect(self.record_error)
        self.recording = True
        self.mic_ready = False
        self.started = time.monotonic()
        self.wave.active = True
        self.record_button.setText('آماده‌سازی میکروفون…')
        self.record_button.setObjectName('danger')
        self.record_button.setIcon(icon('stop', '#ffb3c8' if self.resolved_theme == 'dark' else '#a42d4d'))
        self.record_button.style().unpolish(self.record_button)
        self.record_button.style().polish(self.record_button)
        self.controls()
        self.record_button.setEnabled(False)
        self.recorder.start()

    def record_ready(self):
        self.mic_ready = True
        self.started = time.monotonic()
        self.record_button.setText('پایان ضبط و تبدیل')
        self.record_button.setEnabled(True)

    def reset_recording(self):
        self.recording = False
        self.mic_ready = False
        self.wave.active = False
        self.wave.update()
        self.record_button.setText('شروع ضبط')
        self.record_button.setObjectName('primary')
        self.record_button.setIcon(icon('mic', '#101322' if self.resolved_theme == 'dark' else '#ffffff'))
        self.record_button.style().unpolish(self.record_button)
        self.record_button.style().polish(self.record_button)
        self.controls()

    def record_finished(self, path, duration):
        if self.closing:
            return
        self.reset_recording()
        self.start_transcription(Path(path))

    def record_error(self, detail):
        if self.closing:
            return
        self.reset_recording()
        self.status.setText('ضبط انجام نشد؛ میکروفون و اجازه دسترسی در تنظیمات ویندوز را بررسی کنید.')
        self.error(detail)

    def tick(self):
        now = time.monotonic()
        if now - self.last_library_poll > .8:
            self.last_library_poll = now
            self.refresh_library()
        if self.recording:
            if self.mic_ready:
                duration = int(time.monotonic()-self.started)
                self.status.setText(f'در حال ضبط  ·  {duration//60:02d}:{duration%60:02d}  ·  برای تبدیل، پایان ضبط را بزنید.')
            else:
                self.status.setText('در حال آماده‌سازی میکروفون؛ پس از فعال‌شدن دکمه پایان ضبط، صحبت کنید.')
        elif self.busy and self.process:
            duration = int(time.monotonic()-self.started)
            phases = {'preparing': 'آماده‌سازی', 'decoding': 'خواندن صوت', 'loading': 'بارگذاری مدل',
                      'transcribing': 'تشخیص گفتار', 'done': 'ذخیره نتیجه', 'error': 'خطا',
                      'fallback': 'بازگشت به CPU'}
            phase = 'آماده‌سازی'
            try:
                progress = json.loads(self.output.with_suffix('.progress.json').read_text(encoding='utf-8'))
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
            if self.process.poll() is not None:
                self.complete()

    def complete(self):
        returncode = self.process.returncode
        self.process = None
        self.busy = False
        self.progress.setRange(0, 100)
        if self.cancelled:
            self.progress.setValue(0)
            self.status.setText('تبدیل متوقف شد؛ می‌توانید فایل یا مدل دیگری انتخاب کنید.')
        else:
            try:
                metrics = json.loads(self.output.with_suffix('.metrics.json').read_text(encoding='utf-8'))
                if returncode or metrics.get('status') != 'success':
                    raise RuntimeError('\n'.join(metrics.get('errors', [])) or 'تبدیل کامل نشد.')
                self.display_result(self.output, metrics)
                self.progress.setValue(100)
                self.status.setText('تبدیل تمام شد؛ متن و گزارش خودکار ذخیره شدند.')
                if metrics.get('fallback_reasons'):
                    self.status.setText('تبدیل تمام شد؛ شتاب‌دهنده در دسترس نبود و CPU استفاده شد.')
                    self.status.setToolTip('\n'.join(str(x) for x in metrics['fallback_reasons']))
                QTimer.singleShot(1200, self.maybe_prompt_star)
            except Exception as exc:
                self.progress.setValue(0)
                log = self.output.with_suffix('.log')
                self.status.setText('تبدیل ناموفق بود؛ فایل گزارش برای عیب‌یابی نگه داشته شد.')
                self.error(str(exc) + f'\n\nگزارش: {log}')
        self.controls()
        self.refresh_history()

    def display_result(self, path, metrics):
        self.raw_text = path.read_text(encoding='utf-8')
        self.text.setPlainText(self.raw_text)
        self.update_transcript_direction(metrics.get('language'))
        self.copy_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.ai_button.setEnabled(True)
        self.output = path
        self.result_model.setText(metrics.get('subfolder') or metrics.get('model', ''))
        self.metrics_label.setText(f'صوت: {metrics.get("audio_seconds",0):.1f} ثانیه   |   '
                                   f'تشخیص: {metrics.get("inference_seconds",0):.1f} ثانیه   |   '
                                   f'کل: {metrics.get("total_seconds",0):.1f} ثانیه   |   '
                                   f'RAM: {metrics.get("peak_rss_mib_sampled",0):.0f} MiB   |   '
                                   f'{str(metrics.get("device", "cpu")).upper()}')
        if metrics.get('fallback_reasons'):
            self.metrics_label.setToolTip('\n'.join(str(x) for x in metrics['fallback_reasons']))

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
        box.setWindowTitle(tr('از Voxriva حمایت کنید'))
        box.setText(tr('اگر Voxriva برایتان مفید بود، می‌توانید به مخزن آن در گیت‌هاب ستاره بدهید. این پیشنهاد فقط یک‌بار نمایش داده می‌شود.'))
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
                metrics = json.loads(path.read_text(encoding='utf-8'))
                text_path = path.with_name(path.name.replace('.metrics.json', '.txt'))
                if metrics.get('status') == 'success' and text_path.exists():
                    records.append((text_path, metrics))
            except (OSError, ValueError):
                pass
        self.table.setRowCount(len(records))
        for row, (path, metrics) in enumerate(records):
            self.history_paths.append(path)
            language = next((language_title(x) for x in LANGUAGES if x['code'] == metrics.get('language')), metrics.get('language', ''))
            values = [path.stem.split('-whisper')[0], metrics.get('subfolder') or metrics.get('model', ''), f'{metrics.get("audio_seconds",0):.1f}s',
                      f'{metrics.get("total_seconds",0):.1f}s', time.strftime('%Y-%m-%d %H:%M', time.localtime(path.stat().st_mtime))]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
                self.table.item(row, col).setToolTip(language)
            self.table.setRowHeight(row, 48)

    def load_history(self, row, column):
        if self.busy or self.recording:
            return
        path = self.history_paths[row]
        metrics = json.loads(path.with_suffix('.metrics.json').read_text(encoding='utf-8'))
        self.display_result(path, metrics)
        self.show_page(0)
        self.status.setText('نتیجه ذخیره‌شده از تاریخچه نمایش داده شد.')

    def cancel(self):
        if self.busy and self.process:
            self.cancelled = True
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
        self.start_transcription(Path(event.mimeData().urls()[0].toLocalFile()))
        event.acceptProposedAction()

    def error(self, text):
        QMessageBox.warning(self, tr('نیاز به بررسی'), tr(text))

    def about(self):
        box = QMessageBox(self)
        box.setWindowTitle(tr('درباره Voxriva'))
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText('<b>Voxriva</b><p>' + tr('توسعه‌دهنده برنامه') + ': <b>Fardin Milani</b><br>'
                    '<a href="https://github.com/Fardinmilani">GitHub / Fardinmilani</a> · '
                    '<a href="https://fardinmilani.ir">fardinmilani.ir</a><br>'
                    '<a href="https://github.com/Fardinmilani/Voxriva">Voxriva / GitHub</a></p><p>' +
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
    app = QApplication(sys.argv)
    app.setApplicationName('Voxriva')
    app.setOrganizationName('Voxriva')
    app.setFont(QFont('Segoe UI', 10))
    window = Studio()
    screen = app.primaryScreen().availableGeometry()
    window.resize(min(1280, screen.width()-40), min(880, screen.height()-60))
    window.show()
    if page is not None:
        window.show_page({'studio': 0, 'history': 1, 'library': 2, 'ai': 3}.get(str(page), 0))
    if audio:
        QTimer.singleShot(300, lambda: window.start_transcription(Path(audio)))
    if preview:
        window.allow_star_prompt = False
        def capture():
            window.grab().save(str(preview))
            window.close()
            app.quit()
        QTimer.singleShot(700, capture)
    sys.exit(app.exec())
