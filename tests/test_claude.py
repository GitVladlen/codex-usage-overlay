import json
import math
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt
from src.claude_client import ClaudeClient,find_claude
from src.claude_worker import ClaudeWorker
from src.codex_client import ClientError
from src.usage_model import parse_claude_usage


def payload(used=25):
 return {'rate_limits_available':True,'rate_limits':{'five_hour':{'utilization':used,'resets_at':'2024-01-01T00:00:00.123456+00:00'},'seven_day':{'utilization':1,'resets_at':None}}}

class ClaudeParsingTests(unittest.TestCase):
 def test_percentage_and_iso_reset(self):
  windows=parse_claude_usage(payload(25.5))
  self.assertEqual(windows[300].remaining,74.5)
  self.assertEqual(windows[300].resets,1704067200)
  self.assertEqual(windows[10080].remaining,99)
  self.assertIsNone(windows[10080].resets)
 def test_missing_is_not_zero(self):
  for data in [None,{}, {'rate_limits_available':False}, {'rate_limits_available':True,'rate_limits':None}, {'rate_limits_available':True,'rate_limits':{}}]:
   with self.assertRaises(ValueError):parse_claude_usage(data)
 def test_invalid_percent(self):
  for number in [True,-1,'1',math.nan,math.inf]:
   with self.assertRaises(ValueError):parse_claude_usage(payload(number))
 def test_invalid_and_utc_timestamps(self):
  for reset in ['tomorrow','2024-01-01T00:00:00',123,False]:
   data=payload();data['rate_limits']['five_hour']['resets_at']=reset
   with self.assertRaises(ValueError):parse_claude_usage(data)
  data=payload();data['rate_limits']['five_hour']['resets_at']='2024-01-01T00:00:00Z'
  self.assertEqual(parse_claude_usage(data)[300].resets,1704067200)
 def test_null_window_and_over_limit(self):
  data=payload(105); data['rate_limits']['seven_day']=None
  windows=parse_claude_usage(data); self.assertEqual(windows[300].remaining,0)
  self.assertNotIn(10080,windows)

class ClaudeClientTests(unittest.TestCase):
 def test_configured_native_path(self):
  with tempfile.TemporaryDirectory() as root:
   p=Path(root)/'claude.exe';p.touch()
   self.assertEqual(find_claude(str(p)),str(p))
   self.assertEqual(find_claude(' \"'+str(p)+'\" '),str(p))
 def test_managed_cli_without_path_or_preference(self):
  with tempfile.TemporaryDirectory() as root:
   runtime=Path(root)/'CodexUsageOverlay/tools/claude.exe'
   runtime.parent.mkdir(parents=True);runtime.touch()
   with patch('src.claude_client.local_claude_candidates',return_value=[]),patch('src.claude_client.shutil.which',return_value=None),patch('pathlib.Path.home',return_value=Path(root)/'empty'),patch.dict(os.environ,{'LOCALAPPDATA':root}):
    self.assertEqual(find_claude(''),str(runtime))
 def test_project_local_runtime_and_stale_preference(self):
  with tempfile.TemporaryDirectory() as root:
   runtime=Path(root)/'claude.exe';runtime.touch()
   with patch('src.claude_client.local_claude_candidates',return_value=[runtime]):
    self.assertEqual(find_claude('C:/missing/claude.exe'),str(runtime))
    self.assertEqual(find_claude(''),str(runtime))
 def test_missing_cli(self):
  with patch('src.claude_client.shutil.which',return_value=None),patch('pathlib.Path.is_file',return_value=False):
   with self.assertRaises(ClientError):find_claude()
 def test_safe_launch(self):
  with patch('src.claude_client.find_claude',return_value='official.exe'),patch.object(ClaudeClient,'_launch') as launch:
   ClaudeClient().start(); args,env=launch.call_args.args
   self.assertIn('--safe-mode',args);self.assertIn('--restricted',args)
   self.assertIn('--no-session-persistence',args)
   self.assertEqual(args[args.index('--tools')+1],'')
   self.assertEqual(env['DISABLE_TELEMETRY'],'1')
   self.assertEqual(env['DISABLE_AUTOUPDATER'],'1')
   self.assertEqual(env['DISABLE_ERROR_REPORTING'],'1')
   self.assertNotIn('CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC',env)
 def test_only_usage_and_initialize_can_be_sent(self):
  import io
  class Process:stdin=io.BytesIO()
  client=ClaudeClient();client.process=Process()
  client.send_control('initialize');client.send_control('get_usage')
  messages=[json.loads(line) for line in client.process.stdin.getvalue().splitlines()]
  self.assertTrue(all(m['type']=='control_request' for m in messages))
  self.assertEqual(messages[1]['request'],{'subtype':'get_usage','skip_behaviors':True})
  with self.assertRaises(ClientError):client.send_control('query')
  with self.assertRaises(ClientError):client.send('anything')

class ClaudeWorkerTests(unittest.TestCase):
 def test_inactive_does_not_start_cli(self):
  calls=[]
  worker=ClaudeWorker(client_factory=lambda:calls.append(True))
  worker.start();time.sleep(.1);worker.stop();self.assertTrue(worker.wait(2000))
  self.assertEqual(calls,[])
 def test_poll_and_graceful_cleanup(self):
  instances=[];output=[];worker=None
  class Fake:
   def __init__(self):self.messages=[];self.count=0;self.closed=False;instances.append(self)
   def start(self):pass
   def send_control(self,subtype):
    self.count+=1;rid=str(self.count)
    data={} if subtype=='initialize' else payload()
    self.messages.append({'type':'control_response','response':{'request_id':rid,'subtype':'success','response':data}})
    return rid
   def receive(self):
    if self.messages:return self.messages.pop(0)
    worker.stop();return {}
   def close(self):self.closed=True
  worker=ClaudeWorker(client_factory=Fake);worker.set_active(True)
  worker.updated.connect(lambda w,t:output.append(w[300].remaining),Qt.DirectConnection)
  worker.start();self.assertTrue(worker.wait(3000))
  self.assertEqual(output,[75]);self.assertEqual(instances[0].count,2);self.assertTrue(instances[0].closed)
 def test_cli_crash_reconnects(self):
  instances=[];worker=None
  class Failing:
   def __init__(self):self.closed=False;instances.append(self)
   def start(self):
    if len(instances)>1:worker.stop()
    raise ClientError('offline')
   def close(self):self.closed=True
  worker=ClaudeWorker(client_factory=Failing);worker.set_active(True);worker.start()
  self.assertTrue(worker.wait(4000));self.assertEqual(len(instances),2)
  self.assertTrue(all(c.closed for c in instances))
