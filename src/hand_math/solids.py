"""Regular convex solids sharing a circumradius and their virtual measurements."""

from dataclasses import dataclass
from functools import cached_property
from itertools import combinations
from math import dist, pi, sqrt

from .cube import FACES, VERTICES, face_normal


@dataclass(frozen=True)
class Solid:
    key: str
    name: str
    vertices: tuple
    faces: tuple

    @cached_property
    def edges(self):
        return tuple(sorted({tuple(sorted((face[i], face[(i + 1) % len(face)])))
                             for face in self.faces for i in range(len(face))}))


def triangular_faces(vertices):
    """For these regular triangular solids, every nearest-neighbor triple is a face."""
    edge_length = min(dist(a, b) for a, b in combinations(vertices, 2))
    faces = []
    for face in combinations(range(len(vertices)), 3):
        if not all(abs(dist(vertices[a], vertices[b]) - edge_length) < 1e-8 for a, b in combinations(face, 2)):
            continue
        normal = face_normal(vertices, face)
        center = tuple(sum(vertices[i][j] for i in face) / 3 for j in range(3))
        faces.append(face if sum(a * b for a, b in zip(normal, center)) > 0 else tuple(reversed(face)))
    return tuple(faces)


def make_solids():
    tetrahedron = ((.5, .5, .5), (.5, -.5, -.5), (-.5, .5, -.5), (-.5, -.5, .5))
    radius = sqrt(3) / 2
    octahedron = tuple(tuple(sign * radius if i == axis else 0 for i in range(3))
                       for axis in range(3) for sign in (-1, 1))
    phi = (1 + sqrt(5)) / 2
    raw = tuple(vertex for a in (-1, 1) for b in (-phi, phi)
                for vertex in ((0, a, b), (a, b, 0), (b, 0, a)))
    scale = radius / sqrt(1 + phi * phi)
    icosahedron = tuple(tuple(v * scale for v in p) for p in raw)
    return (Solid('cube', 'Cubo', VERTICES, FACES),
            Solid('tetrahedron', 'Tetraedro', tetrahedron, triangular_faces(tetrahedron)),
            Solid('octahedron', 'Octaedro', octahedron, triangular_faces(octahedron)),
            Solid('icosahedron', 'Icosaedro', icosahedron, triangular_faces(icosahedron)))


def measurements(solid):
    area, signed_volume = 0.0, 0.0
    for face in solid.faces:
        a = solid.vertices[face[0]]
        for i in range(1, len(face) - 1):
            b, c = solid.vertices[face[i]], solid.vertices[face[i + 1]]
            normal = face_normal(solid.vertices, (face[0], face[i], face[i + 1]))
            area += sqrt(sum(v * v for v in normal)) / 2
            cross = (b[1] * c[2] - b[2] * c[1], b[2] * c[0] - b[0] * c[2], b[0] * c[1] - b[1] * c[0])
            signed_volume += sum(x * y for x, y in zip(a, cross)) / 6
    return dict(vertices=len(solid.vertices), edges=len(solid.edges), faces=len(solid.faces),
                euler=len(solid.vertices) - len(solid.edges) + len(solid.faces),
                area=area, volume=abs(signed_volume))


SOLIDS = make_solids()
SOLID_STATS = tuple(measurements(solid) for solid in SOLIDS)


class AutoRotation:
    """A time-based angle that pauses during tracking loss or object freeze."""

    def __init__(self):
        self.enabled = False
        self.angle = 0.0
        self.previous = None

    def update(self, now, active=True, frozen=False):
        if self.previous is not None and self.enabled and active and not frozen:
            self.angle = (self.angle + max(0, min(.2, now - self.previous)) * .7) % (2 * pi)
        self.previous = now
        return self.angle

    def reset(self):
        self.enabled, self.angle, self.previous = False, 0.0, None
