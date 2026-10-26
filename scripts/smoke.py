import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer,Qt
from src.config import Config
from src.overlay import Overlay
from src.refresh_worker import RefreshWorker
from src.tray import Tray
app=QApplication([]); app.setQuitOnLastWindowClosed(False)
c=Config(); o=Overlay(c,lambda:None); w=RefreshWorker(); tray=Tray(o,w,c,lambda c:None)
received=[]
def updated(windows,stamp):
 received.append(windows); o.update_usage(windows,stamp)
w.updated.connect(updated); w.failed.connect(o.fail)
o.show(); w.start()
def check():
 assert o.windowFlags() & Qt.WindowTransparentForInput
 tray.unlock(True); assert not o.windowFlags() & Qt.WindowTransparentForInput
 tray.unlock(False)
 tray.settings(); tray.dialog.close()
 assert o.isVisible()
 o.grab().save('smoke-overlay.png')
 w.stop(); assert w.wait(10000); tray.hide()
 print('GUI smoke passed; real usage received:',bool(received)); app.quit()
QTimer.singleShot(8000,check)
app.exec()
