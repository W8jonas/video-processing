from contextlib import contextmanager
from io import StringIO
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from hand_effects.app import annotate, main, parser, run
from hand_effects.output import fit_frame, open_virtual, test_pattern
from hand_effects.background import BackgroundEffect


class OutputTests(unittest.TestCase):
    def test_letterbox_preserves_proportions_and_bgr_without_mutating_source(self):
        source = np.full((480, 640, 3), (10, 20, 230), dtype=np.uint8)
        output = fit_frame(cv2, source, 1280, 720)
        self.assertEqual(output.shape, (720, 1280, 3))
        self.assertTrue((output[:, :160] == 0).all())
        self.assertTrue((output[:, 160:1120] == (10, 20, 230)).all())
        self.assertTrue((output[:, 1120:] == 0).all())
        output[:] = 0
        self.assertTrue((source == (10, 20, 230)).all())

    def test_pattern_has_correct_bgr_primaries_and_moving_counter(self):
        first = test_pattern(cv2, 960, 540, 1)
        second = test_pattern(cv2, 960, 540, 2)
        self.assertEqual(first[0, 0].tolist(), [0, 0, 255])
        self.assertEqual(first[0, 400].tolist(), [0, 255, 0])
        self.assertEqual(first[0, 800].tolist(), [255, 0, 0])
        self.assertFalse(np.array_equal(first, second))

    def test_virtual_backend_explicitly_requests_bgr(self):
        module = SimpleNamespace(Camera=MagicMock(), PixelFormat=SimpleNamespace(BGR='BGR'))
        with patch.dict(sys.modules, pyvirtualcam=module):
            open_virtual(1280, 720, 30)
        module.Camera.assert_called_once_with(width=1280, height=720, fps=30, fmt='BGR', backend='obs')

    def test_backend_failure_explains_setup_and_preview_fallback(self):
        module = SimpleNamespace(Camera=MagicMock(side_effect=RuntimeError('no device')),
                                 PixelFormat=SimpleNamespace(BGR='BGR'))
        with patch.dict(sys.modules, pyvirtualcam=module):
            with self.assertRaisesRegex(RuntimeError, '--preview-only'):
                open_virtual(1280, 720, 30)

    def test_independent_finger_states_highlight_index_and_little_finger(self):
        drawing = MagicMock()
        hand = dict(points=[(.5, .5, 0)] * 21, fingers=dict(indicador=True, medio=False,
                    anelar=False, minimo=True))
        with patch('hand_effects.app.draw_hands'):
            annotate(drawing, np.zeros((480, 640, 3), dtype=np.uint8), [hand])
        colors = [call.args[3] for call in drawing.circle.call_args_list]
        self.assertEqual(colors, [(70, 240, 110), (140, 140, 140), (140, 140, 140), (70, 240, 110)])


