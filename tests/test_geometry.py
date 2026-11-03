from math import isclose
import unittest

from hand_math.geometry import SmoothQuad, measurements, quad_from_hands, valid_quad

SQUARE = ((0, 0), (100, 0), (100, 100), (0, 100))


class GeometryTests(unittest.TestCase):
    def test_square_area_perimeter_angles(self):
        self.assertTrue(valid_quad(SQUARE))
        stats = measurements(SQUARE)
        self.assertEqual(stats['area'], 10000)
        self.assertEqual(stats['perimeter'], 400)
        self.assertTrue(all(isclose(a, 90) for a in stats['angles']))

    def test_nonrectangular_convex_quad_has_360_degree_angle_sum(self):
        points = ((10, 0), (150, 20), (120, 100), (0, 80))
        self.assertTrue(valid_quad(points))
        self.assertAlmostEqual(sum(measurements(points)['angles']), 360)

    def test_crossed_concave_tiny_and_nonfinite_quads_rejected(self):
        for points in (((0, 0), (100, 100), (100, 0), (0, 100)),
                       ((0, 0), (100, 0), (10, 10), (0, 100)),
                       ((0, 0), (1, 0), (1, 1), (0, 1)),
                       ((0, 0), (100, 0), (float('nan'), 100), (0, 100))):
            self.assertFalse(valid_quad(points))

    def test_hand_result_order_does_not_swap_corners(self):
        def hand(x):
            points = [(x, .5, 0)] * 21
            points[8], points[4] = (x, .2, 0), (x, .8, 0)
            return dict(points=points)
        left, right = hand(.2), hand(.8)
        expected = ((200, 100), (800, 100), (800, 400), (200, 400))
        self.assertEqual(quad_from_hands([right, left], 1000, 500), expected)
        self.assertIsNone(quad_from_hands([left], 1000, 500))

    def test_smoothing_is_time_based_and_clears_on_hand_loss(self):
        shifted = tuple((x + 100, y) for x, y in SQUARE)
        slow, fast = SmoothQuad(), SmoothQuad()
        slow.update(SQUARE, 0)
        fast.update(SQUARE, 0)
        a = slow.update(shifted, .1)
        fast.update(shifted, .05)
        b = fast.update(shifted, .1)
        self.assertAlmostEqual(a[0][0], b[0][0])
        self.assertIsNone(slow.update(None, .2))
        self.assertEqual(slow.update(shifted, .3), shifted)


if __name__ == '__main__':
    unittest.main()
