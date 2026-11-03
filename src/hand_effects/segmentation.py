"""MediaPipe person confidence masks, separate from the published image."""

import hashlib
from pathlib import Path
import ssl
from urllib.request import urlopen

import numpy as np

MODEL_URL = ('https://storage.googleapis.com/mediapipe-models/image_segmenter/'
             'selfie_segmenter_landscape/float16/1/selfie_segmenter_landscape.tflite')
MODEL_SHA256 = '490e9ea734313e0de10fa0cd9e3c6133e36ea4db2b7a49bde9ef019f72796b8e'


def download_model(path):
    path = Path(path)
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != MODEL_SHA256:
            raise ValueError('Modelo existente difere do oficial; use outro --segment-model para o download.')
        print(f'Modelo de segmentacao ja existe: {path}')
        return
    import certifi
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.download')
    try:
        with urlopen(MODEL_URL, timeout=60, context=ssl.create_default_context(
                cafile=certifi.where())) as response:
            data = response.read(4 * 1024 * 1024)
        if hashlib.sha256(data).hexdigest() != MODEL_SHA256:
            raise ValueError('Download de segmentacao nao corresponde ao modelo oficial esperado')
        temporary.write_bytes(data)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    print(f'Modelo de segmentacao salvo: {path}')


def person_confidence(result, labels):
    """Select by metadata: the pinned model has one channel named 'selfie'."""
    labels = [label.strip().lower() for label in labels]
    masks = result.confidence_masks
    if not masks or len(labels) != len(masks):
        raise ValueError('Canais de segmentacao incompatíveis com os rotulos do modelo')
    if labels == ['selfie']:
        index = 0
    elif 'person' in labels:
        index = labels.index('person')
    else:
        raise ValueError('Modelo deve identificar pessoa (rotulo person ou selfie)')
    mask = masks[index].numpy_view()
    if mask.ndim == 3 and mask.shape[2] == 1:
        mask = mask[:, :, 0]
    if mask.ndim != 2 or not mask.size or not np.isfinite(mask).all():
        raise ValueError('Mascara de pessoa invalida')
    return np.clip(mask, 0., 1.).astype(np.float32)


def refine_mask(cv2, confidence, width, height, margin=3):
    # Saturate confident pixels, expand slightly to cover edges, then feather.
    mask = np.clip((confidence - .2) / .4, 0., 1.).astype(np.float32)
    if mask.shape != (height, width):
        mask = cv2.resize(mask, (width, height), interpolation=cv2.INTER_LINEAR)
    if margin:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (margin * 2 + 1, margin * 2 + 1))
        mask = cv2.dilate(mask, kernel)
    return np.clip(cv2.GaussianBlur(mask, (5, 5), 0), 0., 1.)


class PersonSegmenter:
    def __init__(self, path, margin=3):
        self.path, self.margin = Path(path), margin

    def __enter__(self):
        if not self.path.is_file():
            raise RuntimeError('Modelo de pessoa ausente. Execute .venv/bin/hand-effects --download-segmenter')
        from mediapipe.tasks.python import BaseOptions, vision
        self.segmenter = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=str(self.path)),
            running_mode=vision.RunningMode.VIDEO, output_confidence_masks=True,
            output_category_mask=False))
        try:
            self.labels = self.segmenter.labels
        except Exception:
            self.segmenter.close()
            raise
        return self

    def mask(self, cv2, image, timestamp, width, height):
        result = self.segmenter.segment_for_video(image, timestamp)
        return refine_mask(cv2, person_confidence(result, self.labels), width, height, self.margin)

    def __exit__(self, *exc):
        self.segmenter.close()
