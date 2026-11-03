from math import dist, isfinite, pi
import unittest

from hand_math.cube import CubePose, EDGES, FACES, face_normal, pose_from_quad, project, rotated_vertices, visible_faces

QUAD = ((100, 100), (500, 100), (500, 350), (100, 350))


class CubeTests(unittest.TestCase):
    def test_rigid_rotation_preserves_all_twelve_unit_edges(self):
        self.assertEqual(len(EDGES), 12)
        self.assertEqual(len(FACES), 6)
        for angles in ((0, 0, 0), (.4, .7, -.2), (-1, 1.15, pi)):
            vertices = rotated_vertices(CubePose((320, 240), 200, *angles))
            for a, b in EDGES:
                self.assertAlmostEqual(dist(vertices[a], vertices[b]), 1)
            for face in FACES:
                a, b, c = (vertices[k] for k in face[:3])
                self.assertAlmostEqual(sum((a[j] - b[j]) * (c[j] - b[j]) for j in range(3)), 0)

    def test_frontal_cube_has_one_visible_face_and_front_looks_larger(self):
        pose = CubePose((320, 240), 200, 0, 0, 0)
        vertices = rotated_vertices(pose)
        self.assertEqual(visible_faces(vertices), (1,))
        screen = project(vertices, pose)
        self.assertGreater(dist(screen[4], screen[5]), dist(screen[0], screen[1]))

    def test_rotated_cube_has_three_visible_faces_sorted_far_to_near(self):
        pose = pose_from_quad(QUAD)
        vertices = rotated_vertices(pose)
        faces = visible_faces(vertices)
        self.assertEqual(len(faces), 3)
        depths = [sum(vertices[k][2] for k in FACES[i]) / 4 for i in faces]
        self.assertEqual(depths, sorted(depths))

    def test_face_normals_point_outward(self):
        vertices = rotated_vertices(pose_from_quad(QUAD))
        for face in FACES:
            normal = face_normal(vertices, face)
            center = tuple(sum(vertices[k][j] for k in face) / 4 for j in range(3))
            self.assertGreater(sum(a * b for a, b in zip(normal, center)), 0)

    def test_image_translation_and_scale_preserve_orientation(self):
        original = pose_from_quad(QUAD)
        moved = pose_from_quad(tuple((x * 2 + 30, y * 2 - 20) for x, y in QUAD))
        self.assertEqual(original.pitch, moved.pitch)
        self.assertEqual(original.yaw, moved.yaw)
        self.assertEqual(original.roll, moved.roll)
        self.assertAlmostEqual(original.scale * 2, moved.scale)
        self.assertEqual(moved.center, (original.center[0] * 2 + 30, original.center[1] * 2 - 20))

    def test_hand_cues_control_distinct_rotation_axes(self):
        base = pose_from_quad(QUAD)
        tilted = pose_from_quad(((100, 100), (500, 200), (500, 450), (100, 350)))
        unequal_grips = pose_from_quad(((100, 100), (500, 50), (500, 400), (100, 350)))
        unequal_edges = pose_from_quad(((50, 100), (550, 100), (500, 350), (100, 350)))
        self.assertGreater(tilted.roll, base.roll)
        self.assertGreater(unequal_grips.yaw, base.yaw)
        self.assertGreater(unequal_edges.pitch, base.pitch)

    def test_projection_is_finite_at_control_limits_and_rejects_near_plane(self):
        for pitch in (-1.05, 1.05):
            for yaw in (-1.15, 1.15):
                pose = CubePose((0, 0), 100, pitch, yaw, 2.5)
                self.assertTrue(all(isfinite(v) for p in project(rotated_vertices(pose), pose) for v in p))
        with self.assertRaises(ValueError):
            project(((0, 0, 4),), pose)
