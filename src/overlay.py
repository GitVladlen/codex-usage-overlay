import time
from datetime import datetime
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication

class Overlay(QWidget):
    def __init__(self, config, persist):
        super().__init__()
        self.config,self.persist=config,persist
        self.windows={}; self.last=0; self.error='Connecting to Codex…'; self.unlocked=False; self.drag=None
        self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.Tool|Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.label=QLabel(); self.label.setTextFormat(Qt.PlainText)
        layout=QVBoxLayout(self); layout.setContentsMargins(8,5,8,5); layout.addWidget(self.label)
        self.timer=QTimer(self); self.timer.timeout.connect(self.render); self.timer.start(1000)
        self.apply(); self.place()
        QApplication.instance().screenAdded.connect(lambda _:self.place())
        QApplication.instance().screenRemoved.connect(lambda _:self.place())
        for screen in QApplication.screens(): screen.availableGeometryChanged.connect(lambda _:self.place())
    def apply(self):
        c=self.config
        self.setWindowOpacity(c.opacity/100)
        bg='rgba(20,20,20,160)' if c.background else 'transparent'
        self.label.setStyleSheet(f'color:{c.font_color}; font-family:Segoe UI; font-size:{c.font_size}pt; background:{bg}; border-radius:5px; padding:3px;')
        self.setWindowFlag(Qt.WindowTransparentForInput,c.click_through and not self.unlocked)
        self.render()
        if self.isVisible(): self.show()
    def place(self):
        screens=QApplication.screens()
        screen=next((s for s in screens if s.name()==self.config.monitor),QApplication.primaryScreen())
        area=screen.availableGeometry()
        x=self.config.x if self.config.x is not None else area.right()-self.width()-16
        y=self.config.y if self.config.y is not None else area.top()+16
        self.move(max(area.left(),min(x,area.right()-self.width())),max(area.top(),min(y,area.bottom()-self.height())))
    def update_usage(self, windows, stamp):
        self.windows,self.last,self.error=windows,stamp,''; self.render()
    def fail(self,error): self.error=error; self.render()
    def render(self):
        now=time.time(); lines=['CODEX'+('  ·  MOVE' if self.unlocked else '')]
        for minutes,title in [(300,'5h'),(10080,'Week')]:
            if minutes==10080 and not self.config.show_weekly: continue
            w=self.windows.get(minutes)
            line=f'{title:<5} {w.remaining if w else "—"}% left'
            if w and self.config.progress_bars: line+='  '+('▰'*round(w.remaining/10)).ljust(10,'▱')
            if self.config.show_reset_times:
                if w and w.resets is not None:
                    secs=max(0,int(w.resets-now)); hours,secs=divmod(secs,3600); mins,secs=divmod(secs,60)
                    line+=f'  ·  Reset {datetime.fromtimestamp(w.resets):%a %H:%M} ({hours:02}:{mins:02}:{secs:02})'
                else: line+='  ·  Reset unknown'
            lines.append(line)
        stale=bool(self.error) or bool(self.last and now-self.last>max(65,self.config.refresh_interval*2+5))
        lines.append(('STALE · ' if stale and self.last else '') + ('Updated '+datetime.fromtimestamp(self.last).strftime('%H:%M:%S') if self.last else 'No usage data'))
        if self.error: lines.append('⚠ '+self.error)
        self.label.setText('\n'.join(lines)); self.adjustSize()
    def mousePressEvent(self,event):
        if self.unlocked and event.button()==Qt.LeftButton: self.drag=event.globalPosition().toPoint()-self.pos()
    def mouseMoveEvent(self,event):
        if self.drag is not None: self.move(event.globalPosition().toPoint()-self.drag)
    def mouseReleaseEvent(self,event):
        if self.drag is not None:
            self.drag=None; self.config.x,self.config.y=self.x(),self.y()
            if self.screen(): self.config.monitor=self.screen().name()
            self.persist()
    def closeEvent(self,event): event.ignore(); self.hide()
