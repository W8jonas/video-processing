from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from hand_math.drawing_app import run_drawing
from test_drawing import hands_with_counts


class DrawingAppTests(unittest.TestCase):
    def run_sequence(self, sequence, headless=True):
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
        args = SimpleNamespace(camera=1, width=0, height=0, headless=headless, max_frames=len(sequence))
        rendered_times = []
        def render(*args):
            rendered_times.append(sequence[tick[0]][0])
            return frame
        with patch('hand_math.drawing_app.time.monotonic', side_effect=lambda: sequence[max(0, tick[0])][0]), \
                patch('hand_math.drawing_app.describe', side_effect=[entry[1] for entry in sequence]), \
                patch('hand_math.drawing_app.draw_drawing', side_effect=render) as draw, \
                patch('hand_math.app.panel', return_value=frame):
            report = run_drawing(cv2, mp, np, detector, args)
        cv2.VideoCapture.return_value.release.assert_called_once()
        draw.rendered_times = rendered_times
        return report, draw, cv2

    def test_finger_counts_build_all_four_shapes_without_keyboard_commands(self):
        sequence = []
        for i, counts in enumerate(((2, 1), (2, 2), (3, 1), (3, 3))):
            sequence += [(i, hands_with_counts(*counts)), (i + .4, hands_with_counts(*counts))]
        report, _, cv2 = self.run_sequence(sequence)
        self.assertEqual(report['shapes'], ['cube', 'pyramid', 'rectangle', 'triangle'])
        self.assertEqual(report['drawing_frames'], 4)
        cv2.imshow.assert_not_called()

    def test_open_palms_freeze_and_unfreeze_without_triggering_shape_controls(self):
        normal, palms = hands_with_counts(2, 2), hands_with_counts(5, 5)
        sequence = ([(i / 20, normal) for i in range(13)]
                    + [(i / 20, palms) for i in range(13, 38)]
                    + [(2., [])]
                    + [(i / 20, normal) for i in range(44, 57)]
                    + [(i / 20, palms) for i in range(57, 83)]
                    + [(4.2, [])])
        report, draw, _ = self.run_sequence(sequence, headless=False)
        self.assertIn(2., draw.rendered_times)
        self.assertNotIn(4.2, draw.rendered_times)
        self.assertEqual(report['shapes'], ['rectangle'])
