import unittest,tempfile
from pathlib import Path
from src.config import Config,load,save,validate
class SettingsTests(unittest.TestCase):
 def test_roundtrip(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'settings.json'; c=Config(x=-500,monitor='Display 2'); save(c,p); self.assertEqual(load(p),c)
 def test_corrupt(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'settings.json'; p.write_text('broken'); self.assertEqual(load(p),Config())
 def test_validation(self):
  c=validate({'font_size':999,'opacity':False,'font_color':'red; url(x)','refresh_interval':0,'click_through':'false'})
  self.assertEqual((c.font_size,c.opacity,c.font_color,c.refresh_interval,c.click_through),(36,75,'#eeeeee',5,True))
