# Verification — 2026-10-26

Environment: Windows 11, Python 3.12.10, PySide6 6.8.3, PyInstaller 6.12.0.

## Automated checks

51 credential-free unittest tests passed. Coverage includes consumed/remaining conversion, Codex epoch and Claude ISO reset times, decimal usage, null/malformed windows, sparse/duplicate/delayed Codex updates, scheduling and overlap prevention, missing executables, native CLI discovery, real mocked subprocess framing and reaping, reconnect, inactive Claude startup suppression, safe command/telemetry flags, configuration persistence, tray/settings mode switching, and independent provider errors.

Desktop presence tests cover all row combinations, own-child/descendant exclusion, detection-error recovery and distinguishing the Codex Store application from ChatGPT. Lock/unlock preserves widget size, position and text in compact/full modes with background enabled and disabled.

## Live checks

- Official Codex CLI 0.163.0-alpha.10.2: stdio initialization and rate-limit reads succeeded for both supported durations. Generated schemas are under schema/.
- Native Codex discovery succeeded with PATH restricted to Windows System32.
- Official Claude native CLI 2.1.310: package SHA-512 matched official npm registry metadata before extraction into the ignored virtual environment. Authentication was performed by the user through official CLI login.
- Claude initialization and get_usage with skip_behaviors=true returned actual five-hour/seven-day usage with ISO timestamps. The safe projection confirmed no history analysis and zero session model cost. No prompt was sent.
- On this CLI, CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 produced null usage despite valid login. Removing only that umbrella flag restored usage; explicit telemetry, OTel enablement, updates and error-reporting opt-outs remain set by the runtime client.
- GUI smoke received real Codex and Claude usage in the same window. Compact screenshot visually inspected. Child workers stopped and were reaped after the smoke check.
- Earlier packaged startup and duplicate-instance checks passed. Current distribution rebuilt after Claude integration.

No credentials, account identities or live usage payloads are persisted in project files. The CLI executable path is stored only in local preferences. Claude integration uses an explicitly experimental official SDK control interface and may require changes after CLI updates.

Remaining manual acceptance: physical mouse pass-through over other applications, all monitor/DPI combinations, Windows sign-in startup, long-running resource use, a Python-free target machine, and graceful recovery during real network outages or service-side authentication expiration. Desktop detection treats minimized windows as open and last-window closure to tray as inactive; browser/terminal-only sessions and the selected Claude Desktop tab are outside its scope.

## Packaged connection diagnostics

Isolated frozen Claude check succeeded with no errors, including with PATH restricted to Windows System32. Full packaged GUI check confirmed both desktop windows active and both providers populated, with empty Claude/activity errors. Startup is now distinct from failure in the compact row, and the tray exposes safe connection status.

## Claude runtime discovery

Verified packaged full-GUI startup with an empty Claude executable preference and PATH restricted to Windows System32. The optional native CLI in the application-managed tools directory was found automatically; both providers received real data with no Claude/activity errors. The native dependency is outside the repository and is not auto-downloaded or auto-updated.

## MSIX AppData redirection fix

The earlier source/frozen checks inherited Codex MSIX filesystem virtualization and therefore did not reproduce normal Explorer launches. Resolved file handles confirmed AppData had been redirected into the package LocalCache. The external native Claude CLI now also supports physical project-local tools/claude.exe and side-by-side deployment, with normalization of pasted quotes and fallback from stale preferences. The full packaged GUI was launched via a Windows Explorer shortcut outside the Codex process environment: both providers received real data and Claude/activity errors were empty. No personal paths or account data are included in the report.
