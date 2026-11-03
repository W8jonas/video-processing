import json
from math import cos, radians, sin
from pathlib import Path
import tempfile
import unittest

from hand_libras.core import PoseLibrary, StableLabel, features, finger_states, pair_geometry


def hand():
    points = [(0.0, 0.0, 0.0)]
    for x in (-0.8, -0.4, 0.0, 0.4, 0.8):
        points.extend((x, -y, 0.0) for y in (1.0, 1.5, 2.0, 2.5))
    return points


def rotate(points, tilt=8):
    c, s = cos(radians(tilt)), sin(radians(tilt))
    return [(c * x - s * y, s * x + c * y, z) for x, y, z in points]


class GeometryTests(unittest.TestCase):
    def test_translation_scale_and_left_hand_invariance(self):
        points = hand()
        original = features(points, 'Right', 4 / 3)
        moved = [(x * 3 + 5, y * 3 + 2, z * 3 - 1) for x, y, z in points]
        mirrored = [(-x, y, z) for x, y, z in points]
        for actual in (features(moved, 'Right', 4 / 3), features(mirrored, 'Left', 4 / 3)):
            for a, b in zip(original, actual):
                self.assertAlmostEqual(a, b)

    def test_aspect_ratio_does_not_distort_pose(self):
        points = hand()
        wider = [(x / 2, y, z / 2) for x, y, z in points]
        self.assertEqual(features(points, 'Right'), features(wider, 'Right', 2))

    def test_camera_orientation_is_preserved(self):
        points = hand()
        rotated = [(-y, x, z) for x, y, z in points]
        self.assertNotEqual(features(points, 'Right'), features(rotated, 'Right'))

    def test_invalid_landmarks_are_rejected(self):
        for points in ([(0, 0, 0)] * 21, hand()[:20], [(float('nan'), 0, 0)] * 21):
            with self.assertRaises(ValueError):
                features(points, 'Right')

    def test_extended_and_curled_index(self):
        points = hand()
        self.assertTrue(finger_states(points)['indicador'])
        points[7] = (-0.4, -1.4, 0.2)
        points[8] = (-0.4, -1.1, 0.3)
        self.assertFalse(finger_states(points)['indicador'])

    def test_local_pair_cues_preserve_shape_under_camera_roll(self):
        original = features(hand(), 'Right')
        rolled = features(rotate(hand()), 'Right')
        for pair in (frozenset(('A', 'S')), frozenset(('U', 'V'))):
            for a, b in zip(pair_geometry(original, pair), pair_geometry(rolled, pair)):
                self.assertAlmostEqual(a, b)


class RecognitionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'poses.jsonl'
        self.library = PoseLibrary(self.path)
        self.a = (0.0,) * 63
        self.b = (0.4,) * 63

    def enroll(self):
        for _ in range(10):
            self.library.add('A', self.a, 'session-one')
            self.library.add('B', self.b, 'session-two')

    def test_no_prediction_until_two_classes_have_enough_examples(self):
        self.assertIsNone(self.library.predict(self.a).label)
        for _ in range(10):
            self.library.add('A', self.a, 's')
        self.assertIsNone(self.library.predict(self.a).label)
        for _ in range(9):
            self.library.add('B', self.b, 's')
        self.assertIsNone(self.library.predict(self.a).label)

    def test_prediction_round_trip_and_session_metadata(self):
        self.enroll()
        loaded = PoseLibrary(self.path)
        self.assertEqual(loaded.predict((0.01,) * 63).label, 'A')
        self.assertEqual(loaded.predict((0.39,) * 63).label, 'B')
        self.assertEqual(loaded.counts, {'A': 10, 'B': 10})
        self.assertEqual(json.loads(self.path.read_text().splitlines()[0])['session'], 'session-one')

    def test_unknown_and_ambiguous_poses_are_rejected(self):
        self.enroll()
        self.assertIsNone(self.library.predict((2.0,) * 63).label)
        self.assertIsNone(self.library.predict((0.2,) * 63).label)

    def test_thumb_cues_resolve_synthetic_orientation_distractor(self):
        # Synthetic geometry fixtures, not linguistically validated letter poses.
        original = hand()
        query = rotate(original)
        distractor = list(query)
        x, y, z = distractor[4]
        distractor[4] = (x + 1.0, y, z)
        for _ in range(10):
            self.library.add('A', features(original, 'Right'), 's')
            self.library.add('S', features(distractor, 'Right'), 's')
        before = self.path.read_bytes()
        prediction = self.library.predict(features(query, 'Right'))
        self.assertEqual(prediction.label, 'A')
        self.assertEqual(prediction.alternative, 'S')
        self.assertEqual(self.path.read_bytes(), before)

    def test_finger_spread_resolves_synthetic_orientation_distractor(self):
        original = hand()
        query = rotate(original)
        distractor = list(query)
        x, y, z = distractor[8]
        distractor[8] = (x - 0.4, y, z)
        x, y, z = distractor[12]
        distractor[12] = (x + 0.4, y, z)
        for _ in range(10):
            self.library.add('U', features(original, 'Right'), 's')
            self.library.add('V', features(distractor, 'Right'), 's')
        self.assertEqual(self.library.predict(features(query, 'Right')).label, 'U')

    def test_pair_refinement_keeps_identical_examples_ambiguous(self):
        vector = features(hand(), 'Right')
        for _ in range(10):
            self.library.add('U', vector, 's')
            self.library.add('V', vector, 's')
        prediction = self.library.predict(vector)
        self.assertIsNone(prediction.label)
        self.assertEqual(prediction.reason, 'ambiguous')

    def test_movement_labels_and_corrupt_data_are_rejected(self):
        with self.assertRaises(ValueError):
            self.library.add('J', self.a, 's')
        self.path.write_text('{broken}\n')
        with self.assertRaisesRegex(ValueError, 'linha 1'):
            PoseLibrary(self.path)

    def test_prediction_is_cleared_on_hand_loss_or_uncertainty(self):
        stable = StableLabel(size=4)
        for _ in range(3):
            self.assertIsNone(stable.update('A'))
        self.assertEqual(stable.update('A'), 'A')
        self.assertIsNone(stable.update(None))
        self.assertIsNone(stable.update('A'))
        stable.update('A')
        stable.update('A')
        self.assertIsNone(stable.update('B'))


if __name__ == '__main__':
    unittest.main()
