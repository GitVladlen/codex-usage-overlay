"""Official Claude Code stream-json control API; never sends a model prompt."""
import json
import os
from pathlib import Path
import shutil
import sys
from .codex_client import CodexClient, ClientError


def local_claude_candidates():
    if getattr(sys,'frozen',False):
        directory=Path(sys.executable).resolve().parent
        # Side-by-side deployments, then the standard project/dist/app layout.
        return [directory/'tools/claude.exe',directory.parent.parent/'tools/claude.exe']
    return [Path(__file__).resolve().parent.parent/'tools/claude.exe']


def find_claude(configured=''):
    configured=configured.strip().strip('"').strip("'").strip()
    if configured:
        path=Path(configured)
        if path.is_absolute() and path.suffix.lower()=='.exe' and path.is_file():
            return str(path)
    # App/project-local dependencies avoid MSIX AppData redirection entirely.
    for path in local_claude_candidates():
        if path.is_file(): return str(path)
    direct=shutil.which('claude.exe' if os.name=='nt' else 'claude')
    if direct and not direct.lower().endswith(('.cmd','.bat')):
        return direct
    native=Path.home()/'.local/bin/claude.exe'
    if native.is_file(): return str(native)
    local=os.environ.get('LOCALAPPDATA')
    if local:
        managed=Path(local)/'CodexUsageOverlay/tools/claude.exe'
        if managed.is_file(): return str(managed)
    if configured:
        raise ClientError('Claude CLI path must point to an existing native .exe')
    raise ClientError('Claude CLI not found. Set its executable path in Overlay Settings.')


class ClaudeClient(CodexClient):
    def __init__(self, executable=''):
        super().__init__()
        self.executable=executable
    def _keep_message(self, message):
        return message.get('type') in ('control_response','control_request')
    def start(self):
        exe=find_claude(self.executable)
        env=dict(os.environ,DISABLE_AUTOUPDATER='1',DISABLE_TELEMETRY='1',DISABLE_ERROR_REPORTING='1',CLAUDE_CODE_ENABLE_TELEMETRY='0')
        # The umbrella flag also suppresses get_usage. Keep the specific opt-outs.
        env.pop('CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC',None)
        arguments=[exe,'--safe-mode','--restricted','--print',
            '--input-format','stream-json','--output-format','stream-json','--verbose',
            '--no-session-persistence','--permission-mode','dontAsk','--tools','',
            '--strict-mcp-config','--mcp-config','{"mcpServers":{}}',
            '--no-chrome','--setting-sources','']
        try: self._launch(arguments,env)
        except ClientError: raise ClientError('Cannot start official Claude CLI') from None
    def receive(self,timeout=.2):
        try: return super().receive(timeout)
        except ClientError: raise ClientError('Claude CLI disconnected; reconnecting') from None
    def send_control(self, subtype):
        if subtype=='initialize': fields={'hooks':{},'sdkMcpServers':[],'agents':{}}
        elif subtype=='get_usage': fields={'skip_behaviors':True}
        else: raise ClientError('Unsupported Claude control request')
        self.counter+=1
        identifier='overlay-'+str(self.counter)
        message={'type':'control_request','request_id':identifier,
            'request':{'subtype':subtype,**fields}}
        try:
            self.process.stdin.write((json.dumps(message)+'\n').encode())
            self.process.stdin.flush()
        except (OSError,AttributeError,ValueError):
            raise ClientError('Claude CLI disconnected; reconnecting') from None
        return identifier
    def send(self,*args,**kwargs):
        raise ClientError('Claude client only permits initialize and get_usage')
