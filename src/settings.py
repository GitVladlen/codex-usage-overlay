from PySide6.QtWidgets import QDialog,QFormLayout,QSpinBox,QCheckBox,QLineEdit,QComboBox,QDialogButtonBox,QApplication,QMessageBox
from .config import validate
from dataclasses import asdict

class SettingsDialog(QDialog):
    def __init__(self,config,apply,parent=None):
        super().__init__(parent); self.setWindowTitle('Overlay Settings'); self.config=config; self.callback=apply
        form=QFormLayout(self); self.fields={}
        for key,label,lo,hi in [('refresh_interval','Refresh interval (seconds)',5,3600),('font_size','Font size',8,36),('opacity','Opacity (%)',10,100)]:
            widget=QSpinBox(); widget.setRange(lo,hi); widget.setValue(getattr(config,key)); form.addRow(label,widget); self.fields[key]=widget
        color=QLineEdit(config.font_color); form.addRow('Font color (#RRGGBB)',color); self.fields['font_color']=color
        monitor=QComboBox()
        for screen in QApplication.screens(): monitor.addItem(screen.name())
        monitor.setCurrentText(config.monitor or QApplication.primaryScreen().name()); self.fields['monitor']=monitor; form.addRow('Monitor',monitor)
        for key,label in [('click_through','Click-through'),('background','Background panel'),('show_reset_times','Show reset times'),('show_weekly','Show weekly usage'),('progress_bars','Progress bars'),('start_with_windows','Start with Windows')]:
            widget=QCheckBox(); widget.setChecked(getattr(config,key)); self.fields[key]=widget; form.addRow(label,widget)
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); buttons.accepted.connect(self.commit); buttons.rejected.connect(self.reject); form.addRow(buttons)
    def commit(self):
        data=asdict(self.config)
        for key,w in self.fields.items():
            data[key]=w.isChecked() if isinstance(w,QCheckBox) else w.value() if isinstance(w,QSpinBox) else w.currentText() if isinstance(w,QComboBox) else w.text()
        if data['monitor']!=self.config.monitor: data['x']=data['y']=None
        try: self.callback(validate(data))
        except OSError: QMessageBox.warning(self,'Settings','Could not save settings or Windows startup entry.'); return
        self.accept()
