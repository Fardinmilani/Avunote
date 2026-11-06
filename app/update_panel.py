"""A small Qt update surface; network and disk verification stay off the UI thread."""
from __future__ import annotations

import os
import threading

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QHBoxLayout,
                               QLabel, QProgressBar, QPushButton, QVBoxLayout)

from app_updates import (Update, UpdateCancelled, baseline_digest, check_release, clean_staged_updates,
                         delta_name, install_root, launch_installer, running_version,
                         stage_update, verify_staged)
from model_catalog import data_root
from ui_i18n import RTL_LANGUAGES, current_language, tr


def _byte_label(size):
    if size >= 1_000_000:
        return f'{size / 1_000_000:.1f} MB'
    return f'{max(1, round(size / 1000))} KB'


class UpdateController(QObject):
    available = Signal(str)
    _finished = Signal(str, object, object)
    _progress = Signal(int)

    def __init__(self, parent, request_close=None):
        super().__init__(parent)
        self.window = parent
        self.request_close = request_close or parent.close
        self.version = running_version()
        self.root = install_root(self.version)
        self.release = None
        self.staged = None
        self.job = None
        self.dialog = None
        self.cancel_event = threading.Event()
        self.state = ''
        self.last_detail = ''
        self.checked = False
        self._finished.connect(self._complete)
        self._progress.connect(self._show_progress)
        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(6 * 60 * 60 * 1000)
        self._auto_timer.timeout.connect(self.check_background)

    def check_background(self):
        if not self.root or os.environ.get('AVUNOTE_DISABLE_UPDATES') == '1':
            return
        if not self._auto_timer.isActive():
            self._auto_timer.start()
        self._check()

    def _start(self, name, operation):
        if self.job:
            return
        self.job = name

        def work():
            try:
                value, error = operation(), None
            except (OSError, ValueError, UpdateCancelled) as exc:
                value, error = None, exc
            except Exception as exc:
                value, error = None, exc
            try:
                self._finished.emit(name, value, error)
            except RuntimeError:
                # The window can be closed while a background check is pending.
                pass

        threading.Thread(target=work, name=f'avunote-update-{name}', daemon=True).start()
        self._refresh()

    def _check(self):
        if self.job or self.staged is not None:
            return
        if os.environ.get('AVUNOTE_DISABLE_UPDATES') == '1':
            self._state('Automatic update checks are off.')
            return
        self._state('Checking for updates…')
        def check():
            clean_staged_updates(data_root() / 'updates', self.version)
            return check_release(self.version, self.root)

        self._start('check', check)

    def open_dialog(self):
        if self.dialog is None:
            dialog = QDialog(self.window)
            dialog.setMinimumWidth(370)
            self.dialog = dialog
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(12)
            self.title = QLabel()
            self.title.setObjectName('sectionTitle')
            layout.addWidget(self.title)
            self.status = QLabel()
            self.status.setWordWrap(True)
            layout.addWidget(self.status)
            self.details = QLabel()
            self.details.setWordWrap(True)
            self.details.setObjectName('muted')
            layout.addWidget(self.details)
            self.progress = QProgressBar()
            self.progress.setRange(0, 100)
            self.progress.setTextVisible(False)
            layout.addWidget(self.progress)
            self.progress_text = QLabel()
            self.progress_text.setObjectName('muted')
            layout.addWidget(self.progress_text)
            buttons = QHBoxLayout()
            self.action = QPushButton()
            self.action.setMinimumHeight(42)
            self.action.setObjectName('primary')
            self.action.clicked.connect(self._action)
            buttons.addWidget(self.action)
            self.cancel = QPushButton()
            self.cancel.setMinimumHeight(42)
            self.cancel.clicked.connect(self.cancel_event.set)
            buttons.addWidget(self.cancel)
            buttons.addStretch(1)
            close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            close.rejected.connect(dialog.hide)
            self.close_button = close.button(QDialogButtonBox.StandardButton.Close)
            self.close_button.setMinimumHeight(42)
            buttons.addWidget(close)
            layout.addLayout(buttons)
        self.retranslate_ui()
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
        if not self.checked and not self.job and self.root:
            self._check()

    def retranslate_ui(self):
        if self.dialog:
            self.dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft
                                           if current_language() in RTL_LANGUAGES
                                           else Qt.LayoutDirection.LeftToRight)
            self._refresh()

    def _state(self, text, detail=''):
        self.state = text
        self.last_detail = detail
        self._refresh()

    def _refresh(self):
        if self.dialog is None:
            return
        self.dialog.setWindowTitle(tr('Updates'))
        self.title.setText(tr('Updates'))
        details = [tr('Installed: {version}').format(version=self.version)]
        status = tr(self.state) if self.state else ''
        if not self.root:
            status = tr('Windows Setup installation required for in-app updates.')
        if self.release:
            if not status or self.state == 'Update available':
                status = tr('Update available: {version}').format(version=self.release.version)
            asset = self.release.delta or self.release.setup
            details.append(tr('Download size: {size}').format(size=_byte_label(asset.size)))
            if self.release.delta:
                details.append(tr('Update is smaller because only changed files are included.'))
        self.status.setText(status)
        self.status.setToolTip(self.last_detail)
        self.details.setText('\n'.join(details))
        self.progress.setVisible(self.job == 'download')
        self.progress_text.setVisible(self.job == 'download')
        self.cancel.setVisible(self.job == 'download')
        self.cancel.setText(tr('Cancel download'))
        self.close_button.setText(tr('Close'))
        label = ('Restart and install' if self.staged else
                 'Download update' if self.release else 'Check for updates')
        self.action.setText(tr(label))
        self.action.setVisible(bool(self.root))
        self.action.setEnabled(not self.job)

    def _show_progress(self, percent):
        if self.dialog:
            self.progress.setValue(percent)
            self.progress_text.setText(f'{percent}%')

    def _action(self):
        if self.job or not self.root:
            return
        if self.release is None:
            self._check()
            return
        asset = self.release.delta or self.release.setup
        if self.staged is not None:
            def verify():
                if self.release.delta:
                    baseline = baseline_digest(self.root, self.version, verify_files=True)
                    if not baseline or asset.name != delta_name(self.release.version, self.version, baseline):
                        return 'full'
                return verify_staged(self.staged, asset)

            self._start('verify', verify)
            return
        self.cancel_event.clear()
        self._show_progress(0)
        self._state('Downloading update…')

        def download():
            previous = -1

            def progress(count, total):
                nonlocal previous
                percent = count * 100 // total
                if percent != previous:
                    self._progress.emit(percent)
                    previous = percent

            return stage_update(asset, data_root() / 'updates', self.cancel_event, progress)

        self._start('download', download)

    def _complete(self, name, result, error):
        self.job = None
        if name == 'check':
            self.checked = error is None
            if error is not None:
                self._state("Couldn't check for updates.", str(error))
                return
            self.release = result
            if result is None:
                self._state("You're up to date.")
            else:
                self._state('Update available')
                self.available.emit(result.version)
        elif name == 'download':
            if isinstance(error, UpdateCancelled):
                self._state('Download cancelled.')
            elif error:
                self._state("Couldn't download the update.", str(error))
            else:
                self.staged = result
                self._state('Update ready to install.')
        elif name == 'verify':
            if result == 'full':
                self.staged = None
                self.release = Update(self.release.version, self.release.setup)
                self._state('Update available')
            elif not result or error:
                self.staged = None
                self._state("Couldn't start the installer.", str(error or 'SHA-256 mismatch'))
            else:
                self._install()

    def _install(self):
        app = QApplication.instance()
        old_quit = app.quitOnLastWindowClosed()
        app.setQuitOnLastWindowClosed(False)
        self.dialog.hide()
        try:
            if not self.request_close():
                self._state('Close the active task before installing the update.')
                self.dialog.show()
                return
            launch_installer(self.staged, self.root, self.version)
        except (OSError, ValueError) as exc:
            self._state("Couldn't start the installer.", str(exc))
            self.window.show()
            self.dialog.show()
        else:
            app.quit()
        finally:
            app.setQuitOnLastWindowClosed(old_quit)
