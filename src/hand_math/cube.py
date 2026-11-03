"""Rigid unit cube, virtual perspective camera, and hand-driven rotations.

The hand-derived controls are artistic parameters, not metric reconstruction.
All eight vertices undergo one rotation, preserving lengths and right angles.
"""

from dataclasses import dataclass, replace
from math import atan2, cos, dist, log, sin, sqrt

VERTICES = ((-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, -.5), (-.5, .5, -.5),
            (-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5))
FACES = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
         (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5))
EDGES = tuple(sorted({tuple(sorted((face[i], face[(i + 1) % 4])))
                      for face in FACES for i in range(4)}))
STYLES = ('Cristal', 'Neon', 'Solido', 'Aramado')
CAMERA_Z = 4.0


@dataclass(frozen=True)
class CubePose:
    center: tuple
    scale: float
    pitch: float
    yaw: float
    roll: float


def pose_from_quad(points):
    left = tuple((a + b) / 2 for a, b in zip(points[0], points[3]))
    right = tuple((a + b) / 2 for a, b in zip(points[1], points[2]))
    center = tuple(sum(p[i] for p in points) / 4 for i in range(2))
    left_grip, right_grip = dist(points[0], points[3]), dist(points[1], points[2])
    top, bottom = dist(points[0], points[1]), dist(points[3], points[2])
    # Ratio cues are invariant to global image translation and scale.
    yaw = max(-1.15, min(1.15, .55 + log(max(right_grip, 1) / max(left_grip, 1)) * 1.4))
    pitch = max(-1.05, min(1.05, -.35 + (top - bottom) / max(top + bottom, 1) * 3))
    roll = atan2(right[1] - left[1], right[0] - left[0])
    return CubePose(center, max(1, dist(left, right) * .62), pitch, yaw, roll)


def rotated_vertices(pose, local_vertices=VERTICES):
    cx, sx = cos(pose.pitch), sin(pose.pitch)
    cy, sy = cos(pose.yaw), sin(pose.yaw)
    cz, sz = cos(pose.roll), sin(pose.roll)
    result = []
    for x, y, z in local_vertices:
        y, z = cx * y - sx * z, sx * y + cx * z
        x, z = cy * x + sy * z, -sy * x + cy * z
        x, y = cz * x - sz * y, sz * x + cz * y
        result.append((x, y, z))
    return tuple(result)


def project(vertices, pose):
    result = []
    for x, y, z in vertices:
        depth = CAMERA_Z - z
        if depth <= 0:
            raise ValueError('Vertice atras da camera virtual')
        result.append((pose.center[0] + pose.scale * CAMERA_Z * x / depth,
                       pose.center[1] + pose.scale * CAMERA_Z * y / depth))
    return tuple(result)


def face_normal(vertices, face):
    a, b, c = (vertices[i] for i in face[:3])
    u, v = tuple(b[i] - a[i] for i in range(3)), tuple(c[i] - a[i] for i in range(3))
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def visible_faces(vertices, definitions=FACES):
    faces = []
    for i, face in enumerate(definitions):
        normal = face_normal(vertices, face)
        a = vertices[face[0]]
        if sum(normal[j] * (CAMERA_Z - a[j] if j == 2 else -a[j]) for j in range(3)) > 1e-8:
            faces.append((sum(vertices[k][2] for k in face) / len(face), i))
    return tuple(index for _, index in sorted(faces))


def draw_cube(cv2, np, frame, points, style, grid, mesh=None, spin=0):
    pose = pose_from_quad(points)
    pose = replace(pose, yaw=pose.yaw + spin)
    definitions = mesh.faces if mesh is not None else FACES
    edges = mesh.edges if mesh is not None else EDGES
    vertices = rotated_vertices(pose, mesh.vertices if mesh is not None else VERTICES)
    output = draw_mesh(cv2, np, frame, vertices, pose, definitions, edges, style, grid)
    # Light anchors make the connection between fingertips and cube explicit.
    for left, right in ((0, 3), (1, 2)):
        anchor = tuple(int((points[left][j] + points[right][j]) / 2) for j in range(2))
        cv2.circle(output, anchor, 7, (80, 250, 210), 2, cv2.LINE_AA)
    return output


