from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from hand_effects.app import parser, run
from hand_effects.background import BackgroundEffect, local_preview
from hand_effects.segmentation import download_model, person_confidence, refine_mask


def result(*masks):
    return SimpleNamespace(confidence_masks=[SimpleNamespace(numpy_view=lambda data=mask: data) for mask in masks])


class MaskTests(unittest.TestCase):
    def test_single_selfie_channel_and_person_label_in_arbitrary_order(self):
        foreground = np.full((10, 12, 1), .8, dtype=np.float32)
        np.testing.assert_allclose(person_confidence(result(foreground), ['selfie']), .8)
        np.testing.assert_allclose(person_confidence(result(foreground, 1 - foreground),
                                                    ['person', 'background']), .8)
        np.testing.assert_allclose(person_confidence(result(1 - foreground, foreground),
                                                    ['background', 'person']), .8)

    def test_unknown_missing_and_nonfinite_masks_fail_instead_of_hiding_entire_frame(self):
        for output, labels in ((result(), []), (result(np.ones((2, 2))), ['cat']),
                               (result(np.ones((2, 2))), ['person', 'background']),
                               (result(np.array([[np.nan]])), ['selfie'])):
            with self.subTest(labels=labels), self.assertRaises(ValueError):
                person_confidence(output, labels)

    def test_refinement_resizes_and_preserves_empty_and_full_masks(self):
        for value in (0., 1.):
            mask = refine_mask(cv2, np.full((10, 12), value, dtype=np.float32), 96, 64)
            self.assertEqual(mask.shape, (64, 96))
            self.assertEqual(mask.dtype, np.float32)
            np.testing.assert_allclose(mask, value)

    def test_margin_expands_person_edges_without_touching_far_background(self):
        confidence = np.zeros((40, 40), dtype=np.float32)
        confidence[15:25, 15:25] = 1.
        plain = refine_mask(cv2, confidence, 40, 40, margin=0)
        expanded = refine_mask(cv2, confidence, 40, 40, margin=3)
        self.assertGreater(expanded.sum(), plain.sum())
        self.assertEqual(expanded[0, 0], 0.)
        self.assertEqual(expanded[20, 20], 1.)


class SelectiveCompositionTests(unittest.TestCase):
    def setUp(self):
        self.effect = BackgroundEffect(countdown=1., fade=0.)
        self.background = np.full((120, 180, 3), 40, dtype=np.uint8)
        self.effect.begin_capture(0.)
        self.effect.update(self.background, 1.)
        self.effect.confirm()
        self.effect.toggle(2.)

    def test_person_is_removed_while_background_motion_stays_live(self):
        mask = np.zeros((120, 180), dtype=np.float32)
        mask[:, :90] = 1.
        for movement in (70, 100):
            live = np.full_like(self.background, movement)
            live[:, :90] = 200
            output = self.effect.compose(cv2, live, 3., mask)
            np.testing.assert_array_equal(output[:, :90], self.background[:, :90])
            np.testing.assert_array_equal(output[:, 90:], live[:, 90:])
            self.assertTrue((live[:, :90] == 200).all())

    def test_soft_mask_and_fade_multiply_instead_of_replacing_outside_person(self):
        self.effect.fade = 1.
        self.effect.origin, self.effect.since = 0., 2.
        live = np.full_like(self.background, 200)
        mask = np.full(live.shape[:2], .5, dtype=np.float32)
        self.assertTrue((self.effect.compose(cv2, live, 2.5, mask) == 160).all())
        self.assertTrue((self.effect.compose(cv2, live, 3., mask) == 120).all())

    def test_bad_mask_dimensions_are_rejected(self):
        with self.assertRaises(ValueError):
            self.effect.compose(cv2, self.background, 3., np.zeros((10, 10)))

    def test_mask_debug_is_local_and_does_not_mutate_published_output(self):
        live = np.full_like(self.background, 200)
        debug = local_preview(cv2, self.effect, live, 3., np.zeros(live.shape[:2]))
        self.assertTrue((debug[-1] == 0).all())
        self.assertTrue((live == 200).all())

    def test_hidden_pipeline_reads_original_and_suppresses_hand_annotations(self):
        from mediapipe.tasks.python import vision
        original = np.full((120, 180, 3), 200, dtype=np.uint8)
        mask = np.zeros(original.shape[:2], dtype=np.float32)
        mask[:, :90] = 1.
        detector = MagicMock()
        detector.__enter__.return_value = detector
        detector.detect_for_video.return_value = SimpleNamespace(
            hand_landmarks=[], hand_world_landmarks=[], handedness=[])
        camera = MagicMock()
        camera.read.return_value = (True, original)
        segmenter = MagicMock()
        segmenter.__enter__.return_value = segmenter
        segmenter.mask.return_value = mask
        sink = MagicMock()
        sink.__enter__.return_value = sink
        args = parser().parse_args(['--headless', '--max-frames', '1', '--width', '180', '--height', '120'])
        with patch.object(vision.HandLandmarker, 'create_from_options', return_value=detector), \
                patch.object(cv2, 'VideoCapture', return_value=camera), \
                patch('hand_effects.app.PersonSegmenter', return_value=segmenter), \
                patch('hand_effects.app.open_virtual', return_value=sink), \
                patch('hand_effects.app.BackgroundEffect', return_value=self.effect), \
                patch('hand_effects.app.annotate') as annotation:
            run(args)
        output = sink.send.call_args.args[0]
        np.testing.assert_array_equal(output[:, :90], self.background[:, :90])
        np.testing.assert_array_equal(output[:, 90:], original[:, 90:])
        np.testing.assert_array_equal(detector.detect_for_video.call_args.args[0].numpy_view(), original)
        annotation.assert_not_called()
        segmenter.mask.assert_called_once()
        segmenter.__exit__.assert_called_once()
        camera.release.assert_called_once()


class DownloadTests(unittest.TestCase):
    def test_invalid_download_and_existing_file_are_not_overwritten(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'model.tflite'
            with patch('hand_effects.segmentation.urlopen', return_value=BytesIO(b'invalid')):
                with self.assertRaises(ValueError):
                    download_model(path)
            self.assertFalse(path.exists())
            self.assertFalse(path.with_suffix('.download').exists())
            path.write_bytes(b'keep existing')
            with self.assertRaises(ValueError):
                download_model(path)
            self.assertEqual(path.read_bytes(), b'keep existing')


if __name__ == '__main__':
    unittest.main()
