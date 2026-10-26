import sys
from PySide6.QtCore import QLockFile,QStandardPaths,QTimer
from PySide6.QtWidgets import QApplication,QSystemTrayIcon,QMessageBox
from pathlib import Path
from src.config import load,save
from src.overlay import Overlay
from src.refresh_worker import RefreshWorker
from src.tray import Tray
from src.startup import set_startup
from src.activity import ActivityMonitor
from src.claude_worker import ClaudeWorker

def main():
    app=QApplication(sys.argv); app.setApplicationName('CodexUsageOverlay'); app.setQuitOnLastWindowClosed(False)
    lockdir=Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)); lockdir.mkdir(parents=True,exist_ok=True)
    lock=QLockFile(str(lockdir/'overlay.lock')); lock.setStaleLockTime(0)
    if not lock.tryLock(100): return 0
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None,'Codex Overlay','Windows system tray unavailable.'); return 1
    config=load()
    def persist():
        try: save(overlay.config)
        except OSError: overlay.fail('Unable to save position')
    overlay=Overlay(config,persist); worker=RefreshWorker(config.refresh_interval)
    claude_worker=ClaudeWorker(config.refresh_interval,config.claude_cli_path)
    def commit(new):
        set_startup(new.start_with_windows); save(new)
        overlay.config=new; worker.interval=new.refresh_interval; tray.config=new
        claude_worker.interval=new.refresh_interval; claude_worker.set_executable(new.claude_cli_path)
        tray.compact.blockSignals(True); tray.compact.setChecked(new.compact_mode); tray.compact.blockSignals(False)
        tray.click.blockSignals(True); tray.click.setChecked(new.click_through); tray.click.blockSignals(False)
        tray.start.blockSignals(True); tray.start.setChecked(new.start_with_windows); tray.start.blockSignals(False)
        visible=overlay.isVisible(); overlay.apply(); overlay.place(); overlay.setVisible(visible)
    class RefreshBoth:
        def refresh(self): worker.refresh(); claude_worker.refresh()
    tray=Tray(overlay,RefreshBoth(),config,commit)
    activity=ActivityMonitor(app)
    def activity_changed(codex,claude):
        overlay.set_activity(codex,claude)
        if codex: worker.refresh()
        claude_worker.set_active(claude)
    activity.changed.connect(activity_changed)
    activity.failed.connect(overlay.fail_activity)
    activity.start()
    worker.updated.connect(overlay.update_usage); worker.failed.connect(overlay.fail)
    claude_worker.updated.connect(overlay.update_claude_usage); claude_worker.failed.connect(overlay.fail_claude)
    def cleanup():
        activity.timer.stop(); tray.hide(); worker.stop(); claude_worker.stop()
        worker.wait(10000); claude_worker.wait(10000)
    app.aboutToQuit.connect(cleanup)
    if len(sys.argv)==3 and sys.argv[1]=='--self-test-overlay':
        def finish_check():
            import json
            report={'codex_active':overlay.codex_active,'claude_active':overlay.claude_active,
                'codex_has_data':bool(overlay.windows),'claude_has_data':bool(overlay.claude_windows),
                'claude_error':overlay.claude_error,'activity_error':overlay.activity_error}
            Path(sys.argv[2]).write_text(json.dumps(report,indent=2),encoding='utf-8')
            app.quit()
        QTimer.singleShot(8000,finish_check)
    overlay.show(); worker.start(); claude_worker.start()
    return app.exec()
if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--self-test-claude':
        from src.diagnostics import check_claude
        sys.exit(check_claude(sys.argv[2]))
    sys.exit(main())
