"""Atomic UTF-8 checkpoints that tolerate short Windows reader/AV locks.

Replacement keeps readers on a complete old or new file. A bounded retry is
needed because ordinary Windows readers may temporarily omit FILE_SHARE_DELETE.
No fallback truncates the destination in place or discards the previous file.
"""
import math
import os
from pathlib import Path
import tempfile
import time


def _retryable_lock(error):
    code = getattr(error, 'winerror', None)
    return code in {5, 32, 33} or (isinstance(error, PermissionError) and code is None)


def atomic_write_text(path, text, *, timeout=2.0):
    """Replace a text file, retrying transient permission/sharing errors briefly.

    ``timeout`` bounds replacement retries, not filesystem I/O itself. If the
    lock outlives that interval or a different I/O error occurs, the original
    exception is raised and the caller's existing destination is preserved.
    """
    if not math.isfinite(timeout) or timeout < 0:
        raise ValueError('Atomic-write timeout must be finite and nonnegative')
    path = Path(path)
    descriptor, name = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
    temporary = Path(name)
    descriptor_owned = True
    try:
        stream = os.fdopen(descriptor, 'w', encoding='utf-8', newline='')
        descriptor_owned = False
        with stream:
            stream.write(text)
        deadline = time.monotonic() + timeout
        delay = .01
        while True:
            try:
                os.replace(temporary, path)
                return
            except OSError as error:
                remaining = deadline - time.monotonic()
                if not _retryable_lock(error) or remaining <= 0:
                    raise
                time.sleep(min(delay, remaining))
                delay = min(delay * 2, .1)
    finally:
        if descriptor_owned:
            os.close(descriptor)
        # A failed replacement must not leave checkpoint files accumulating.
        # Ignore cleanup failure rather than masking the actionable I/O error.
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def read_text_shared(path, *, encoding='utf-8'):
    """Read a snapshot without blocking Windows atomic replacement.

    Requesting FILE_SHARE_DELETE avoids unnecessary reader restrictions where
    supported; filesystem/security filters may still briefly block replacement,
    so writers retain bounded retries. The returned snapshot never mixes old
    and new content. Handles close on successful and failed reads.
    """
    path = Path(path)
    if os.name != 'nt':
        return path.read_text(encoding=encoding)
    import ctypes
    from ctypes import wintypes
    import msvcrt

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                            wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create_file.restype = wintypes.HANDLE
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    # GENERIC_READ; FILE_SHARE_READ | WRITE | DELETE; OPEN_EXISTING; NORMAL.
    handle = create_file(str(path), 0x80000000, 0x1 | 0x2 | 0x4, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        error = ctypes.WinError(ctypes.get_last_error())
        error.filename = str(path)
        raise error
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        close_handle(handle)
        raise
    # open_osfhandle transfers handle ownership to the CRT descriptor.
    try:
        stream = os.fdopen(descriptor, 'r', encoding=encoding)
    except BaseException:
        os.close(descriptor)
        raise
    with stream:
        return stream.read()
