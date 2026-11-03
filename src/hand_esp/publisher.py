"""Latest-state delivery outside the camera loop, with bounded request rate."""

from dataclasses import dataclass
from threading import Condition, Thread
import time

from .protocol import NEUTRAL


@dataclass(frozen=True)
class Delivery:
    target: object
    acknowledged: object
    acknowledged_at: float
    error: str | None


class Publisher:
    def __init__(self, send, heartbeat=1., min_interval=.25):
        self.send = send
        self.heartbeat, self.min_interval = heartbeat, min_interval
        self.condition = Condition()
        self.target, self.acknowledged = NEUTRAL, None
        self.acknowledged_at, self.error = 0., None
        self.stopped = False
        self.thread = Thread(target=self._run, name='esp-fingers', daemon=True)
        self.thread.start()

    def set(self, state):
        with self.condition:
            self.target = state
            self.condition.notify_all()

    def status(self):
        with self.condition:
            return Delivery(self.target, self.acknowledged, self.acknowledged_at, self.error)

    def _run(self):
        sequence, last_attempt, retry_at = 0, float('-inf'), 0.
        while True:
            with self.condition:
                if self.stopped:
                    return
                now = time.monotonic()
                changed = self.target != self.acknowledged
                next_attempt = max(last_attempt + self.min_interval, retry_at,
                                   0 if changed else self.acknowledged_at + self.heartbeat)
                if now < next_attempt:
                    self.condition.wait(timeout=next_attempt - now)
                    continue
                state = self.target
                last_attempt = now
                sequence = sequence % 0xFFFFFFFF + 1
            try:
                self.send(state, sequence)
            except Exception as exc:
                with self.condition:
                    self.error = str(exc)
                retry_at = time.monotonic() + 1.
            else:
                with self.condition:
                    self.acknowledged, self.acknowledged_at = state, time.monotonic()
                    self.error = None
                    self.condition.notify_all()
                retry_at = 0.

    def close(self, timeout=2.5):
        # Give a neutral state one bounded chance to reach the ESP. Firmware
        # also expires its state if the process/network disappears abruptly.
        deadline = time.monotonic() + timeout
        with self.condition:
            if self.stopped:
                return
            self.target = NEUTRAL
            # Require a fresh neutral acknowledgement, even if an older neutral
            # ACK predates a currently in-flight non-neutral request.
            self.acknowledged = None
            self.condition.notify_all()
            while self.acknowledged != NEUTRAL and time.monotonic() < deadline:
                self.condition.wait(timeout=max(0, deadline - time.monotonic()))
            self.stopped = True
            self.condition.notify_all()
        self.thread.join(timeout=1.)
