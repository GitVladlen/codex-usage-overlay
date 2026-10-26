from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class Window:
    used: int | float
    minutes: int
    resets: int | None
    @property
    def remaining(self):
        return max(0, min(100, 100-self.used))

def parse_window(value):
    if not isinstance(value, dict):
        raise ValueError("Invalid usage window")
    used, minutes, resets = (value.get(k) for k in ('usedPercent','windowDurationMins','resetsAt'))
    if type(used) is not int or used < 0 or used > 2147483647:
        raise ValueError("Invalid consumed percentage")
    if type(minutes) is not int or minutes <= 0:
        raise ValueError("Unavailable window duration")
    if resets is not None:
        if type(resets) is not int or not 0 <= resets <= 253402300799:
            raise ValueError("Invalid reset timestamp")
        datetime.fromtimestamp(resets, timezone.utc)
    return Window(used, minutes, resets)

def parse_usage(payload, notification=False):
    if not isinstance(payload, dict):
        raise ValueError("Invalid usage response")
    buckets = payload.get('rateLimitsByLimitId')
    snapshot = buckets.get('codex') if isinstance(buckets, dict) and 'codex' in buckets else payload.get('rateLimits')
    if not isinstance(snapshot, dict):
        raise ValueError("Usage unavailable")
    if snapshot.get('limitId') not in (None, 'codex'):
        return {}
    windows = {}
    for key in ('primary','secondary'):
        if snapshot.get(key) is not None:
            window = parse_window(snapshot[key])
            if window.minutes in (300,10080):
                windows[window.minutes] = window
    if not windows and not notification:
        raise ValueError("5-hour and weekly limits unavailable for this account")
    return windows

class UsageState:
    def __init__(self):
        self.windows = {}
    def accept(self, windows, authoritative=False):
        changed = False
        if authoritative:
            changed = windows != self.windows
            self.windows = dict(windows)
            return changed
        for duration, new in windows.items():
            old = self.windows.get(duration)
            if old and old.resets is not None and new.resets is not None:
                if new.resets < old.resets or (new.resets == old.resets and new.used < old.used):
                    continue
            if new != old:
                self.windows[duration] = new
                changed = True
        return changed


def parse_claude_usage(payload):
    import math
    if not isinstance(payload,dict): raise ValueError('Invalid Claude usage response')
    available=payload.get('rate_limits_available')
    if available is False:
        raise ValueError('Claude plan limits unavailable. Check CLI login and subscription.')
    if available is not True: raise ValueError('Invalid Claude usage availability')
    limits=payload.get('rate_limits')
    if limits is None:
        raise ValueError('Claude could not fetch usage; retrying.')
    if not isinstance(limits,dict): raise ValueError('Invalid Claude rate limits')
    windows={}
    for key,minutes in [('five_hour',300),('seven_day',10080)]:
        value=limits.get(key)
        if value is None: continue
        if not isinstance(value,dict): raise ValueError('Invalid Claude usage window')
        used=value.get('utilization')
        if used is None: continue
        if type(used) not in (int,float) or not math.isfinite(used) or not 0<=used<=10000:
            raise ValueError('Invalid Claude consumed percentage')
        reset=value.get('resets_at')
        stamp=None
        if reset is not None:
            if not isinstance(reset,str) or len(reset)>80: raise ValueError('Invalid Claude reset time')
            try:
                date=datetime.fromisoformat(reset.replace('Z','+00:00'))
                if date.tzinfo is None: raise ValueError()
                stamp=int(date.timestamp())
                if stamp<0: raise ValueError()
            except (ValueError,OverflowError,OSError):
                raise ValueError('Invalid Claude reset time') from None
        windows[minutes]=Window(used,minutes,stamp)
    if not windows: raise ValueError('Claude returned no usage windows; retrying.')
    return windows
