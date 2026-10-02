import time
from collections import OrderedDict
from threading import RLock


class TTLCache:
    """Bounded, expendable process cache. Never used as cross-instance quota protection."""
    def __init__(self, max_entries: int = 512):
        self.entries = OrderedDict()
        self.max_entries = max_entries
        self.lock = RLock()

    def get(self, key):
        with self.lock:
            entry = self.entries.get(key)
            if entry is None:
                return None
            expires, value = entry
            if expires <= time.monotonic():
                del self.entries[key]
                return None
            self.entries.move_to_end(key)
            return value

    def put(self, key, value, ttl_s: int):
        with self.lock:
            self.entries[key] = (time.monotonic() + ttl_s, value)
            self.entries.move_to_end(key)
            while len(self.entries) > self.max_entries:
                self.entries.popitem(last=False)
        return value
