"""Read official Claude CLI usage without prompts, credentials or history access."""
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time


def probe(executable, essential_only=False):
    env=dict(os.environ,DISABLE_AUTOUPDATER='1',DISABLE_TELEMETRY='1',DISABLE_ERROR_REPORTING='1')
    if essential_only:
        env['CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC']='1'
    else:
        env.pop('CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC',None)
    arguments=[str(executable),'--safe-mode','--restricted','--print',
        '--input-format','stream-json','--output-format','stream-json','--verbose',
        '--no-session-persistence','--permission-mode','dontAsk','--tools','',
        '--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--no-chrome',
        '--setting-sources','']
    process=subprocess.Popen(arguments,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,env=env,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    events=queue.Queue(maxsize=64)
    def read():
        try:
            while True:
                line=process.stdout.readline(1024*1024+1)
                if not line or len(line)>1024*1024: break
                message=json.loads(line)
                if isinstance(message,dict): events.put(message,timeout=1)
        except (ValueError,OSError,queue.Full): pass
        finally:
            try: events.put(None,timeout=1)
            except queue.Full: pass
    reader=threading.Thread(target=read,daemon=True); reader.start()
    def request(identifier,subtype,**fields):
        process.stdin.write((json.dumps({'type':'control_request','request_id':identifier,
            'request':{'subtype':subtype,**fields}})+'\n').encode())
        process.stdin.flush()
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            try: message=events.get(timeout=.25)
            except queue.Empty: continue
            if message is None: raise RuntimeError('Official CLI disconnected')
            if message.get('type')=='control_request': raise RuntimeError('Unexpected server request')
            response=message.get('response',{})
            if message.get('type')=='control_response' and response.get('request_id')==identifier:
                if response.get('subtype')!='success': raise RuntimeError('Official CLI rejected request')
                return response.get('response',{})
        raise TimeoutError('Official CLI usage timed out')
    try:
        request('initialize','initialize',hooks={},sdkMcpServers=[],agents={})
        data=request('usage','get_usage',skip_behaviors=True)
        limits=data.get('rate_limits')
        result={'available':data.get('rate_limits_available'), 'has_limits':isinstance(limits,dict),
            'history_skipped':data.get('behaviors') is None,
            'session_cost':data.get('session',{}).get('total_cost_usd'),'windows':{}}
        if isinstance(limits,dict):
            for name in ('five_hour','seven_day'):
                window=limits.get(name)
                if isinstance(window,dict):
                    result['windows'][name]={key:window.get(key) for key in ('utilization','resets_at')}
        return result
    finally:
        process.stdin.close()
        try: process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.terminate()
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=3)
        reader.join(timeout=2); process.stdout.close()

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli',type=Path,default=Path(__file__).resolve().parent.parent/'.venv/claude-probe/claude.exe')
    parser.add_argument('--essential-only',action='store_true',help='Diagnostic only: umbrella traffic flag can suppress usage fetching')
    options=parser.parse_args()
    print(json.dumps(probe(options.cli,options.essential_only),indent=2))
