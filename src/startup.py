import os
import subprocess
import sys
from pathlib import Path
NAME = 'CodexUsageOverlay'
def set_startup(enabled):
    if os.name != 'nt': return
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        if enabled:
            if getattr(sys,'frozen',False): args = [sys.executable]
            else:
                pythonw = Path(sys.executable).with_name('pythonw.exe')
                args = [str(pythonw),str(Path(__file__).resolve().parent.parent/'main.py')]
            winreg.SetValueEx(key,NAME,0,winreg.REG_SZ,subprocess.list2cmdline(args))
        else:
            try: winreg.DeleteValue(key,NAME)
            except FileNotFoundError: pass