class PipelineTests(unittest.TestCase):
    def test_confirmed_background_replaces_output_but_inference_keeps_reading_live_camera(self):
        from mediapipe.tasks.python import vision
        camera = MagicMock()
        camera.read.side_effect = [(True, np.full((240, 320, 3), value, dtype=np.uint8))
                                  for value in (20, 30, 40)]
        detector = MagicMock()
        detector.__enter__.return_value = detector
        detector.detect_for_video.return_value = SimpleNamespace(
            hand_landmarks=[], hand_world_landmarks=[], handedness=[])
        sink = MagicMock()
        sink.__enter__.return_value = sink
        effect = BackgroundEffect(fade=0.)
        effect.begin_capture(-10.)
        args = parser().parse_args(['--max-frames', '3'])
        def paint(cv, frame, hands):
            frame[:] = 200
        with patch.object(cv2, 'VideoCapture', return_value=camera), \
                patch.object(vision.HandLandmarker, 'create_from_options', return_value=detector), \
                patch('hand_effects.app.open_virtual', return_value=sink), \
                patch('hand_effects.app.BackgroundEffect', return_value=effect), \
                patch('hand_effects.app.annotate', side_effect=paint), \
                patch.object(cv2, 'imshow'), patch.object(cv2, 'destroyAllWindows'), \
                patch.object(cv2, 'getWindowProperty', return_value=1), \
                patch.object(cv2, 'waitKey', side_effect=[13, ord('i'), ord('q')]):
            self.assertEqual(run(args)['frames'], 3)
        outputs = [call.args[0] for call in sink.send.call_args_list]
        self.assertEqual([frame[360, 640, 0] for frame in outputs], [200, 200, 20])
        inferred = [call.args[0].numpy_view()[0, 0, 0] for call in detector.detect_for_video.call_args_list]
        self.assertEqual(inferred, [20, 30, 40])
        self.assertTrue((effect.background == 20).all())
        camera.release.assert_called_once()

    def test_camera_inference_reads_unpainted_frames_and_resources_close_on_capture_loss(self):
        from mediapipe.tasks.python import vision
        raw = np.full((240, 320, 3), 20, dtype=np.uint8)
        camera = MagicMock()
        camera.read.side_effect = [(True, raw), *[(False, None)] * 20]
        detector = MagicMock()
        detector.__enter__.return_value = detector
        detector.detect_for_video.return_value = SimpleNamespace(
            hand_landmarks=[], hand_world_landmarks=[], handedness=[])
        sink = MagicMock()
        sink.__enter__.return_value = sink
        args = parser().parse_args(['--headless'])
        def paint(cv, frame, hands):
            frame[:] = 200
        with patch.object(cv2, 'VideoCapture', return_value=camera), \
                patch.object(vision.HandLandmarker, 'create_from_options', return_value=detector), \
                patch('hand_effects.app.open_virtual', return_value=sink), \
                patch('hand_effects.app.annotate', side_effect=paint), \
                patch('hand_effects.app.time.sleep'):
            with self.assertRaisesRegex(RuntimeError, '20 falhas'):
                run(args)
        image = detector.detect_for_video.call_args.args[0].numpy_view()
        self.assertTrue((image[:, :, :3] == 20).all())
        self.assertTrue((raw == 20).all())
        self.assertEqual(sink.send.call_count, 1)
        camera.release.assert_called_once()
        detector.__exit__.assert_called_once()
        sink.__exit__.assert_called_once()

    def test_test_pattern_publishes_fixed_frames_without_opening_webcam(self):
        sink = MagicMock(device='test OBS')
        @contextmanager
        def virtual(*args):
            try:
                yield sink
            finally:
                sink.close()
        args = parser().parse_args(['--test-pattern', '--headless', '--max-frames', '3'])
        with patch('hand_effects.app.open_virtual', virtual), patch.object(cv2, 'VideoCapture') as capture:
            report = run(args)
        capture.assert_not_called()
        self.assertEqual(report['frames'], 3)
        self.assertEqual(sink.send.call_count, 3)
        self.assertEqual(sink.send.call_args.args[0].shape, (720, 1280, 3))
        sink.close.assert_called_once()

    def test_virtual_sink_is_released_if_publishing_fails(self):
        sink = MagicMock()
        sink.__enter__.return_value = sink
        sink.send.side_effect = RuntimeError('lost virtual device')
        args = parser().parse_args(['--test-pattern', '--headless', '--max-frames', '1'])
        with patch('hand_effects.app.open_virtual', return_value=sink):
            with self.assertRaisesRegex(RuntimeError, 'lost virtual device'):
                run(args)
        sink.__exit__.assert_called_once()

    def test_preview_does_not_need_virtual_backend(self):
        args = parser().parse_args(['--preview-only', '--test-pattern', '--headless', '--max-frames', '1'])
        with patch('hand_effects.app.open_virtual') as virtual:
            self.assertEqual(run(args)['frames'], 1)
        virtual.assert_not_called()

    def test_invalid_dimensions_and_check_preview_combination_fail_before_hardware(self):
        for argv in (['--width', '1279'], ['--fps', '0'], ['--max-frames', '-1'],
                     ['--countdown', '0'], ['--fade', '-1'], ['--fade', 'nan'],
                     ['--check', '--preview-only']):
            with self.subTest(argv=argv), patch('sys.stderr', new_callable=StringIO):
                with self.assertRaises(SystemExit):
                    main(argv)


if __name__ == '__main__':
    unittest.main()
