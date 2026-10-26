"""Opt-in sanitized packaged-runtime check. Never writes usage or account data."""
import json
from pathlib import Path
import sys
from PySide6.QtCore import QCoreApplication,QTimer
from .config import load
from .claude_worker import ClaudeWorker


def check_claude(report_path):
    app=QCoreApplication([])
    config=load()
    report={'frozen':bool(getattr(sys,'frozen',False)),
        'configured_cli_exists':Path(config.claude_cli_path).is_file(),
        'success':False,'errors':[]}
    worker=ClaudeWorker(executable=config.claude_cli_path)
    worker.set_active(True)
    def updated(windows,stamp):
        report['success']=bool(windows)
        app.quit()
    def failed(message):
        if len(report['errors'])<5: report['errors'].append(message)
    worker.updated.connect(updated);worker.failed.connect(failed)
    worker.start()
    QTimer.singleShot(12000,app.quit)
    app.exec()
    worker.stop();worker.wait(10000)
    Path(report_path).write_text(json.dumps(report,indent=2),encoding='utf-8')
    return 0 if report['success'] else 1
