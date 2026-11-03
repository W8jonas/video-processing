from io import BytesIO
from pathlib import Path
import ssl
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

from hand_libras.app import download_model, main, run_camera
from hand_libras.core import PoseLibrary


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def camera_setup(self):
        cv2 = MagicMock()
        frame = SimpleNamespace(shape=(480, 640, 3), size=480 * 640 * 3)
        camera = cv2.VideoCapture.return_value
        camera.isOpened.return_value = True
        camera.read.return_value = (True, frame)
        cv2.flip.return_value = frame
        mp = MagicMock()
        landmarker = MagicMock()
        library = PoseLibrary(self.root / 'poses.jsonl')
        args = SimpleNamespace(camera=0, max_frames=3, headless=True, width=0, height=0)
        return cv2, mp, landmarker, library, args

    def test_headless_frames_use_strictly_increasing_timestamps_and_release_camera(self):
        cv2, mp, detector, library, args = self.camera_setup()
        with patch('hand_libras.app.describe', return_value=[]), patch('hand_libras.app.time.monotonic', return_value=10):
            report = run_camera(cv2, mp, detector, library, args)
        self.assertEqual(report['frames'], 3)
        self.assertEqual([call.args[1] for call in detector.detect_for_video.call_args_list], [10000, 10001, 10002])
        cv2.VideoCapture.return_value.release.assert_called_once()
        cv2.VideoCapture.return_value.set.assert_not_called()
        cv2.imshow.assert_not_called()

    def test_capture_failure_releases_camera(self):
        cv2, mp, detector, library, args = self.camera_setup()
        cv2.VideoCapture.return_value.read.return_value = (False, None)
        with patch('hand_libras.app.time.sleep'), patch('sys.stderr'):
            with self.assertRaisesRegex(RuntimeError, '20 leituras consecutivas'):
                run_camera(cv2, mp, detector, library, args)
        self.assertEqual(cv2.VideoCapture.return_value.read.call_count, 20)
        cv2.VideoCapture.return_value.release.assert_called_once()

    def test_capture_recovers_after_transient_failure_and_empty_frame(self):
        cv2, mp, detector, library, args = self.camera_setup()
        camera = cv2.VideoCapture.return_value
        good = camera.read.return_value
        camera.read.side_effect = [good, (False, None), (True, None), good, good]
        with patch('hand_libras.app.describe', return_value=[]), patch('hand_libras.app.time.sleep'), patch('sys.stderr'):
            report = run_camera(cv2, mp, detector, library, args)
        self.assertEqual(report['frames'], 3)
        self.assertEqual(report['capture_failures'], 2)
        self.assertEqual(detector.detect_for_video.call_count, 3)

    def test_requested_resolution_is_applied(self):
        cv2, mp, detector, library, args = self.camera_setup()
        args.width, args.height = 640, 480
        with patch('hand_libras.app.describe', return_value=[]):
            run_camera(cv2, mp, detector, library, args)
        cv2.VideoCapture.return_value.set.assert_any_call(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cv2.VideoCapture.return_value.set.assert_any_call(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def test_missing_model_reports_actionable_error(self):
        with patch('sys.stderr') as error:
            self.assertEqual(main(['--model', str(self.root / 'missing.task')]), 1)
        self.assertIn('--download-model', error.write.call_args_list[0].args[0])

    def test_invalid_download_leaves_no_partial_model(self):
        path = self.root / 'models/hand_landmarker.task'
        with patch('hand_libras.app.urlopen', return_value=BytesIO(b'not a model')):
            with self.assertRaises(ValueError):
                download_model(path)
        self.assertFalse(path.exists())
        self.assertFalse(path.with_suffix('.download').exists())

    def test_model_download_is_validated_and_existing_file_is_preserved(self):
        buffer = BytesIO()
        with ZipFile(buffer, 'w') as archive:
            archive.writestr('hand_detector.tflite', b'synthetic test fixture')
            archive.writestr('hand_landmarks_detector.tflite', b'synthetic test fixture')
        content = buffer.getvalue()
        path = self.root / 'hand_landmarker.task'
        with patch('hand_libras.app.urlopen', return_value=BytesIO(content)) as request, patch('builtins.print'):
            download_model(path)
        context = request.call_args.kwargs['context']
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertEqual(path.read_bytes(), content)
        with patch('hand_libras.app.urlopen') as request, patch('builtins.print'):
            download_model(path)
        request.assert_not_called()
        self.assertEqual(path.read_bytes(), content)


if __name__ == '__main__':
    unittest.main()
