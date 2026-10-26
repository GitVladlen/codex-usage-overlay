import sys
from PySide6.QtCore import QLockFile,QStandardPaths
from PySide6.QtWidgets import QApplication,QSystemTrayIcon,QMessageBox
from pathlib import Path
from src.config import load,save
from src.overlay import Overlay
from src.refresh_worker import RefreshWorker
from src.tray import Tray
from src.startup import set_startup

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
    def commit(new):
        set_startup(new.start_with_windows); save(new)
        overlay.config=new; worker.interval=new.refresh_interval; tray.config=new
        tray.click.blockSignals(True); tray.click.setChecked(new.click_through); tray.click.blockSignals(False)
        tray.start.blockSignals(True); tray.start.setChecked(new.start_with_windows); tray.start.blockSignals(False)
        visible=overlay.isVisible(); overlay.apply(); overlay.place(); overlay.setVisible(visible)
    tray=Tray(overlay,worker,config,commit)
    worker.updated.connect(overlay.update_usage); worker.failed.connect(overlay.fail)
    def cleanup():
        tray.hide(); worker.stop(); worker.wait(10000)
    app.aboutToQuit.connect(cleanup)
    overlay.show(); worker.start()
    return app.exec()
if __name__=='__main__': sys.exit(main())
