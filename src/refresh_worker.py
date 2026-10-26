import threading
import time
from PySide6.QtCore import QThread, Signal
from .codex_client import CodexClient, ClientError
from .usage_model import UsageState, parse_usage

class Schedule:
    def __init__(self):
        self.pending = None
        self.deadline = 0
        self.next_poll = 0
    def due(self, now):
        return self.pending is None and now >= self.next_poll
    def begin(self, request_id, now, interval):
        self.pending = request_id
        self.deadline = now + 20
        self.next_poll = now + interval
    def complete(self, request_id):
        if request_id != self.pending: return False
        self.pending = None
        return True

class RefreshWorker(QThread):
    updated = Signal(object, float)
    failed = Signal(str)
    def __init__(self, interval=30, client_factory=CodexClient):
        super().__init__()
        self.interval = interval
        self.factory = client_factory
        self.stop_event = threading.Event()
        self.refresh_event = threading.Event()
    def refresh(self): self.refresh_event.set()
    def stop(self): self.stop_event.set()
    def run(self):
        retry = 1
        while not self.stop_event.is_set():
            client = self.factory()
            try:
                client.start()
                init = client.send('initialize', {'clientInfo':{'name':'codex_usage_overlay','title':'Codex Usage Overlay','version':'1.0.0'},'capabilities':{'experimentalApi':False}})
                deadline = time.monotonic()+20
                while True:
                    if self.stop_event.is_set(): return
                    if time.monotonic()>deadline: raise ClientError('Codex initialization timed out')
                    msg = client.receive()
                    if msg.get('id') == init:
                        if 'error' in msg: raise ClientError('Codex protocol initialization failed')
                        if not isinstance(msg.get('result'),dict): raise ClientError('Invalid initialization response')
                        break
                client.send('initialized', request=False)
                state, schedule = UsageState(), Schedule()
                revision = poll_revision = 0
                while not self.stop_event.is_set():
                    now = time.monotonic()
                    if self.refresh_event.is_set():
                        self.refresh_event.clear(); schedule.next_poll = 0
                    if schedule.due(now):
                        schedule.begin(client.send('account/rateLimits/read', {}), now, self.interval)
                        poll_revision = revision
                    if schedule.pending is not None and now > schedule.deadline:
                        raise ClientError('Usage request timed out; reconnecting')
                    msg = client.receive()
                    if not msg: continue
                    notification = msg.get('method') == 'account/rateLimits/updated' and 'id' not in msg
                    if notification:
                        try:
                            windows = parse_usage(msg.get('params'), True)
                            if state.accept(windows):
                                revision += 1
                                self.updated.emit(dict(state.windows),time.time())
                        except ValueError:
                            self.failed.emit('Invalid usage notification; waiting for poll')
                    elif 'id' in msg and schedule.complete(msg['id']):
                        if poll_revision != revision:
                            continue  # An event superseded this in-flight read.
                        if 'error' in msg:
                            self.failed.emit('Usage unavailable. Check Codex login, plan, and network connection.')
                            continue
                        try:
                            windows = parse_usage(msg.get('result'))
                            state.accept(windows, True)
                            self.updated.emit(dict(state.windows),time.time()); retry = 1
                        except ValueError as error: self.failed.emit(str(error))
                    elif 'id' in msg and 'method' in msg:
                        # This client never authorizes tool executions or credential requests.
                        raise ClientError('Unexpected server request; connection closed')
            except ClientError as error:
                self.failed.emit(str(error))
            except OSError:
                self.failed.emit('Cannot communicate with Codex CLI; retrying.')
            finally:
                client.close()
            self.stop_event.wait(retry)
            retry = min(30,retry*2)
