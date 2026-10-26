"""Desktop presence via Win32 metadata only: no UI text, credentials or commands."""
import ctypes
import os
from ctypes import wintypes
from PySide6.QtCore import QObject, QTimer, Signal


def classify_windows(windows, processes, own_pid):
    """windows: (pid, executable path); processes: (pid, parent pid)."""
    excluded = {own_pid}
    while True:
        children = {pid for pid, parent in processes if parent in excluded}
        expanded = excluded | children
        if expanded == excluded:
            break
        excluded = expanded
    codex = claude = False
    for pid, path in windows:
        if pid in excluded:
            continue
        normalized = path.replace('\\', '/').lower()
        name = normalized.rsplit('/', 1)[-1]
        if name == 'claude.exe':
            claude = True
        elif name == 'codex.exe':
            codex = True
        elif name == 'chatgpt.exe' and ('/openai.codex_' in normalized or '/openai/codex/' in normalized):
            codex = True
    return codex, claude


def desktop_presence():
    if os.name != 'nt':
        raise OSError('Desktop detection requires Windows')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    user = ctypes.WinDLL('user32', use_last_error=True)
    class ProcessEntry(ctypes.Structure):
        _fields_ = [('dwSize',wintypes.DWORD),('cntUsage',wintypes.DWORD),
                    ('th32ProcessID',wintypes.DWORD),('th32DefaultHeapID',ctypes.c_size_t),
                    ('th32ModuleID',wintypes.DWORD),('cntThreads',wintypes.DWORD),
                    ('th32ParentProcessID',wintypes.DWORD),('pcPriClassBase',wintypes.LONG),
                    ('dwFlags',wintypes.DWORD),('szExeFile',wintypes.WCHAR*260)]
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD,wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE,ctypes.POINTER(ProcessEntry)]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE,ctypes.POINTER(ProcessEntry)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.OpenProcess.argtypes = [wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    user.EnumWindows.argtypes = [callback_type,wintypes.LPARAM]
    snapshot = kernel.CreateToolhelp32Snapshot(2,0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    processes, names = [], {}
    try:
        entry = ProcessEntry(); entry.dwSize = ctypes.sizeof(entry)
        if not kernel.Process32FirstW(snapshot,ctypes.byref(entry)):
            raise ctypes.WinError(ctypes.get_last_error())
        while True:
            pid = entry.th32ProcessID
            processes.append((pid,entry.th32ParentProcessID))
            names[pid] = entry.szExeFile.lower()
            if not kernel.Process32NextW(snapshot,ctypes.byref(entry)):
                break
    finally:
        kernel.CloseHandle(snapshot)
    visible = set()
    @callback_type
    def collect(hwnd, _):
        if user.IsWindowVisible(hwnd):
            pid = wintypes.DWORD()
            user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            if names.get(pid.value) in ('chatgpt.exe','codex.exe','claude.exe'):
                visible.add(pid.value)
        return True
    if not user.EnumWindows(collect,0):
        raise ctypes.WinError(ctypes.get_last_error())
    windows = []
    for pid in visible:
        handle = kernel.OpenProcess(0x1000,False,pid)  # limited query only
        if not handle:
            continue  # process may have exited during enumeration
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(buffer))
            if kernel.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(length)):
                windows.append((pid,buffer.value))
        finally:
            kernel.CloseHandle(handle)
    return classify_windows(windows,processes,os.getpid())


class ActivityMonitor(QObject):
    changed = Signal(bool,bool)
    failed = Signal()
    def __init__(self, parent=None, detector=desktop_presence):
        super().__init__(parent)
        self.detector = detector
        self.previous = None
        self.timer = QTimer(self)
        self.timer.setInterval(3000)
        self.timer.timeout.connect(self.check)
    def start(self):
        self.check()
        self.timer.start()
    def check(self):
        try:
            current = self.detector()
        except OSError:
            self.previous = None
            self.failed.emit()
            return
        if current != self.previous:
            self.previous = current
            self.changed.emit(*current)
