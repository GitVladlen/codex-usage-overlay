import threading
import time
from .refresh_worker import RefreshWorker, Schedule
from .claude_client import ClaudeClient
from .codex_client import ClientError
from .usage_model import parse_claude_usage


class ClaudeWorker(RefreshWorker):
    def __init__(self,interval=30,executable='',client_factory=None):
        super().__init__(interval)
        self.executable=executable
        self.active=threading.Event()
        self.restart_event=threading.Event()
        self.client_factory=client_factory
    def set_active(self,active):
        if active:
            self.active.set(); self.refresh()
        else: self.active.clear()
    def set_executable(self,path):
        if path!=self.executable:
            self.executable=path; self.restart_event.set(); self.refresh()
    def run(self):
        retry=1
        while not self.stop_event.is_set():
            if not self.active.is_set():
                self.stop_event.wait(.25); continue
            self.restart_event.clear()
            client=self.client_factory() if self.client_factory else ClaudeClient(self.executable)
            try:
                client.start()
                initialize=client.send_control('initialize')
                deadline=time.monotonic()+30
                while not self.stop_event.is_set():
                    if self.restart_event.is_set(): raise ClientError('Claude CLI configuration changed')
                    if time.monotonic()>deadline: raise ClientError('Claude initialization timed out')
                    message=client.receive()
                    if message.get('type')=='control_request': raise ClientError('Unexpected Claude server request')
                    response=message.get('response')
                    if not isinstance(response,dict) or response.get('request_id')!=initialize: continue
                    if response.get('subtype')!='success' or not isinstance(response.get('response'),dict):
                        raise ClientError('Claude initialization failed. Check CLI login.')
                    break
                schedule=Schedule()
                while not self.stop_event.is_set():
                    if self.restart_event.is_set(): raise ClientError('Claude CLI configuration changed')
                    now=time.monotonic()
                    if self.refresh_event.is_set():
                        self.refresh_event.clear(); schedule.next_poll=0
                    if self.active.is_set() and schedule.due(now):
                        schedule.begin(client.send_control('get_usage'),now,self.interval)
                        schedule.deadline=now+30
                    if schedule.pending is not None and now>schedule.deadline:
                        raise ClientError('Claude usage timed out; reconnecting')
                    message=client.receive()
                    if message.get('type')=='control_request': raise ClientError('Unexpected Claude server request')
                    response=message.get('response')
                    if message.get('type')!='control_response' or not isinstance(response,dict): continue
                    if not schedule.complete(response.get('request_id')): continue
                    if response.get('subtype')!='success':
                        self.failed.emit('Claude usage request failed. Check CLI login and network.'); continue
                    try:
                        windows=parse_claude_usage(response.get('response'))
                        self.updated.emit(windows,time.time()); retry=1
                    except ValueError as error: self.failed.emit(str(error))
            except ClientError as error:
                self.failed.emit(str(error))
            except OSError:
                self.failed.emit('Cannot communicate with Claude CLI; retrying.')
            finally:
                client.close()
            self.stop_event.wait(retry); retry=min(30,retry*2)
