import unittest
from src.usage_model import parse_window,parse_usage,UsageState,Window
class UsageTests(unittest.TestCase):
 def test_conversion(self):
  for used,left in [(0,100),(32,68),(100,0),(110,0)]: self.assertEqual(parse_window(dict(usedPercent=used,windowDurationMins=300,resetsAt=1700000000)).remaining,left)
 def test_timestamp(self):
  self.assertEqual(parse_window(dict(usedPercent=1,windowDurationMins=300,resetsAt=1700000000)).resets,1700000000)
 def test_malformed(self):
  for data in [None,{},dict(usedPercent=True,windowDurationMins=300),dict(usedPercent=1,windowDurationMins=300,resetsAt='tomorrow'),dict(usedPercent=-1,windowDurationMins=300),dict(usedPercent=1,windowDurationMins=300,resetsAt=10**30)]:
   with self.assertRaises(ValueError): parse_window(data)
 def test_missing(self):
  with self.assertRaises(ValueError): parse_usage({'rateLimits':{}})
 def test_bucket(self):
  w=dict(usedPercent=20,windowDurationMins=300)
  self.assertEqual(parse_usage({'rateLimits':{},'rateLimitsByLimitId':{'codex':{'primary':w}}})[300].remaining,80)
 def test_duplicate_delayed_reset(self):
  s=UsageState(); self.assertTrue(s.accept({300:Window(30,300,2000)}))
  self.assertFalse(s.accept({300:Window(30,300,2000)}))
  self.assertFalse(s.accept({300:Window(20,300,2000)}))
  self.assertFalse(s.accept({300:Window(99,300,1000)}))
  self.assertTrue(s.accept({300:Window(0,300,3000)}))
 def test_sparse(self):
  s=UsageState(); s.accept({300:Window(30,300,2000),10080:Window(50,10080,4000)})
  s.accept(parse_usage({'rateLimits':{'primary':dict(usedPercent=40,windowDurationMins=300,resetsAt=2000)}},True))
  self.assertEqual(s.windows[10080].used,50)
 def test_authoritative_correction(self):
  s=UsageState(); s.accept({300:Window(50,300,2000)})
  s.accept({300:Window(20,300,2000)},True); self.assertEqual(s.windows[300].used,20)
