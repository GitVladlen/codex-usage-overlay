from PySide6.QtWidgets import QSystemTrayIcon,QMenu,QApplication,QMessageBox
from PySide6.QtGui import QIcon,QPixmap,QPainter,QColor,QFont
from .settings import SettingsDialog
from .startup import set_startup

class Tray(QSystemTrayIcon):
    def __init__(self,overlay,worker,config,commit):
        pix=QPixmap(32,32); pix.fill(QColor('#333333')); painter=QPainter(pix); painter.setPen(QColor('white')); painter.setFont(QFont('Segoe UI',20)); painter.drawText(pix.rect(),0x84,'C'); painter.end()
        super().__init__(QIcon(pix),overlay)
        self.overlay,self.worker,self.config,self.commit=overlay,worker,config,commit; self.dialog=None
        self.setToolTip('Codex Usage Overlay'); menu=QMenu()
        menu.addAction('Show / Hide Overlay',lambda:overlay.setVisible(not overlay.isVisible()))
        menu.addAction('Refresh Now',worker.refresh)
        self.lock=menu.addAction('Unlock Position'); self.lock.setCheckable(True); self.lock.toggled.connect(self.unlock)
        self.click=menu.addAction('Enable Click-through'); self.click.setCheckable(True); self.click.setChecked(config.click_through); self.click.toggled.connect(self.clickthrough)
        self.compact=menu.addAction('Compact View'); self.compact.setCheckable(True); self.compact.setChecked(config.compact_mode); self.compact.toggled.connect(self.compact_view)
        menu.addAction('Overlay Settings',self.settings)
        self.start=menu.addAction('Start with Windows'); self.start.setCheckable(True); self.start.setChecked(config.start_with_windows); self.start.toggled.connect(self.startup)
        menu.addSeparator(); menu.addAction('Exit',QApplication.instance().quit)
        self.menu=menu; self.setContextMenu(menu); self.show()
    def unlock(self,value):
        visible=self.overlay.isVisible(); self.overlay.unlocked=value; self.overlay.apply(); self.overlay.setVisible(visible)
    def clickthrough(self,value):
        self.config.click_through=value; self.commit(self.config)
    def compact_view(self,value):
        self.config.compact_mode=value; self.commit(self.config)
        if self.dialog and self.dialog.isVisible():
            self.dialog.fields['compact_mode'].setChecked(value)
    def startup(self,value):
        try: set_startup(value); self.config.start_with_windows=value; self.commit(self.config)
        except OSError:
            self.start.blockSignals(True); self.start.setChecked(not value); self.start.blockSignals(False)
            QMessageBox.warning(None,'Startup','Could not change Windows startup entry.')
    def settings(self):
        if self.dialog and self.dialog.isVisible(): self.dialog.raise_(); return
        self.dialog=SettingsDialog(self.config,self.commit); self.dialog.show()
