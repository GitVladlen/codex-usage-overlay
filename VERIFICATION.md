# Verification — 2026-10-26

- Windows 11, Python 3.12.10, PySide6 6.8.3.
- Installed official CLI 0.163.0-alpha.10.2; generated JSON schemas inspected.
- Live stdio handshake and account/rateLimits/read succeeded, returning 300-minute and 10080-minute windows. No tokens or account identifiers printed or stored.
- 20 credential-free unittest tests passed, including a real mocked subprocess pipe and process cleanup.
- GUI smoke passed: real usage received, click-through flag toggled during unlock/relock, settings close preserved overlay, screenshot inspected, worker stopped cleanly.
- PyInstaller 6.12.0 Windows onedir build succeeded.
- Packaged EXE launched successfully and remained running; second instance exited with code 0.
- Packaged overlay left running for use; exit via its C tray icon.

Remaining manual checks: physical click-through over other applications, tray interactions, multi-monitor hot-plug and every DPI setting, startup after Windows sign-in, long-running resource use, and copying the distribution to a Python-free machine. Notification schema and mock delivery verified; no spontaneous cross-process notification was claimed during the short live check. Polling provides cross-process usage consistency.

## CLI discovery regression fix

- 21 automated tests passed, including discovery with no Codex executable on PATH.
- GUI smoke with PATH restricted to Windows System32 successfully retrieved real usage through the installed native CLI fallback.

## Compact view

- 25 automated tests passed, including compact defaults and legacy-settings migration, stale/unavailable text, weekly visibility, tray/settings switching, and preference persistence.
- GUI smoke received real usage and compact screenshot was visually inspected.
