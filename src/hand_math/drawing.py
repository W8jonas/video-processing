"""Build screen-anchored geometry from the actual extended fingertips."""

from dataclasses import dataclass, replace
from math import exp, isfinite

from .cube import CAMERA_Z, CubePose, face_normal
from .solids import Solid

TIPS = (('polegar', 4), ('indicador', 8), ('medio', 12), ('anelar', 16), ('minimo', 20))
NAMES = {'triangle': 'Triangulo', 'rectangle': 'Retangulo / quadrilatero',
         'pyramid': 'Piramide triangular', 'cube': 'Cubo livre'}
KINDS = {(1, 2): 'triangle', (2, 2): 'rectangle', (1, 3): 'pyramid', (3, 3): 'cube'}


@dataclass(frozen=True)
class Fingertip:
    side: int
    finger: str
    point: tuple

    @property
    def identity(self):
        return self.side, self.finger


@dataclass(frozen=True)
class DrawingInput:
    kind: str
    counts: tuple
    tips: tuple

    @property
    def identity(self):
        return self.kind, tuple(tip.identity for tip in self.tips)


@dataclass(frozen=True)
class Drawing:
    source: DrawingInput
    mesh: Solid
    pose: CubePose
    screen: tuple
    # None identifies a computed corner, not a detected fingertip.
    bindings: tuple


def active_tips(hands, width, height):
    if len(hands) != 2:
        return (), ()
    counts, tips = [], []
    for side, hand in enumerate(sorted(hands, key=lambda hand: hand['points'][0][0])):
        fingers = [(name, index) for name, index in TIPS if hand['fingers'].get(name, False)]
        counts.append(len(fingers))
        for name, index in fingers:
            x, y, _ = hand['points'][index]
            tips.append(Fingertip(side, name, (x * width, y * height)))
    return tuple(counts), tuple(tips)


def input_from_hands(hands, width, height, profile='auto'):
    if profile != 'auto':
        if len(hands) != 2:
            return None
        profiles = {'triangle': (2, 1), 'rectangle': (2, 2), 'pyramid': (3, 1), 'cube': (3, 3)}
        counts = profiles[profile]
        selected = []
        for side, hand in enumerate(sorted(hands, key=lambda hand: hand['points'][0][0])):
            fingers = (('indicador', 8),) if counts[side] == 1 else TIPS[:counts[side]]
            for name, index in fingers:
                x, y, _ = hand['points'][index]
                selected.append(Fingertip(side, name, (x * width, y * height)))
        return DrawingInput(profile, counts, tuple(selected))
    counts, tips = active_tips(hands, width, height)
    kind = KINDS.get(tuple(sorted(counts)))
    return DrawingInput(kind, counts, tips) if kind else None


def hull_order(points):
    """Convex hull indexes; reject coincident, collinear or interior anchors."""
    def cross(a, b, c):
        return ((points[b][0] - points[a][0]) * (points[c][1] - points[a][1])
                - (points[b][1] - points[a][1]) * (points[c][0] - points[a][0]))
    ordered = sorted(range(len(points)), key=lambda i: points[i])
    if len({points[i] for i in ordered}) != len(points):
        return None
    lower, upper = [], []
    for index in ordered:
        while len(lower) > 1 and cross(lower[-2], lower[-1], index) <= 0:
            lower.pop()
        lower.append(index)
    for index in reversed(ordered):
        while len(upper) > 1 and cross(upper[-2], upper[-1], index) <= 0:
            upper.pop()
        upper.append(index)
    hull = tuple(lower[:-1] + upper[:-1])
    if len(hull) != len(points):
        return None
    area = abs(sum(points[a][0] * points[b][1] - points[b][0] * points[a][1]
                   for a, b in zip(hull, hull[1:] + hull[:1]))) / 2
    return hull if area >= 120 else None


def _complete_face(tips):
    # The middle point in the finger chain is the shared corner. For the usual
    # thumb/index/middle pose this is index, with thumb and middle adjacent.
    a, origin, b = tips
    inferred = tuple(a.point[i] + b.point[i] - origin.point[i] for i in range(2))
    points = (origin.point, a.point, inferred, b.point)
    bindings = (origin, a, None, b)
    order = hull_order(points)
    if order is None:
        return None
    return tuple(points[i] for i in order), tuple(bindings[i] for i in order)


