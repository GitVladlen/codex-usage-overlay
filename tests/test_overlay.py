import time
import unittest
from PySide6.QtWidgets import QApplication
from src.config import Config, validate
from src.overlay import Overlay
from src.usage_model import Window
from src.tray import Tray
from src.settings import SettingsDialog

class CompactViewTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
 def setUp(self): self.overlay=Overlay(Config(),lambda:None)
 def tearDown(self): self.overlay.timer.stop(); self.overlay.hide(); self.overlay.deleteLater()
 def test_default_and_legacy_settings(self):
  self.assertTrue(Config().compact_mode)
  self.assertTrue(validate({'font_size':12}).compact_mode)
  self.assertFalse(validate({'compact_mode':False}).compact_mode)
 def test_compact_and_stale(self):
  self.overlay.update_usage({300:Window(17,300,None),10080:Window(3,10080,None)},time.time())
  self.assertEqual(self.overlay.label.text(),'CDX · 5h 83% · W 97%')
  self.overlay.fail('offline')
  self.assertEqual(self.overlay.label.text(),'CDX · 5h 83% · W 97% · ⚠')
 def test_unavailable_and_weekly_hidden(self):
  self.assertEqual(self.overlay.label.text(),'CDX · недоступно')
  self.overlay.config.show_weekly=False
  self.overlay.update_usage({300:Window(17,300,None)},time.time())
  self.assertEqual(self.overlay.label.text(),'CDX · 5h 83%')
 def test_tray_toggle_and_settings(self):
  class Worker:
   def refresh(self): pass
  def commit(config): self.overlay.config=config; self.overlay.apply()
  tray=Tray(self.overlay,Worker(),self.overlay.config,commit)
  try:
   tray.compact.setChecked(False)
   self.assertFalse(self.overlay.config.compact_mode)
   self.assertIn('CODEX',self.overlay.label.text())
   self.assertIn('No usage data',self.overlay.label.text())
   tray.compact.setChecked(True)
   self.assertEqual(self.overlay.label.text(),'CDX · недоступно')
   dialog=SettingsDialog(self.overlay.config,commit)
   dialog.fields['compact_mode'].setChecked(False); dialog.commit()
   self.assertFalse(self.overlay.config.compact_mode)
  finally: tray.hide()
