import unittest,time
from src.refresh_worker import Schedule,RefreshWorker
from src.codex_client import ClientError
class SchedulingTests(unittest.TestCase):
 def test_no_overlap(self):
  s=Schedule(); self.assertTrue(s.due(0)); s.begin(1,0,30)
  self.assertFalse(s.due(40)); self.assertFalse(s.complete(2)); self.assertTrue(s.complete(1)); self.assertFalse(s.due(29)); self.assertTrue(s.due(30))
 def test_reconnect_and_stop(self):
  clients=[]
  class Failing:
   def __init__(self): self.closed=False; clients.append(self)
   def start(self): raise ClientError('offline')
   def close(self): self.closed=True
  w=RefreshWorker(client_factory=Failing); w.start(); time.sleep(1.2); w.stop(); self.assertTrue(w.wait(3000)); self.assertGreaterEqual(len(clients),2); self.assertTrue(all(c.closed for c in clients))
 def test_notification(self):
  clients=[]; worker=None
  class Fake:
   def __init__(self): self.messages=[]; self.count=0; self.closed=False; clients.append(self)
   def start(self): pass
   def send(self,method,params=None,request=True):
    self.count+=1
    if method=='initialize': self.messages.append({'id':self.count,'result':{}})
    if method=='account/rateLimits/read':
     self.messages.extend([{'id':self.count,'result':{'rateLimits':{'primary':{'usedPercent':20,'windowDurationMins':300,'resetsAt':2000000000}}}}, {'method':'account/rateLimits/updated','params':{'rateLimits':{'primary':{'usedPercent':30,'windowDurationMins':300,'resetsAt':2000000000}}}}])
    return self.count
   def receive(self):
    if self.messages: return self.messages.pop(0)
    worker.stop(); return {}
   def close(self): self.closed=True
  worker=RefreshWorker(client_factory=Fake); output=[]
  from PySide6.QtCore import Qt
  worker.updated.connect(lambda w,t:output.append(w[300].used),Qt.DirectConnection)
  worker.start(); self.assertTrue(worker.wait(3000)); self.assertEqual(output,[20,30]); self.assertTrue(clients[0].closed)
