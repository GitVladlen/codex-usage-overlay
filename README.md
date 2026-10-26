# Codex Usage Overlay for Windows

A transparent, always-on-top PySide6 tray application with Codex and experimental Claude subscription limits. The official Codex and Claude CLIs remain external dependencies; the packaged application includes Python and Qt.

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

Look for the C icon in the Windows tray (possibly under hidden icons). Right-click for Show/Hide, Refresh Now, Connection Status, Unlock Position, Click-through, Settings, Start with Windows, and Exit. Unlock temporarily disables click-through so the overlay can be dragged; a thin blue border, subtle blue background and move cursor indicate this mode. The border space is always reserved, so locking/unlocking changes neither text nor overlay size. Relock from the tray. Settings include monitor, font, color, opacity, refresh interval, background, optional text progress bars, reset times, weekly usage and startup. Closing settings keeps the application running. Exit stops and reaps the app-owned Codex child; it never terminates other Codex processes.

Default refresh is 30 seconds; configurable 5–3600 seconds. Reset countdowns repaint locally every second and do not make requests. Last successful reception uses local time. Errors retain in-memory values with STALE indication; no usage values are persisted. A passed reset shows zero countdown until a server snapshot arrives; the application never fabricates a reset to 100% remaining.

Settings live in `%LOCALAPPDATA%\CodexUsageOverlay\settings.json` and contain preferences only. Invalid values fall back to validated defaults. Startup uses the current user's `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` entry named CodexUsageOverlay, with properly quoted executable arguments. Disable it in the tray before moving/removing the installation. Source-mode startup points to pythonw.exe in this venv; packaged startup points to the EXE. Position uses Qt logical pixels and monitor names, supports negative screen coordinates, and clamps to the selected screen after display changes. Qt handles display scaling. The tool window is frameless, translucent, non-activating and absent from Alt+Tab; Qt's Windows transparent-input flag provides click-through.

## Desktop activity and Claude

The overlay checks desktop window presence every three seconds using Win32 EnumWindows and process metadata. Only executable names/paths and parent process IDs are queried; window titles/content, command lines, session files and credentials are not read. Minimized desktop windows count as active. Closing the last window to the tray counts as inactive, even if background processes remain. Terminal-only sessions and browser tabs are outside this desktop detector. Codex's Store build may use ChatGPT.exe; the executable installation path distinguishes it from the separate ChatGPT app. The overlay and all its descendants are explicitly excluded, so its own app-server never keeps the Codex row visible. Detection is limited to windows accessible in the current Windows desktop/session; errors show an explicit status warning rather than pretending both apps are closed.

- Codex window only: CDX row with live usage.
- Claude window only: CLD row.
- Both windows: both rows (also in full view).
- Neither: `Неактивно`.

**Claude usage integration (experimental):** Claude Desktop's Code tab does not execute the terminal `statusLine` command. Instead, the overlay keeps a separate official native Claude Code CLI process on stream-json and sends only `initialize` and `get_usage` control requests. The latter corresponds to the official SDK method `usage_EXPERIMENTAL_MAY_CHANGE_DO_NOT_RELY_ON_THIS_API_YET()` and includes `skip_behaviors: true` to skip local transcript analysis. No user prompts, model turns, slash commands, tool executions or private HTTP calls are sent by the overlay. The tested CLI is **2.1.310**; this API may change without notice. The official SDK changelog records its introduction: https://github.com/anthropics/claude-agent-sdk-typescript/blob/main/CHANGELOG.md#03169.

Install the official native Claude Code CLI following https://code.claude.com/docs/en/setup and run `claude auth login` yourself, selecting the same account as Claude Desktop. Desktop and the separate CLI may have separate sign-ins. The overlay never reads or compares identities or credentials. Set **Claude CLI executable** in Overlay Settings to the absolute path of the official native `claude.exe` when automatic discovery (PATH, `~/.local/bin/claude.exe`, or the optional app-managed `%LOCALAPPDATA%/CodexUsageOverlay/tools/claude.exe`) fails. This is a non-sensitive executable preference, stored only in local settings. Shell `.cmd`/`.bat` launchers are not used. The native CLI is an external dependency, not part of the PyInstaller distribution.

Claude polls every 30 seconds (or the configured refresh interval), with one pending request at a time, a 30-second timeout, and exponential reconnect. It starts when Claude Desktop is first opened; later closing Desktop pauses polling and hides the row while retaining the initialized child until exit. Reopening requests an immediate update. Refresh Now refreshes both providers. Successful values are cached in memory only; errors retain them with a stale indicator. Null usage data never becomes 100% remaining. In the `get_usage` response, `utilization` is percentage consumed, **0–100**, not a fraction; `resets_at` is an ISO 8601 timestamp with timezone. Remaining values are clamped and displayed as whole percentages.

