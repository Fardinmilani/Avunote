"""Windows lock regression tests; no ASR models or network are needed."""
import ctypes
import errno
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import traceback
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
import atomic_files


class AtomicFileTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.target = self.root / 'progress.json'

    def tearDown(self):
        self.folder.cleanup()

    def assert_no_temporary_files(self):
        self.assertFalse(list(self.root.glob('*.tmp')))

    def test_preserves_unicode_and_exact_written_text(self):
        raw = '  متنِ خام، Əİö؟\nبدون بازنویسی  '
        atomic_files.atomic_write_text(self.target, raw)
        self.assertEqual(self.target.read_bytes(), raw.encode('utf-8'))
        self.assertEqual(atomic_files.read_text_shared(self.target), raw)
        self.assert_no_temporary_files()

    def test_permanent_permission_failure_preserves_previous_checkpoint(self):
        self.target.write_text('previous', encoding='utf-8')
        began = time.monotonic()
        with patch.object(atomic_files.os, 'replace', side_effect=PermissionError(errno.EACCES, 'denied')) as replace:
            with self.assertRaises(PermissionError):
                atomic_files.atomic_write_text(self.target, 'new', timeout=.04)
        self.assertGreaterEqual(replace.call_count, 2)
        self.assertLess(time.monotonic() - began, 1.0)
        self.assertEqual(self.target.read_text(encoding='utf-8'), 'previous')
        self.assert_no_temporary_files()

    def test_non_permission_io_error_propagates_without_retry(self):
        self.target.write_text('previous', encoding='utf-8')
        with patch.object(atomic_files.os, 'replace', side_effect=OSError(errno.ENOSPC, 'disk full')) as replace:
            with self.assertRaises(OSError) as error:
                atomic_files.atomic_write_text(self.target, 'new')
        self.assertEqual(error.exception.errno, errno.ENOSPC)
        self.assertEqual(replace.call_count, 1)
        self.assertEqual(self.target.read_text(encoding='utf-8'), 'previous')
        self.assert_no_temporary_files()

    def test_missing_parent_and_missing_reader_path_remain_actionable(self):
        with self.assertRaises(FileNotFoundError):
            atomic_files.atomic_write_text(self.root / 'missing/file.json', '{}')
        with self.assertRaises(FileNotFoundError):
            atomic_files.read_text_shared(self.target)

    def test_invalid_timeout_rejected_before_creating_temporary_files(self):
        for timeout in [-1, float('inf'), float('nan')]:
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                atomic_files.atomic_write_text(self.target, 'new', timeout=timeout)
        self.assert_no_temporary_files()

    @unittest.skipUnless(os.name == 'nt', 'Native Windows file-sharing regression')
    def test_native_windows_reader_lock_is_retried_until_released(self):
        from ctypes import wintypes
        self.target.write_text('previous', encoding='utf-8')
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create_file.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        # A normal reader that omits FILE_SHARE_DELETE reproduces WinError 5.
        handle = create_file(str(self.target), 0x80000000, 0x1 | 0x2, None, 3, 0x80, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
        errors = []
        def replace_checkpoint():
            try:
                atomic_files.atomic_write_text(self.target, 'new', timeout=1.0)
            except BaseException as error:
                errors.append(error)
        writer = threading.Thread(target=replace_checkpoint)
        writer.start()
        try:
            time.sleep(.1)
            self.assertTrue(writer.is_alive(), 'The native lock did not hold replacement')
            self.assertEqual(self.target.read_text(encoding='utf-8'), 'previous')
        finally:
            kernel32.CloseHandle(handle)
            writer.join(2)
        self.assertFalse(writer.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(self.target.read_text(encoding='utf-8'), 'new')
        self.assert_no_temporary_files()

    def test_simultaneous_writers_and_readers_only_observe_complete_json(self):
        atomic_files.atomic_write_text(self.target, json.dumps({'writer': -1, 'value': 0, 'payload': 'Ə' * 1024}))
        failures = []
        running = threading.Event()
        running.set()
        def writer(identifier):
            try:
                for index in range(50):
                    atomic_files.atomic_write_text(self.target, json.dumps({'writer': identifier, 'value': index, 'payload': 'Ə' * 1024}))
            except BaseException as error:
                failures.append(('writer', traceback.format_exc()))
        def reader():
            try:
                while running.is_set():
                    value = json.loads(atomic_files.read_text_shared(self.target))
                    if value['payload'] != 'Ə' * 1024:
                        raise AssertionError('Observed a partial checkpoint')
                    # Poll more aggressively than the UI, but leave a quiescent
                    # interval: continuously held locks are intentionally bounded.
                    time.sleep(.003)
            except BaseException as error:
                failures.append(('reader', traceback.format_exc()))
        readers = [threading.Thread(target=reader) for _ in range(3)]
        writers = [threading.Thread(target=writer, args=(identifier,)) for identifier in range(2)]
        for thread in readers + writers:
            thread.start()
        try:
            for thread in writers:
                thread.join(10)
                self.assertFalse(thread.is_alive())
        finally:
            running.clear()
            for thread in readers:
                thread.join(3)
        self.assertFalse(any(thread.is_alive() for thread in readers))
        self.assertEqual(failures, [])
        self.assert_no_temporary_files()


if __name__ == '__main__':
    unittest.main()
