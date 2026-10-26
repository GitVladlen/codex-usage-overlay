import unittest
from unittest.mock import patch
from src.codex_client import CodexClient,ClientError,find_codex
class ClientTests(unittest.TestCase):
 def test_missing_cli(self):
  with patch('src.codex_client.shutil.which',return_value=None),patch('pathlib.Path.is_dir',return_value=False),patch('pathlib.Path.glob',return_value=[]):
   with self.assertRaises(ClientError): find_codex()
 def test_launch_failure(self):
  with patch('src.codex_client.subprocess.Popen',side_effect=OSError):
   with self.assertRaises(ClientError): CodexClient(['missing.exe']).start()
 def test_eof(self):
  c=CodexClient(); c.events.put(None)
  with self.assertRaises(ClientError): c.receive()
 def test_bad_pipe(self):
  with self.assertRaises(ClientError): CodexClient().send('initialize')
 def test_close_idempotent(self):
  c=CodexClient(); c.close(); c.close()

class StdioIntegrationTests(unittest.TestCase):
 def test_real_pipe_and_clean_shutdown(self):
  import sys,time
  program = "import sys,json; [(print(json.dumps({'id': m['id'], 'result': {}}),flush=True)) for line in sys.stdin if (m:=json.loads(line)) and 'id' in m]"
  c=CodexClient([sys.executable,'-u','-c',program])
  try:
   c.start(); proc=c.process; request=c.send('initialize',{})
   deadline=time.monotonic()+5; message={}
   while not message and time.monotonic()<deadline: message=c.receive()
   self.assertEqual(message,{'id':request,'result':{}})
  finally: c.close()
  self.assertIsNotNone(proc.poll())

class DiscoveryTests(unittest.TestCase):
 def test_desktop_cli_without_path(self):
  import os,tempfile
  from pathlib import Path
  if os.name != 'nt': self.skipTest('Windows discovery')
  with tempfile.TemporaryDirectory() as root:
   exe=Path(root)/'OpenAI/Codex/bin/version/codex.exe'
   exe.parent.mkdir(parents=True); exe.touch()
   with patch('src.codex_client.shutil.which',return_value=None),patch.dict(os.environ,{'LOCALAPPDATA':root,'APPDATA':str(Path(root)/'empty')}):
    self.assertEqual(find_codex(),[str(exe)])