The child uses `--safe-mode --restricted --print --input-format stream-json --output-format stream-json --verbose --no-session-persistence --permission-mode dontAsk --tools "" --strict-mcp-config --mcp-config '{"mcpServers":{}}' --no-chrome --setting-sources ""`. User customizations, hooks and MCP configurations are disabled; no conversation is resumed or persisted. Telemetry, auto-updates and error reporting are disabled through `DISABLE_TELEMETRY=1`, `CLAUDE_CODE_ENABLE_TELEMETRY=0`, `DISABLE_AUTOUPDATER=1` and `DISABLE_ERROR_REPORTING=1`. The child does **not** set the umbrella `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, because on the tested CLI it suppresses the usage fetch and returns null limits even after login. CLI service networking/authentication remains delegated to Anthropic's executable. Existing enterprise-managed policies remain outside the overlay's control.

For a sanitized diagnostic, run `.\.venv\Scripts\python.exe scripts\probe_claude_usage.py --cli C:\path\to\claude.exe`. It prints only availability, usage percentages/reset timestamps, the history-skip flag and session cost. Authentication errors or unavailable plan windows are displayed honestly; CLI/API-key accounts that do not expose subscription limits are unsupported for those rows.

Codex polling continues in its persistent connection while its desktop window is closed, but its row is hidden. Reopening Codex requests a refresh immediately; cached values are temporarily marked stale until confirmed. The full usage client remains independent of the Codex GUI; desktop presence controls presentation only.

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
- refresh_worker.py: Codex background QThread, initialize/initialized handshake, immediate read, non-overlapping fallback polls, immediate notification handling, bounded exponential reconnect (1–30 seconds), cancellable shutdown.
- usage_model.py: validates fields consumed by the app, selects rateLimitsByLimitId.codex when available, falls back to rateLimits, identifies windows by duration (300 and 10080 minutes), and converts consumed usedPercent to clamped remaining percentage. Null/missing windows remain unavailable rather than becoming zero usage.
- claude_client.py and claude_worker.py: restricted Claude stream-json controls, validation, activity-gated polling and reconnect.
- activity.py: Win32 desktop-window presence, excluding overlay-owned processes.
- overlay.py: rendering for both providers, one-second countdown, drag, display positioning.
- config.py, settings.py, startup.py and tray.py: preference validation, atomic JSON persistence, dialogs and tray controls.

Reads use `account/rateLimits/read` with an empty params object. Notifications use `account/rateLimits/updated` with params.rateLimits. This version supports notifications without a separate subscription RPC: leaving the method out of initialize's opt-out list receives events when the server emits them. There is no invented subscribe request. Older versions without events still poll. An idle separate app-server may emit no events caused by work in another Codex process; polling is necessary and no fixed backend publication interval is assumed.

The generated notification schema explicitly describes sparse updates. Non-null available windows merge into state. Duplicate events are ignored; older reset epochs and lower consumed values within the same epoch are rejected. Full polls are authoritative and can correct usage downward. If an event changes state while a poll is pending, that poll response is discarded to avoid overwriting the event. The protocol has no event timestamp/sequence number: perfect ordering of equal-epoch corrections cannot be inferred. Polling reconciles this limitation. Unrecognized model-specific buckets are ignored. Invalid data is visibly marked, raw payloads/errors are never logged.

## Security and boundaries

The application never opens auth.json, cookies, credential stores, or token files. Authentication, renewal and all service networking are delegated to the official CLI. There is no app telemetry, updater, HTTP client, third-party service, downloaded script execution, or shell=True. For Codex, the spawned process is the resolved official CLI with fixed argument arrays: `-c analytics.enabled=false -c feedback.enabled=false -c otel.exporter="none" app-server --listen stdio://`. stderr is discarded to avoid persisting sensitive diagnostics. The app requests no threads, turns, tool executions, account reads or login methods. Unexpected server requests close the connection rather than authorize actions. Received account metadata is not displayed, logged or persisted.

CLI installation and Python package installation naturally contact their official registries when you choose to install dependencies. Runtime CLI network endpoints and credential handling are controlled by the official CLI and your existing CLI configuration. The overlay explicitly disables Codex CLI analytics, feedback and OTel exporting and Claude CLI telemetry, automatic updates and error reporting but cannot audit a replaced executable or override arbitrary enterprise CLI configuration. Use a trusted CLI installation and ordinary-user filesystem permissions. No administrator privileges or global startup changes are used. A Qt lock file prevents duplicate overlay instances per Windows user.

Verification: mocked automated tests cover parsing, conversion, malformed fields, resets, duplicates, delayed events, sparse merges, authoritative correction, CLI unavailable, launch failure/disconnection, scheduling/non-overlap, reconnect, stop, notification delivery and preferences. A live read confirmed both 300- and 10080-minute windows. GUI smoke checks and packaging results are recorded in VERIFICATION.md. Physical mouse pass-through across other applications, all monitor/scaling combinations and a Python-free target installation require manual acceptance on the intended machine.


## Connection diagnostics

During startup the compact row says `підключення…` until data arrives; a failed request instead says data is unavailable. Use **Connection Status** in the tray to see the safe provider-specific error without changing to full view.

The built EXE supports opt-in diagnostics: `--self-test-claude REPORT.json` tests the official Claude bridge and `--self-test-overlay REPORT.json` starts the full overlay for eight seconds, checks provider/activity state, then exits. Reports contain only success booleans and application-generated error messages, never percentages, account identifiers or raw CLI payloads. Use a report path outside the tracked source, such as the ignored build directory. Normal startup creates no diagnostic reports.

The app-managed Claude runtime is a native official executable installed separately; the overlay does not download or update it automatically. This location is independent of project/build directories and does not require a saved CLI path.


For project-local deployment, place the official native CLI at `tools/claude.exe` in the project root (ignored by Git), or `tools/claude.exe` next to the overlay EXE. Discovery checks these locations automatically, including the standard `dist/CodexUsageOverlay` layout. These physical locations avoid Windows MSIX AppData virtualization when development commands run inside a packaged application. A quoted path pasted into Settings is normalized; a stale preference falls back to known local/installed CLI locations.
