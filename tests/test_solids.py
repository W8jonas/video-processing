from collections import Counter
from math import dist, sqrt
import unittest

from hand_math.cube import CubePose, face_normal, rotated_vertices
from hand_math.solids import AutoRotation, SOLIDS, SOLID_STATS, Solid, measurements


class SolidTests(unittest.TestCase):
    def test_topology_and_euler_for_all_four_closed_meshes(self):
        for solid, expected in zip(SOLIDS, ((8, 12, 6), (4, 6, 4), (6, 12, 8), (12, 30, 20))):
            with self.subTest(solid=solid.name):
                stats = measurements(solid)
                self.assertEqual((stats['vertices'], stats['edges'], stats['faces']), expected)
                self.assertEqual(stats['euler'], 2)
                edge_faces = Counter(tuple(sorted((face[i], face[(i + 1) % len(face)])))
                                     for face in solid.faces for i in range(len(face)))
                self.assertTrue(all(count == 2 for count in edge_faces.values()))

    def test_all_meshes_have_equal_edges_and_shared_circumradius(self):
        for solid in SOLIDS:
            lengths = [dist(solid.vertices[a], solid.vertices[b]) for a, b in solid.edges]
            self.assertAlmostEqual(max(lengths), min(lengths))
            for vertex in solid.vertices:
                self.assertAlmostEqual(dist(vertex, (0, 0, 0)), sqrt(3) / 2)

    def test_all_faces_point_outwards(self):
        for solid in SOLIDS:
            for face in solid.faces:
                normal = face_normal(solid.vertices, face)
                center = tuple(sum(solid.vertices[i][j] for i in face) / len(face) for j in range(3))
                self.assertGreater(sum(a * b for a, b in zip(normal, center)), 0)

    def test_known_cube_tetrahedron_and_octahedron_measures(self):
        self.assertAlmostEqual(SOLID_STATS[0]['area'], 6)
        self.assertAlmostEqual(SOLID_STATS[0]['volume'], 1)
        self.assertAlmostEqual(SOLID_STATS[1]['area'], 2 * sqrt(3))
        self.assertAlmostEqual(SOLID_STATS[1]['volume'], 1 / 3)
        self.assertAlmostEqual(SOLID_STATS[2]['area'], 3 * sqrt(3))
        self.assertAlmostEqual(SOLID_STATS[2]['volume'], sqrt(3) / 2)

    def test_area_volume_and_edges_are_preserved_by_rigid_motion(self):
        pose = CubePose((0, 0), 1, .4, .8, -.7)
        for solid in SOLIDS:
            rotated = rotated_vertices(pose, solid.vertices)
            moved = tuple((x + 3, y - 2, z + 1) for x, y, z in rotated)
            new = measurements(Solid(solid.key, solid.name, moved, solid.faces))
            original = measurements(solid)
            self.assertAlmostEqual(new['area'], original['area'])
            self.assertAlmostEqual(new['volume'], original['volume'])
            for a, b in solid.edges:
                self.assertAlmostEqual(dist(moved[a], moved[b]), dist(solid.vertices[a], solid.vertices[b]))


class RotationTests(unittest.TestCase):
    def test_rotation_has_same_speed_at_different_frame_rates(self):
        slow, fast = AutoRotation(), AutoRotation()
        slow.enabled = fast.enabled = True
        slow.update(0)
        fast.update(0)
        for i in range(1, 11):
            slow.update(i / 10)
        for i in range(1, 21):
            fast.update(i / 20)
        self.assertAlmostEqual(slow.angle, fast.angle)
        self.assertAlmostEqual(slow.angle, .7)

    def test_disabled_frozen_and_missing_tracking_pause_rotation(self):
        rotation = AutoRotation()
        rotation.update(0)
        self.assertEqual(rotation.update(.1), 0)
        rotation.enabled = True
        before = rotation.update(.2)
        self.assertEqual(rotation.update(.3, frozen=True), before)
        self.assertEqual(rotation.update(.4, active=False), before)
        self.assertAlmostEqual(rotation.update(.5), before + .07)
        rotation.reset()
        self.assertEqual(rotation.angle, 0)
        self.assertFalse(rotation.enabled)
