import time
from datetime import datetime
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication

class Overlay(QWidget):
    def __init__(self, config, persist):
        super().__init__()
        self.config,self.persist=config,persist
        self.codex_active=False; self.claude_active=False; self.activity_error=False
        self.claude_windows={}; self.claude_last=0; self.claude_error='Connecting to Claude…'
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
        bg='rgba(35,90,130,70)' if self.unlocked else ('rgba(20,20,20,160)' if c.background else 'transparent')
        border='#65bfff' if self.unlocked else 'transparent'
        self.setCursor(Qt.SizeAllCursor if self.unlocked else Qt.ArrowCursor)
        self.label.setStyleSheet(f'color:{c.font_color}; font-family:Segoe UI; font-size:{c.font_size}pt; background:{bg}; border:1px solid {border}; border-radius:5px; padding:3px;')
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
    def set_activity(self, codex, claude):
        reopened = codex and not self.codex_active
        claude_reopened = claude and not self.claude_active
        self.codex_active,self.claude_active=codex,claude
        self.activity_error=False
        if reopened and self.last:
            self.error='Refreshing usage…'
        if claude_reopened and self.claude_last:
            self.claude_error='Refreshing usage…'
        self.render()
    def fail_activity(self):
        self.activity_error=True; self.render()
    def update_usage(self, windows, stamp):
        self.windows,self.last,self.error=windows,stamp,''; self.render()
    def fail(self,error): self.error=error; self.render()
    def update_claude_usage(self, windows, stamp):
        self.claude_windows,self.claude_last,self.claude_error=windows,stamp,''; self.render()
    def fail_claude(self,error): self.claude_error=error; self.render()
    def provider_text(self, windows, last, error, title, abbreviation):
        now=time.time(); lines=[title]
        for minutes,label in [(300,'5h'),(10080,'Week')]:
            if minutes==10080 and not self.config.show_weekly: continue
            window=windows.get(minutes)
            percent=f'{window.remaining:.0f}' if window else '—'
            line=f'{label:<5} {percent}% left'
            if window and self.config.progress_bars:
                line+='  '+('▰'*round(window.remaining/10)).ljust(10,'▱')
            if self.config.show_reset_times:
                if window and window.resets is not None:
                    seconds=max(0,int(window.resets-now)); hours,seconds=divmod(seconds,3600); mins,seconds=divmod(seconds,60)
                    line+=f'  ·  Reset {datetime.fromtimestamp(window.resets):%a %H:%M} ({hours:02}:{mins:02}:{seconds:02})'
                else: line+='  ·  Reset unknown'
            lines.append(line)
        stale=bool(error) or bool(last and now-last>max(65,self.config.refresh_interval*2+5))
        lines.append(('STALE · ' if stale and last else '')+('Updated '+datetime.fromtimestamp(last).strftime('%H:%M:%S') if last else 'No usage data'))
        if error: lines.append('⚠ '+error)
        full_text='\n'.join(lines)
        if not self.config.compact_mode: return full_text,full_text
        if not windows:
            if error.startswith('Connecting to '):
                text=abbreviation+' · підключення…'
            else:
                text=abbreviation+(' · дані недоступні' if abbreviation=='CLD' else ' · недоступно')
        else:
            parts=[abbreviation]
            for minutes,label in [(300,'5h'),(10080,'W')]:
                if minutes==10080 and not self.config.show_weekly: continue
                window=windows.get(minutes)
                parts.append(f'{label} {window.remaining:.0f}%' if window else f'{label} —%')
            if stale: parts.append('⚠')
            text=' · '.join(parts)
        return text,full_text
    def render(self):
        rows=[]; details=[]
        providers=[(self.codex_active,self.windows,self.last,self.error,'CODEX','CDX'),
            (self.claude_active,self.claude_windows,self.claude_last,self.claude_error,'CLAUDE','CLD')]
        for active,windows,last,error,title,abbreviation in providers:
            if active:
                text,detail=self.provider_text(windows,last,error,title,abbreviation)
                rows.append(text); details.append(detail)
        if self.activity_error: rows.append('⚠ Стан застосунків недоступний')
        if not rows: rows.append('Неактивно')
        self.label.setToolTip('\n\n'.join(details))
        self.label.setText('\n'.join(rows)); self.adjustSize()
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
