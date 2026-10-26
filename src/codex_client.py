import json
import os
import shutil
import subprocess
import threading
from queue import Queue, Empty

MAX_LINE = 1024 * 1024
class ClientError(Exception):
    pass

def find_codex():
    # Never execute npm .cmd wrappers through a command interpreter.
    direct = shutil.which('codex.exe' if os.name == 'nt' else 'codex')
    if direct and not direct.lower().endswith(('.cmd','.bat')):
        return [direct]
    if os.name == 'nt':
        from pathlib import Path
        npm = Path(os.environ.get('APPDATA','')) / 'npm/node_modules/@openai/codex/node_modules'
        if npm.is_dir():
            matches = sorted(npm.glob('@openai/codex-win32-*/vendor/*/codex/codex.exe'))
            if matches:
                return [str(matches[-1])]
    raise ClientError('Codex CLI unavailable. Install official Codex and add codex.exe to PATH.')

class CodexClient:
    def __init__(self, command=None):
        self.command = command
        self.process = None
        self.events = Queue(maxsize=256)
        self.reader = None
        self.counter = 0
    def start(self):
        self.close()
        self.events = Queue(maxsize=256)
        command = self.command or find_codex()
        try:
            self.process = subprocess.Popen(command + ['-c','analytics.enabled=false','-c','feedback.enabled=false','-c','otel.exporter="none"','app-server','--listen','stdio://'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except OSError:
            raise ClientError('Cannot start official Codex CLI') from None
        proc, events = self.process, self.events
        def read():
            try:
                while True:
                    raw = proc.stdout.readline(MAX_LINE+1)
                    if not raw or len(raw) > MAX_LINE:
                        break
                    try:
                        message = json.loads(raw)
                    except (ValueError, UnicodeError):
                        break
                    if not isinstance(message, dict):
                        break
                    # Ignore unrelated notifications; never retain account metadata.
                    if 'id' in message or message.get('method') == 'account/rateLimits/updated':
                        events.put(message, timeout=1)
            except Exception:
                pass
            finally:
                try: events.put(None, timeout=1)
                except Exception: pass
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()
    def send(self, method, params=None, request=True):
        self.counter += 1
        msg = {'method':method}
        if params is not None: msg['params'] = params
        if request: msg['id'] = self.counter
        try:
            self.process.stdin.write((json.dumps(msg)+'\n').encode())
            self.process.stdin.flush()
        except (OSError, AttributeError, ValueError):
            raise ClientError('Codex app-server disconnected') from None
        return self.counter
    def receive(self, timeout=0.2):
        try:
            item = self.events.get(timeout=timeout)
        except Empty:
            return {}
        if item is None:
            raise ClientError('Codex app-server stopped; reconnecting')
        return item
    def close(self):
        proc = self.process
        self.process = None
        if proc:
            try:
                proc.stdin.close()
                proc.wait(timeout=2)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                if proc.poll() is None:
                    proc.terminate()
                    try: proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill(); proc.wait(timeout=2)
            finally:
                proc.stdout.close()
        if self.reader:
            self.reader.join(timeout=2)
            self.reader = None
