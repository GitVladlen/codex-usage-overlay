import unittest
from src.activity import classify_windows, ActivityMonitor

class ActivityTests(unittest.TestCase):
 def test_desktop_identities(self):
  self.assertEqual(classify_windows([(10,'C:/Program Files/WindowsApps/OpenAI.Codex_1/app/ChatGPT.exe'),(20,'C:/Apps/Claude/claude.exe')],[],99),(True,True))
 def test_chatgpt_is_not_codex(self):
  self.assertEqual(classify_windows([(10,'C:/Apps/ChatGPT/ChatGPT.exe')],[],99),(False,False))
 def test_own_child_and_descendants_excluded(self):
  self.assertEqual(classify_windows([(2,'codex.exe'),(3,'claude.exe')],[(3,2),(2,1)],1),(False,False))
 def test_no_visible_windows(self):
  self.assertEqual(classify_windows([],[(2,1)],1),(False,False))
 def test_case_and_separators(self):
  self.assertEqual(classify_windows([(10,r'C:\Apps\CODEX.EXE'),(20,r'C:\Apps\CLAUDE.EXE')],[],99),(True,True))
 def test_monitor_changes_and_failure(self):
  from PySide6.QtWidgets import QApplication
  app=QApplication.instance() or QApplication([])
  events=[]; errors=[]
  states=iter([(True,False),(True,False),(False,True),OSError(),(False,True)])
  def detect():
   value=next(states)
   if isinstance(value,Exception): raise value
   return value
  monitor=ActivityMonitor(detector=detect)
  monitor.changed.connect(lambda a,b:events.append((a,b)))
  monitor.failed.connect(lambda:errors.append(True))
  for _ in range(5): monitor.check()
  self.assertEqual(events,[(True,False),(False,True),(False,True)])
  self.assertEqual(errors,[True])
