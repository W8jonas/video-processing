from types import SimpleNamespace
from copy import deepcopy
import unittest
from unittest.mock import MagicMock, patch

from hand_math.app import run


def hands(left_open=False, right_open=False):
    result = []
    for x, raised in ((.2, left_open), (.8, right_open)):
        points = [(x, .5, 0)] * 21
        points[8], points[4] = (x, .2, 0), (x, .8, 0)
        points[9] = (x, .35, 0)
        result.append(dict(points=points, fingers={name: raised for name in ('medio', 'anelar', 'minimo')}))
    return result


class MathAppTests(unittest.TestCase):
    def test_pinches_change_shape_and_start_spin_without_losing_the_object(self):
        def pinch(index):
            result = deepcopy(hands())
            x = result[index]['points'][0][0]
            result[index]['points'][4] = (x, .35, 0)
            result[index]['points'][8] = (x + .015, .35, 0)
            return result

        sequence = [(0, hands()), (.3, hands()),
                    (.4, pinch(0)), (1.3, pinch(0)),
                    (1.4, hands()), (1.7, hands()),
                    (1.8, pinch(1)), (2.7, pinch(1)), (2.8, hands())]
        frame = SimpleNamespace(shape=(480, 640, 3), size=480 * 640 * 3)
        frame.copy = lambda: frame
        cv2, mp, np, detector = (MagicMock() for _ in range(4))
        cv2.VideoCapture.return_value.isOpened.return_value = True
        cv2.flip.return_value = frame
        cv2.waitKey.return_value = -1
        cv2.getWindowProperty.return_value = 1
        tick = [-1]

        def read():
            tick[0] += 1
            return True, frame

        cv2.VideoCapture.return_value.read.side_effect = read
        args = SimpleNamespace(camera=1, width=0, height=0, headless=False, max_frames=len(sequence), scene='cube')
        with patch('hand_math.app.time.monotonic', side_effect=lambda: sequence[max(0, tick[0])][0]), \
                patch('hand_math.app.describe', side_effect=[entry[1] for entry in sequence]), \
                patch('hand_math.app.draw_cube', return_value=frame) as draw, \
                patch('hand_math.app.panel', return_value=frame):
            report = run(cv2, mp, np, detector, args)
        self.assertEqual(report['portal_frames'], len(sequence))
        self.assertEqual(report['shape'], 'tetrahedron')
        self.assertTrue(report['auto_rotation'])
        self.assertEqual(draw.call_args_list[0].kwargs['mesh'].key, 'cube')
        self.assertEqual(draw.call_args.kwargs['mesh'].key, 'tetrahedron')
        self.assertGreater(draw.call_args.kwargs['spin'], 0)

    def test_gestures_change_filter_freeze_portal_and_toggle_grid_without_keys(self):
        self.exercise_controls('portal')

    def test_same_gestures_control_the_cube_without_keys(self):
        self.exercise_controls('cube')

    def exercise_controls(self, scene):
        sequence = [
            (0, hands()), (.3, hands()),
            (.4, hands(True)), (1.3, hands(True)),
            (1.4, hands()), (1.7, hands()),
            (1.8, hands(False, True)), (2.7, hands(False, True)),
            (2.8, []),  # Fixed portal remains visible without hands.
            (2.9, hands()), (3.2, hands()),
            (3.3, hands(True, True)), (4.2, hands(True, True)),
        ]
        frame = SimpleNamespace(shape=(480, 640, 3), size=480 * 640 * 3)
        frame.copy = lambda: frame
        cv2, mp, np, detector = (MagicMock() for _ in range(4))
        cv2.VideoCapture.return_value.isOpened.return_value = True
        cv2.flip.return_value = frame
        cv2.waitKey.return_value = -1
        cv2.getWindowProperty.return_value = 1
        tick = [-1]

        def read():
            tick[0] += 1
            return True, frame

        cv2.VideoCapture.return_value.read.side_effect = read
        args = SimpleNamespace(camera=1, width=0, height=0, headless=False, max_frames=len(sequence), scene=scene)
        with patch('hand_math.app.time.monotonic', side_effect=lambda: sequence[max(0, tick[0])][0]), \
                patch('hand_math.app.describe', side_effect=[entry[1] for entry in sequence]), \
                patch('hand_math.app.draw_cube' if scene == 'cube' else 'hand_math.app.draw_portal', return_value=frame) as draw, \
                patch('hand_math.app.panel', return_value=frame):
            report = run(cv2, mp, np, detector, args)
        self.assertEqual(report['portal_frames'], len(sequence))
        self.assertEqual(draw.call_args_list[0].args[4], 1)
        self.assertEqual(draw.call_args_list[3].args[4], 2)
        self.assertEqual(draw.call_args_list[8].args[3], draw.call_args_list[7].args[3])
        self.assertFalse(draw.call_args.args[5])
        cv2.VideoCapture.return_value.release.assert_called_once()


if __name__ == '__main__':
    unittest.main()
