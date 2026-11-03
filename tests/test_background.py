import unittest

import cv2
import numpy as np

from hand_effects.background import BackgroundEffect, handle_key, local_preview


class BackgroundTests(unittest.TestCase):
    def setUp(self):
        self.effect = BackgroundEffect(countdown=5., fade=1.)
        self.empty = np.full((120, 180, 3), 40, dtype=np.uint8)
        self.person = np.full((120, 180, 3), 200, dtype=np.uint8)

    def capture(self):
        self.effect.begin_capture(0.)
        self.effect.update(self.empty, 5.)
        self.assertTrue(self.effect.confirm())

    def test_capture_waits_for_deadline_and_requires_explicit_confirmation(self):
        effect = self.effect
        effect.begin_capture(10.)
        effect.update(self.person, 14.9)
        self.assertIsNone(effect.candidate)
        self.assertIn('1 s', effect.status(14.9))
        effect.update(self.empty, 15.)
        self.assertIsNone(effect.background)
        self.assertFalse(effect.toggle(16.))
        self.empty[:] = 5
        self.assertTrue((effect.candidate == 40).all())
        effect.update(self.person, 16.)
        self.assertTrue((effect.candidate == 40).all())
        self.assertTrue(effect.confirm())
        self.assertTrue((effect.background == 40).all())

    def test_effect_cannot_hide_without_reference(self):
        self.assertFalse(self.effect.toggle(0.))
        self.assertFalse(self.effect.confirm())
        np.testing.assert_array_equal(self.effect.compose(cv2, self.person, 5.), self.person)

    def test_fade_reverses_continuously_and_returns_to_live(self):
        self.capture()
        effect = self.effect
        effect.toggle(10.)
        np.testing.assert_array_equal(effect.compose(cv2, self.person, 10.), self.person)
        self.assertTrue((effect.compose(cv2, self.person, 10.5) == 120).all())
        effect.toggle(10.5)
        self.assertAlmostEqual(effect.strength(10.5), .5)
        self.assertAlmostEqual(effect.strength(11.), .25)
        np.testing.assert_array_equal(effect.compose(cv2, self.person, 11.5), self.person)
        effect.toggle(12.)
        np.testing.assert_array_equal(effect.compose(cv2, self.person, 13.), self.empty)
        effect.show_live()
        self.assertEqual(effect.strength(13.), 0.)
        self.assertIsNotNone(effect.background)

    def test_zero_fade_switches_immediately_without_dividing_by_zero(self):
        self.capture()
        self.effect.fade = 0.
        self.effect.toggle(10.)
        np.testing.assert_array_equal(self.effect.compose(cv2, self.person, 10.), self.empty)

    def test_mode_change_invalidates_reference_and_pending_capture(self):
        self.capture()
        self.effect.toggle(10.)
        changed = np.zeros((240, 320, 3), dtype=np.uint8)
        self.effect.update(changed, 12.)
        self.assertIsNone(self.effect.background)
        self.assertEqual(self.effect.strength(12.), 0.)
        self.effect.begin_capture(13.)
        self.effect.update(self.person, 14.)
        self.assertIsNone(self.effect.deadline)
        self.assertIsNone(self.effect.candidate)

    def test_recapture_and_cancel_do_not_restore_stale_background(self):
        self.capture()
        self.effect.toggle(10.)
        handle_key(self.effect, ord('b'), 11.)
        self.assertIsNone(self.effect.background)
        self.assertEqual(self.effect.strength(11.), 0.)
        handle_key(self.effect, ord('c'), 12.)
        self.effect.update(self.person, 20.)
        self.assertIsNone(self.effect.candidate)
        self.assertFalse(self.effect.toggle(21.))

    def test_local_candidate_preview_and_controls_do_not_modify_published_image(self):
        self.effect.begin_capture(0.)
        self.effect.update(self.empty, 5.)
        published = self.person.copy()
        preview = local_preview(cv2, self.effect, published, 6.)
        self.assertTrue((preview[-1] == 40).all())
        np.testing.assert_array_equal(published, self.person)
        self.assertTrue((self.effect.candidate == 40).all())


if __name__ == '__main__':
    unittest.main()
