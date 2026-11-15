"""A bounded one-frame mailbox prevents an inference backlog."""

from threading import Lock
from time import monotonic


class LatestFrame:
    def __init__(self):
        self._lock = Lock()
        self._pending = None
        self.replaced = 0

    def put(self, message, received_at=None):
        timestamp = monotonic() if received_at is None else received_at
        with self._lock:
            if self._pending is not None:
                self.replaced += 1
            self._pending = (message, timestamp)

    def take(self):
        with self._lock:
            pending, self._pending = self._pending, None
            return pending


def is_stale(stamp_ns: int, now_ns: int, received_at: float,
             now_monotonic: float, max_age: float) -> bool:
    # Zero ROS stamps are unspecified: still enforce local arrival age.
    return (now_monotonic - received_at > max_age
            or (stamp_ns > 0 and (now_ns - stamp_ns) / 1e9 > max_age))
