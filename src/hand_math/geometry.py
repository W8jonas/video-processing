"""Screen-space quadrilateral geometry, independent of camera libraries."""

from math import acos, degrees, dist, exp, isfinite


def area(points):
    return abs(sum(a[0] * b[1] - b[0] * a[1]
                   for a, b in zip(points, points[1:] + points[:1]))) / 2


def valid_quad(points, min_area=600):
    if len(points) != 4 or any(len(p) != 2 or not all(isfinite(v) for v in p) for p in points):
        return False
    crosses = []
    for i in range(4):
        a, b, c = points[i], points[(i + 1) % 4], points[(i + 2) % 4]
        crosses.append((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]))
    return (all(v > 0 for v in crosses) or all(v < 0 for v in crosses)) and area(points) >= min_area


def quad_from_hands(hands, width, height):
    if len(hands) != 2:
        return None
    left, right = sorted(hands, key=lambda h: h['points'][0][0])
    # Fixed finger identity: left index, right index, right thumb, left thumb.
    points = tuple((hand['points'][tip][0] * width, hand['points'][tip][1] * height)
                   for hand, tip in ((left, 8), (right, 8), (right, 4), (left, 4)))
    return points if valid_quad(points) else None


def measurements(points):
    sides = [dist(points[i], points[(i + 1) % 4]) for i in range(4)]
    angles = []
    for i, vertex in enumerate(points):
        a, b = points[(i - 1) % 4], points[(i + 1) % 4]
        u = (a[0] - vertex[0], a[1] - vertex[1])
        v = (b[0] - vertex[0], b[1] - vertex[1])
        norm = dist(a, vertex) * dist(b, vertex)
        if norm < 1e-9:
            raise ValueError('Aresta degenerada')
        angles.append(degrees(acos(max(-1, min(1, (u[0] * v[0] + u[1] * v[1]) / norm)))))
    return dict(area=area(points), perimeter=sum(sides), sides=sides, angles=angles)


class SmoothQuad:
    """Time-based smoothing with immediate reset on invalid or missing hands."""

    def __init__(self, tau=0.08):
        self.tau = tau
        self.points = None
        self.time = None

    def update(self, points, now):
        if points is None:
            self.points = self.time = None
            return None
        if self.points is None:
            self.points = points
        else:
            alpha = 1 - exp(-max(0, now - self.time) / self.tau)
            smoothed = tuple(tuple(a + alpha * (b - a) for a, b in zip(old, new))
                             for old, new in zip(self.points, points))
            self.points = smoothed if valid_quad(smoothed) else points
        self.time = now
        return self.points
