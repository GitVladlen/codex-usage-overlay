# Codex Usage Overlay for Windows

A transparent, always-on-top PySide6 tray application. The official Codex CLI remains an external dependency; the packaged application includes Python and Qt.

## Quick start (PowerShell, ordinary user)

Run project commands from your clone directory; the example below uses `C:\projects\codex-usage-overlay`.

```powershell
Set-Location C:\projects\codex-usage-overlay
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
codex login
.\.venv\Scripts\pythonw.exe main.py
```

Install Python 3.11+ from python.org. Install the official Codex CLI following https://developers.openai.com/codex/cli (for example `npm install -g @openai/codex` with an existing trusted Node installation). Restart your terminal after PATH changes. Use `codex --version` and `codex login` in your own terminal. The overlay resolves codex.exe from PATH, with a fallback to the native executable inside the standard per-user npm package. It deliberately does not launch .cmd/.bat shell wrappers. If PATH and npm discovery fail, the overlay also discovers the native CLI under the standard per-user Codex desktop installation directory (`%LOCALAPPDATA%/OpenAI/Codex/bin/*/codex.exe`), selecting the most recently modified executable. The desktop app does not need to be running. Other installation layouts must expose the native codex.exe on PATH.

The overlay uses the CLI's authenticated account and CODEX_HOME environment. Sign into the same ChatGPT account in the CLI as in the desktop application. The overlay does not inspect account identity or automatically prove that two separate CLI/desktop profiles match. API-key accounts or plans without rolling windows may report usage unavailable. No custom login is implemented.

## Operation

The default compact view displays a single line such as `CDX · 5h 83% · W 97%` (illustrative remaining percentages). A warning symbol marks stale/error data; unavailable data displays `CDX · недоступно`. Toggle **Compact View** in the tray or the matching checkbox in Overlay Settings to switch to the full view. The choice persists across restarts; existing settings without this preference also default to compact. Compact mode respects Show weekly usage, while reset times, update details and progress bars remain in the full view.

Look for the C icon in the Windows tray (possibly under hidden icons). Right-click for Show/Hide, Refresh Now, Unlock Position, Click-through, Settings, Start with Windows, and Exit. Unlock temporarily disables click-through so the overlay can be dragged; a thin blue border, subtle blue background and move cursor indicate this mode. The border space is always reserved, so locking/unlocking changes neither text nor overlay size. Relock from the tray. Settings include monitor, font, color, opacity, refresh interval, background, optional text progress bars, reset times, weekly usage and startup. Closing settings keeps the application running. Exit stops and reaps the app-owned Codex child; it never terminates other Codex processes.

Default refresh is 30 seconds; configurable 5–3600 seconds. Reset countdowns repaint locally every second and do not make requests. Last successful reception uses local time. Errors retain in-memory values with STALE indication; no usage values are persisted. A passed reset shows zero countdown until a server snapshot arrives; the application never fabricates a reset to 100% remaining.

Settings live in `%LOCALAPPDATA%\CodexUsageOverlay\settings.json` and contain preferences only. Invalid values fall back to validated defaults. Startup uses the current user's `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` entry named CodexUsageOverlay, with properly quoted executable arguments. Disable it in the tray before moving/removing the installation. Source-mode startup points to pythonw.exe in this venv; packaged startup points to the EXE. Position uses Qt logical pixels and monitor names, supports negative screen coordinates, and clamps to the selected screen after display changes. Qt handles display scaling. The tool window is frameless, translucent, non-activating and absent from Alt+Tab; Qt's Windows transparent-input flag provides click-through.

