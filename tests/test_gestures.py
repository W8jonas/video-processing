import unittest

from hand_math.gestures import PortalGestures


def hand(x, raised=0):
    return dict(points=[(x, 0, 0)] * 21,
                fingers={name: i < raised for i, name in enumerate(('medio', 'anelar', 'minimo'))})


def pinched_hand(x):
    result = hand(x)
    result['points'] = list(result['points'])
    result['points'][9] = (x, 1, 0)
    result['points'][4] = (x, .3, 0)
    result['points'][8] = (x + .1, .3, 0)
    return result


class PortalGestureTests(unittest.TestCase):
    def setUp(self):
        self.gestures = PortalGestures()
        self.neutral = [hand(.2), hand(.8)]
        self.left = [hand(.2, 3), hand(.8)]
        self.right = [hand(.2), hand(.8, 3)]
        self.both = [hand(.2, 3), hand(.8, 3)]

    def arm(self, start=0):
        self.gestures.update(self.neutral, start)
        self.gestures.update(self.neutral, start + .3)
        self.assertTrue(self.gestures.armed)

    def test_open_hands_at_start_do_not_trigger_accidental_command(self):
        self.assertIsNone(self.gestures.update(self.both, 0))
        self.assertIsNone(self.gestures.update(self.both, 2))

    def test_screen_left_hand_changes_filter_once_until_release(self):
        self.arm()
        self.assertIsNone(self.gestures.update(self.left, 1))
        self.assertIsNone(self.gestures.update(self.left, 1.5))
        self.assertEqual(self.gestures.update(self.left, 1.9), 'filter')
        self.assertIsNone(self.gestures.update(self.left, 5))
        self.arm(6)
        self.gestures.update(self.left, 7)
        self.assertEqual(self.gestures.update(self.left, 8), 'filter')

    def test_right_and_both_commands_use_screen_position_not_result_order(self):
        for hands, expected in ((self.right, 'freeze'), (self.both, 'grid')):
            self.gestures = PortalGestures()
            self.arm()
            self.gestures.update(list(reversed(hands)), 1)
            self.assertEqual(self.gestures.update(hands, 2), expected)

    def test_both_hands_override_pending_single_hand_without_firing_it(self):
        self.arm()
        self.gestures.update(self.left, 1)
        self.assertIsNone(self.gestures.update(self.both, 1.4))
        self.assertIsNone(self.gestures.update(self.both, 1.9))
        self.assertEqual(self.gestures.update(self.both, 2.3), 'grid')

    def test_tracking_loss_cancels_hold_and_does_not_rearm(self):
        self.arm()
        self.gestures.update(self.left, 1)
        self.assertIsNone(self.gestures.update([], 1.5))
        self.assertIsNone(self.gestures.update(self.left, 2))
        self.assertEqual(self.gestures.update(self.left, 3), 'filter')
        self.gestures.update([], 4)
        self.assertIsNone(self.gestures.update(self.left, 5))
        self.assertIsNone(self.gestures.update(self.left, 6))

    def test_one_uncertain_finger_does_not_interrupt_hold(self):
        self.arm()
        self.gestures.update(self.left, 1)
        self.gestures.update([hand(.2, 2), hand(.8)], 1.5)
        self.assertEqual(self.gestures.update(self.left, 1.9), 'filter')

    def test_brief_gesture_is_cancelled_by_return_to_neutral(self):
        self.arm()
        self.gestures.update(self.left, 1)
        self.gestures.update(self.neutral, 1.4)
        self.gestures.update(self.left, 1.5)
        self.assertIsNone(self.gestures.update(self.left, 1.9))

    def test_two_pinches_switch_scene_once_and_require_release(self):
        self.arm()
        pinches = [pinched_hand(.2), pinched_hand(.8)]
        self.assertIsNone(self.gestures.update(pinches[:1], .5))
        self.assertIsNone(self.gestures.update(pinches, 1))
        self.assertEqual(self.gestures.update(pinches, 2), 'scene')
        self.assertIsNone(self.gestures.update(pinches, 3))
        self.assertIsNone(self.gestures.update([], 4))
        self.assertIsNone(self.gestures.update(pinches, 5))
        self.assertIsNone(self.gestures.update(pinches, 6))
        self.arm(7)
        self.gestures.update(pinches, 8)
        self.assertEqual(self.gestures.update(pinches, 9), 'scene')

    def test_single_pinches_select_shape_or_spin_only_when_enabled(self):
        for poses, expected in (([pinched_hand(.2), hand(.8)], 'shape'),
                                ([hand(.2), pinched_hand(.8)], 'spin')):
            for enabled in (False, True):
                self.gestures = PortalGestures()
                self.arm()
                self.gestures.update(poses, 1, allow_single_pinches=enabled)
                self.assertEqual(self.gestures.update(poses, 2, allow_single_pinches=enabled), expected if enabled else None)
                self.assertIsNone(self.gestures.update(poses, 3, allow_single_pinches=enabled))

    def test_double_pinch_takes_priority_over_pending_shape(self):
        self.arm()
        left = [pinched_hand(.2), hand(.8)]
        both = [pinched_hand(.2), pinched_hand(.8)]
        self.gestures.update(left, 1, allow_single_pinches=True)
        self.assertIsNone(self.gestures.update(both, 1.3, allow_single_pinches=True))
        self.assertIsNone(self.gestures.update(both, 1.9, allow_single_pinches=True))
        self.assertEqual(self.gestures.update(both, 2.2, allow_single_pinches=True), 'scene')


if __name__ == '__main__':
    unittest.main()
