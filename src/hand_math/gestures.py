"""Held open-hand commands with deliberate activation and release to rearm."""

from math import dist


class PortalGestures:
    """Use spare fingers while thumb/index remain the portal corners.

    Hands are named by their position in the mirrored preview, not handedness.
    Holding a command fires once. Both hands must visibly return to neutral
    before another command; missing tracking never counts as a release.
    Two pinches with spare fingers curled request a 2D/3D scene change.
    """

    def __init__(self, hold_seconds=0.8, release_seconds=0.25):
        self.hold_seconds = hold_seconds
        self.release_seconds = release_seconds
        self.open = [False, False]
        self.pinched = [False, False]
        self.armed = False
        self.pending = None
        self.since = None
        self.release_since = None
        self.progress = 0.0

    def update(self, hands, now, allow_single_pinches=False):
        if len(hands) != 2:
            self.pending = self.since = self.release_since = None
            self.progress = 0.0
            self.open = [False, False]
            self.pinched = [False, False]
            return None
        ordered = sorted(hands, key=lambda hand: hand['points'][0][0])
        for i, hand in enumerate(ordered):
            count = sum(hand['fingers'][finger] for finger in ('medio', 'anelar', 'minimo'))
            # Hysteresis tolerates a single uncertain finger on transition.
            if count == 3:
                self.open[i] = True
            elif count <= 1:
                self.open[i] = False
            vector = hand.get('vector')
            points = ([vector[j:j + 3] for j in range(0, 63, 3)] if vector is not None else hand['points'])
            palm = dist(points[0], points[9])
            ratio = dist(points[4], points[8]) / palm if palm > 1e-6 else float('inf')
            if ratio < .22:
                self.pinched[i] = True
            elif ratio > .38:
                self.pinched[i] = False
        left, right = self.open
        pinch_command = None
        if not (left or right):
            if all(self.pinched):
                pinch_command = 'scene'
            elif allow_single_pinches and self.pinched[0]:
                pinch_command = 'shape'
            elif allow_single_pinches and self.pinched[1]:
                pinch_command = 'spin'
        if not left and not right and pinch_command is None:
            self.pending = self.since = None
            self.progress = 0.0
            if self.release_since is None:
                self.release_since = now
            if now - self.release_since >= self.release_seconds:
                self.armed = True
            return None
        self.release_since = None
        if not self.armed:
            self.pending = self.since = None
            self.progress = 0.0
            return None
        command = pinch_command or ('grid' if left and right else 'filter' if left else 'freeze')
        if command != self.pending:
            self.pending, self.since = command, now
        self.progress = min(1.0, max(0.0, (now - self.since) / self.hold_seconds))
        if now - self.since >= self.hold_seconds:
            self.armed = False
            self.pending = self.since = None
            self.progress = 0.0
            return command
        return None