def draw_mesh(cv2, np, frame, vertices, pose, definitions, edges, style, grid):
    """Render a supplied mesh; vertex positions need not come from a preset solid."""
    screen = project(vertices, pose)
    pixels = np.rint(screen).astype(np.int32)
    output = frame.copy()
    palette = ((245, 185, 55), (100, 245, 185), (245, 95, 190),
               (80, 200, 250), (225, 130, 90), (150, 240, 110))
    # Hidden edges are dashed; only front-facing faces participate in blending.
    visible = visible_faces(vertices, definitions)
    front_edges = {tuple(sorted((definitions[i][k], definitions[i][(k + 1) % len(definitions[i])])))
                   for i in visible for k in range(len(definitions[i]))}
    for a, b in edges:
        if (a, b) not in front_edges:
            for start in range(0, 12, 2):
                p = tuple(int(screen[a][j] + (screen[b][j] - screen[a][j]) * start / 12) for j in range(2))
                q = tuple(int(screen[a][j] + (screen[b][j] - screen[a][j]) * (start + 1) / 12) for j in range(2))
                cv2.line(output, p, q, (130, 140, 145), 1, cv2.LINE_AA)
    for index in visible:
        face = definitions[index]
        polygon = pixels[list(face)]
        normal = face_normal(vertices, face)
        norm = sqrt(sum(v * v for v in normal))
        light = .65 + .35 * abs(sum(a * b for a, b in zip(normal, (.3, -.4, .866))) / norm)
        color = tuple(int(c * light) for c in palette[index % len(palette)])
        if style != 3:
            # Blend only this face's screen bounds, rather than a full frame per face.
            x0, y0 = np.maximum(0, polygon.min(axis=0) - 2)
            x1, y1 = np.minimum((frame.shape[1], frame.shape[0]), polygon.max(axis=0) + 3)
            if x1 > x0 and y1 > y0:
                region = output[y0:y1, x0:x1]
                layer = region.copy()
                cv2.fillPoly(layer, [(polygon - (x0, y0)).astype(np.int32)], color, cv2.LINE_AA)
                alpha = (.28, .12, .88)[style]
                cv2.addWeighted(layer, alpha, region, 1 - alpha, 0, dst=region)
        # A freely constructed block can have a face whose image folds or
        # collapses. A homography on it can send grid lines outside the object.
        if (grid and len(face) == 4 and cv2.isContourConvex(polygon)
                and abs(cv2.contourArea(polygon)) > 5):
            unit = np.float32([[0, 0], [1, 0], [1, 1], [0, 1]])
            transform = cv2.getPerspectiveTransform(unit, np.float32([screen[k] for k in face]))
            for t in (.25, .5, .75):
                endpoints = np.float32([[[t, 0]], [[t, 1]], [[0, t]], [[1, t]]])
                p = np.rint(cv2.perspectiveTransform(endpoints, transform)).astype(np.int32).reshape(4, 2)
                cv2.line(output, tuple(p[0]), tuple(p[1]), color, 1, cv2.LINE_AA)
                cv2.line(output, tuple(p[2]), tuple(p[3]), color, 1, cv2.LINE_AA)
        elif grid and len(face) == 3:
            for corner in range(3):
                a, b, c = (vertices[face[(corner + i) % 3]] for i in range(3))
                for t in (.25, .5, .75):
                    endpoints = tuple(tuple((1 - t) * a[j] + t * end[j] for j in range(3)) for end in (b, c))
                    p, q = (tuple(int(round(v)) for v in point) for point in project(endpoints, pose))
                    cv2.line(output, p, q, color, 1, cv2.LINE_AA)
        edge_color = (100, 255, 230) if style == 1 else color
        cv2.polylines(output, [polygon], True, edge_color, 3 if style == 1 else 2, cv2.LINE_AA)
    for point in pixels:
        cv2.circle(output, tuple(point), 4, (200, 255, 245), -1, cv2.LINE_AA)
    return output
