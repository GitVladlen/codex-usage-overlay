import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer,Qt
from src.config import Config,load
from src.overlay import Overlay
from src.refresh_worker import RefreshWorker
from src.tray import Tray
from src.activity import desktop_presence
from src.claude_worker import ClaudeWorker
app=QApplication([]); app.setQuitOnLastWindowClosed(False)
c=Config(); o=Overlay(c,lambda:None); w=RefreshWorker(); tray=Tray(o,w,c,lambda c:None)
cw=ClaudeWorker(executable=load().claude_cli_path); claude_received=[]
received=[]
def updated(windows,stamp):
 received.append(windows); o.update_usage(windows,stamp)
w.updated.connect(updated); w.failed.connect(o.fail)
def claude_updated(windows,stamp):
 claude_received.append(windows); o.update_claude_usage(windows,stamp)
cw.updated.connect(claude_updated); cw.failed.connect(o.fail_claude)
o.set_activity(*desktop_presence()); o.show(); w.start()
# Explicitly exercise the Claude bridge even when its Desktop is currently closed.
cw.set_active(True); cw.start()
def check():
 assert o.windowFlags() & Qt.WindowTransparentForInput
 tray.unlock(True); assert not o.windowFlags() & Qt.WindowTransparentForInput
 tray.unlock(False)
 tray.settings(); tray.dialog.close()
 assert o.isVisible()
 o.grab().save('smoke-overlay.png')
 w.stop(); cw.stop(); assert w.wait(10000); assert cw.wait(10000); tray.hide()
 print('GUI smoke passed; real Codex usage:',bool(received),'real Claude usage:',bool(claude_received)); app.quit()
QTimer.singleShot(8000,check)
app.exec()
