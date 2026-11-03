from copy import deepcopy
from types import SimpleNamespace
import unittest

from hand_libras.core import finger_states
from hand_math.fingers import FingerTracker, attach_world_points, extension_scores


def world_hand(relaxed=False, folded=False):
    points = [(0., 0., 0.)] * 21
    points[1:5] = [(-.2, .3, 0), (-.55, .48, 0), (-.75, .75, .1), (-.92, .98, .15)]
    for start, x, base in ((5, -.3, 1.), (9, 0., 1.1), (13, .3, 1.), (17, .6, .9)):
        points[start] = (x, base, 0)
        if folded:
            points[start + 1:start + 4] = [(x, base + .35, .05), (x, base + .18, .22), (x, base + .04, .1)]
        elif relaxed:
            points[start + 1:start + 4] = [(x, base + .4, 0), (x, base + .7, .15), (x, base + .95, .3)]
        else:
            points[start + 1:start + 4] = [(x, base + .4, 0), (x, base + .7, 0), (x, base + 1., 0)]
    return points


def tracked_hand(points):
    return dict(points=[(.3, .5, 0)] * 21, world_points=points, fingers={})


class ExtensionTests(unittest.TestCase):
    def test_real_api_landmark_fields_are_attached_without_changing_existing_flags(self):
        original_flags = {'indicador': False}
        hand = dict(fingers=original_flags)
        points = world_hand(relaxed=True)
        result = SimpleNamespace(hand_world_landmarks=[[SimpleNamespace(x=x, y=y, z=z) for x, y, z in points]])
        attach_world_points([hand], result)
        self.assertEqual(hand['world_points'], tuple(points))
        self.assertIs(hand['fingers'], original_flags)

    def test_naturally_bent_fingers_are_accepted_where_old_strict_rule_fails(self):
        points = world_hand(relaxed=True)
        self.assertFalse(finger_states(points)['indicador'])
        scores = extension_scores(points)
        self.assertGreater(scores['indicador'], .64)
        self.assertGreater(scores['medio'], .64)
        self.assertGreater(scores['polegar'], .64)

    def test_folded_fingers_and_fingers_bent_back_at_the_knuckle_are_rejected(self):
        self.assertLess(extension_scores(world_hand(folded=True))['indicador'], .38)
        points = world_hand()
        points[6:9] = [(-.3, .7, .2), (-.3, .45, .4), (-.3, .2, .6)]
        self.assertLess(extension_scores(points)['indicador'], .38)

    def test_scores_are_invariant_to_scale_translation_and_rotation(self):
        points = world_hand(relaxed=True)
        transformed = [(-y * 3 + 8, x * 3 - 4, z * 3 + 2) for x, y, z in points]
        for name, score in extension_scores(points).items():
            self.assertAlmostEqual(score, extension_scores(transformed)[name])

    def test_bad_world_geometry_is_rejected(self):
        self.assertIsNone(extension_scores([(0, 0, 0)] * 21))
        self.assertIsNone(extension_scores(world_hand()[:20]))
        points = world_hand()
        points[4] = (float('nan'), 0, 0)
        self.assertIsNone(extension_scores(points))


class FingerTrackingTests(unittest.TestCase):
    def test_one_bad_frame_does_not_drop_an_extended_finger(self):
        tracker = FingerTracker()
        opened = tracked_hand(world_hand(relaxed=True))
        closed = tracked_hand(world_hand(folded=True))
        self.assertTrue(tracker.update([opened], 0)[0]['fingers']['indicador'])
        self.assertTrue(tracker.update([closed], .04)[0]['fingers']['indicador'])
        self.assertTrue(tracker.update([opened], .08)[0]['fingers']['indicador'])

    def test_sustained_closing_and_opening_are_detected(self):
        tracker = FingerTracker()
        opened, closed = tracked_hand(world_hand()), tracked_hand(world_hand(folded=True))
        tracker.update([opened], 0)
        for i in range(1, 9):
            result = tracker.update([closed], i * .04)
        self.assertFalse(result[0]['fingers']['indicador'])
        for i in range(9, 18):
            result = tracker.update([opened], i * .04)
        self.assertTrue(result[0]['fingers']['indicador'])

    def test_tracking_loss_resets_state_and_input_is_not_modified(self):
        tracker = FingerTracker()
        opened = tracked_hand(world_hand())
        original = deepcopy(opened)
        tracker.update([opened], 0)
        self.assertEqual(opened, original)
        self.assertEqual(tracker.update([], .04), [])
        result = tracker.update([tracked_hand(world_hand(folded=True))], .08)
        self.assertFalse(result[0]['fingers']['indicador'])