## Build and tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\scripts\build.ps1
```

Output: `dist\CodexUsageOverlay\CodexUsageOverlay.exe`. Distribute the **entire** CodexUsageOverlay directory, not just the EXE. Python need not be installed on the target; the official native Codex CLI must be installed and signed in. The build does not download scripts or dependencies; install the pinned packages beforehand. PowerShell script execution must be permitted by your local policy; alternatively run the PyInstaller command in scripts/build.ps1 directly. `requirements-lock.txt` pins every installed build/runtime dependency; requirements.txt is the minimal runtime set. No elevation is required.

Optional `python scripts/smoke.py` (using this venv) opens the real overlay briefly, checks lock/input flags and settings lifecycle, requests actual CLI usage, saves smoke-overlay.png, then stops. Unlike unit tests this requires the signed-in CLI. Unit tests use mocks only.

## Protocol and architecture

Verified against installed `codex-cli 0.163.0-alpha.10.2` on 2026-10-26. Official documentation: https://developers.openai.com/codex/app-server (redirects to https://learn.chatgpt.com/docs/app-server). The installed protocol schemas are included under schema/, generated by `codex app-server generate-json-schema --out schema`; they are verification references, not runtime dependencies.

- codex_client.py: one persistent stdio subprocess, bounded JSON-lines reader queue, request IDs, size limits, timeouts and cleanup. No TCP listener.
- refresh_worker.py: background QThread, initialize/initialized handshake, immediate read, non-overlapping fallback polls, immediate notification handling, bounded exponential reconnect (1–30 seconds), cancellable shutdown.
- usage_model.py: validates fields consumed by the app, selects rateLimitsByLimitId.codex when available, falls back to rateLimits, identifies windows by duration (300 and 10080 minutes), and converts consumed usedPercent to clamped remaining percentage. Null/missing windows remain unavailable rather than becoming zero usage.
- overlay.py: GUI-only rendering, one-second countdown, drag, display positioning.
- config.py, settings.py, startup.py and tray.py: preference validation, atomic JSON persistence, dialogs and tray controls.

Reads use `account/rateLimits/read` with an empty params object. Notifications use `account/rateLimits/updated` with params.rateLimits. This version supports notifications without a separate subscription RPC: leaving the method out of initialize's opt-out list receives events when the server emits them. There is no invented subscribe request. Older versions without events still poll. An idle separate app-server may emit no events caused by work in another Codex process; polling is necessary and no fixed backend publication interval is assumed.

The generated notification schema explicitly describes sparse updates. Non-null available windows merge into state. Duplicate events are ignored; older reset epochs and lower consumed values within the same epoch are rejected. Full polls are authoritative and can correct usage downward. If an event changes state while a poll is pending, that poll response is discarded to avoid overwriting the event. The protocol has no event timestamp/sequence number: perfect ordering of equal-epoch corrections cannot be inferred. Polling reconciles this limitation. Unrecognized model-specific buckets are ignored. Invalid data is visibly marked, raw payloads/errors are never logged.

## Security and boundaries

The application never opens auth.json, cookies, credential stores, or token files. Authentication, renewal and all service networking are delegated to the official CLI. There is no app telemetry, updater, HTTP client, third-party service, downloaded script execution, or shell=True. The only spawned process is the resolved official CLI with fixed argument arrays: `-c analytics.enabled=false -c feedback.enabled=false -c otel.exporter="none" app-server --listen stdio://`. stderr is discarded to avoid persisting sensitive diagnostics. The app requests no threads, turns, tool executions, account reads or login methods. Unexpected server requests close the connection rather than authorize actions. Received account metadata is not displayed, logged or persisted.

CLI installation and Python package installation naturally contact their official registries when you choose to install dependencies. Runtime CLI network endpoints and credential handling are controlled by the official CLI and your existing CLI configuration. The overlay explicitly disables CLI analytics, feedback and OTel exporting but cannot audit a replaced executable or override arbitrary enterprise CLI configuration. Use a trusted CLI installation and ordinary-user filesystem permissions. No administrator privileges or global startup changes are used. A Qt lock file prevents duplicate overlay instances per Windows user.

Verification: mocked automated tests cover parsing, conversion, malformed fields, resets, duplicates, delayed events, sparse merges, authoritative correction, CLI unavailable, launch failure/disconnection, scheduling/non-overlap, reconnect, stop, notification delivery and preferences. A live read confirmed both 300- and 10080-minute windows. GUI smoke checks and packaging results are recorded in VERIFICATION.md. Physical mouse pass-through across other applications, all monitor/scaling combinations and a Python-free target installation require manual acceptance on the intended machine.
