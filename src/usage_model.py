from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class Window:
    used: int
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