def build_drawing(source):
    tips = source.tips
    if any(not all(isfinite(v) for v in tip.point) for tip in tips):
        return None
    if source.kind in ('triangle', 'rectangle'):
        points = tuple(tip.point for tip in tips)
        order = hull_order(points)
        if order is None:
            return None
        screen = tuple(points[i] for i in order)
        bindings = tuple(tips[i] for i in order)
        faces, depths = (tuple(range(len(points))),), (0,) * len(points)
    elif source.kind == 'pyramid':
        base_side = source.counts.index(3)
        base = tuple(tip for tip in tips if tip.side == base_side)
        apex = next(tip for tip in tips if tip.side != base_side)
        order = hull_order(tuple(tip.point for tip in base))
        if order is None:
            return None
        bindings = tuple(base[i] for i in order) + (apex,)
        screen = tuple(tip.point for tip in bindings)
        faces = ((0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3))
        depths = (-.35, -.35, -.35, .35)
    else:
        first = _complete_face(tuple(tip for tip in tips if tip.side == 0))
        second = _complete_face(tuple(tip for tip in tips if tip.side == 1))
        if first is None or second is None:
            return None
        a_points, a_bindings = first
        b_points, b_bindings = second
        # Match equal cyclic winding, minimizing differences around each center.
        ca = tuple(sum(p[j] for p in a_points) / 4 for j in range(2))
        cb = tuple(sum(p[j] for p in b_points) / 4 for j in range(2))
        shift = min(range(4), key=lambda k: sum(
            ((a_points[i][j] - ca[j]) - (b_points[(i + k) % 4][j] - cb[j])) ** 2
            for i in range(4) for j in range(2)))
        b_points = b_points[shift:] + b_points[:shift]
        b_bindings = b_bindings[shift:] + b_bindings[:shift]
        screen, bindings = a_points + b_points, a_bindings + b_bindings
        faces = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                 (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
        depths = (-.4,) * 4 + (.4,) * 4
    center = tuple(sum(p[j] for p in screen) / len(screen) for j in range(2))
    scale = max(max(p[j] for p in screen) - min(p[j] for p in screen) for j in range(2))
    if scale < 1:
        return None
    pose = CubePose(center, scale, 0, 0, 0)
    # Inverse perspective: applying project() maps every measured vertex back
    # onto its fingertip. The assigned depth is virtual, not cross-hand MP z.
    vertices = tuple(((p[0] - center[0]) * (CAMERA_Z - z) / (scale * CAMERA_Z),
                      (p[1] - center[1]) * (CAMERA_Z - z) / (scale * CAMERA_Z), z)
                     for p, z in zip(screen, depths))
    if source.kind in ('pyramid', 'cube'):
        centroid = tuple(sum(v[j] for v in vertices) / len(vertices) for j in range(3))
        oriented = []
        for face in faces:
            normal = face_normal(vertices, face)
            direction = tuple(sum(vertices[i][j] for i in face) / len(face) - centroid[j] for j in range(3))
            oriented.append(face if sum(a * b for a, b in zip(normal, direction)) >= 0 else tuple(reversed(face)))
        faces = tuple(oriented)
    mesh = Solid(source.kind, NAMES[source.kind], vertices, faces)
    return Drawing(source, mesh, pose, screen, bindings)


class FingerDrawing:
    def __init__(self, settle_seconds=.3, tau=.055, profile='auto'):
        self.settle_seconds, self.tau = settle_seconds, tau
        self.profile = profile
        self.pending = self.since = self.source = self.previous = None
        self.progress = 0.0
        self.status = 'two_hands'

    def reset(self):
        self.pending = self.since = self.source = self.previous = None
        self.progress = 0.0
        self.status = 'two_hands'

    def update(self, hands, width, height, now):
        raw = input_from_hands(hands, width, height, self.profile)
        if raw is None:
            self.reset()
            self.status = 'two_hands' if len(hands) != 2 else 'unsupported_counts'
            return None
        if build_drawing(raw) is None:
            self.reset()
            self.status = 'degenerate_geometry'
            return None
        if raw.identity != self.pending:
            self.pending, self.since = raw.identity, now
            self.source, self.previous = None, None
        self.progress = min(1, (now - self.since) / self.settle_seconds)
        if now - self.since < self.settle_seconds:
            self.status = 'settling'
            return None
        if self.source is None:
            smoothed = raw
        else:
            alpha = 1 - exp(-max(0, now - self.previous) / self.tau)
            tips = tuple(replace(new, point=tuple(a + alpha * (b - a) for a, b in zip(old.point, new.point)))
                         for old, new in zip(self.source.tips, raw.tips))
            smoothed = replace(raw, tips=tips)
        drawing = build_drawing(smoothed)
        if drawing is None:
            smoothed, drawing = raw, build_drawing(raw)
        self.source, self.previous = smoothed, now
        self.status = 'tracking'
        return drawing


class DrawingCommands:
    """Closed fists cycle material; open palms toggle freeze, once per hold."""

    def __init__(self):
        self.pending = self.since = self.release_since = None
        self.armed = False
        self.progress = 0.0

    def update(self, counts, now):
        if len(counts) != 2:
            self.pending = self.since = self.release_since = None
            self.progress = 0.0
            return None
        command = 'style' if counts == (0, 0) else 'freeze' if counts == (5, 5) else None
        if command is None:
            self.pending = self.since = None
            self.progress = 0.0
            if self.release_since is None:
                self.release_since = now
            if now - self.release_since >= .25:
                self.armed = True
            return None
        self.release_since = None
        if not self.armed:
            return None
        if command != self.pending:
            self.pending, self.since = command, now
        self.progress = min(1, (now - self.since) / .8)
        if now - self.since >= .8:
            self.pending = self.since = None
            self.armed, self.progress = False, 0.0
            return command
        return None
