from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path
import re

@dataclass
class Config:
    refresh_interval: int = 30
    x: int | None = None
    y: int | None = None
    monitor: str = ''
    font_size: int = 11
    font_color: str = '#eeeeee'
    opacity: int = 75
    click_through: bool = True
    background: bool = False
    start_with_windows: bool = False
    show_reset_times: bool = True
    show_weekly: bool = True
    progress_bars: bool = False

def config_path():
    return Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'CodexUsageOverlay/settings.json'

def validate(data):
    defaults = asdict(Config())
    if not isinstance(data,dict): return Config()
    for key, default in defaults.items():
        value = data.get(key,default)
        if key in ('x','y'):
            if value is None or (type(value) is int and abs(value)<100000): defaults[key]=value
        elif type(value) is type(default): defaults[key]=value
    for key,lo,hi in [('refresh_interval',5,3600),('font_size',8,36),('opacity',10,100)]:
        defaults[key]=max(lo,min(hi,defaults[key]))
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', defaults['font_color']): defaults['font_color']='#eeeeee'
    defaults['monitor']=defaults['monitor'][:256]
    return Config(**defaults)

def load(path=None):
    try:
        path = path or config_path()
        if path.stat().st_size>65536: return Config()
        return validate(json.loads(path.read_text(encoding='utf-8')))
    except (OSError, ValueError): return Config()

def save(config,path=None):
    path = path or config_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(asdict(config),indent=2),encoding='utf-8')
    temp.replace(path)
