"""Fixed-size BGR output; camera mode changes cannot change the virtual format."""

import numpy as np


def fit_frame(cv2, frame, width, height):
    source_height, source_width = frame.shape[:2]
    scale = min(width / source_width, height / source_height)
    target_width = max(1, min(width, round(source_width * scale)))
    target_height = max(1, min(height, round(source_height * scale)))
    resized = cv2.resize(frame, (target_width, target_height))
    output = np.zeros((height, width, 3), dtype=np.uint8)
    x, y = (width - target_width) // 2, (height - target_height) // 2
    output[y:y + target_height, x:x + target_width] = resized
    return output


def test_pattern(cv2, width, height, count):
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    # Explicit BGR primaries expose accidental RGB/BGR swaps at the recipient.
    for index, color in enumerate(((0, 0, 255), (0, 255, 0), (255, 0, 0))):
        frame[:, index * width // 3:(index + 1) * width // 3] = color
    cv2.putText(frame, f'ABC123  FRAME {count}', (20, height // 2),
                cv2.FONT_HERSHEY_SIMPLEX, .9, (255, 255, 255), 2, cv2.LINE_AA)
    return frame


def open_virtual(width, height, fps):
    try:
        import pyvirtualcam
        return pyvirtualcam.Camera(width=width, height=height, fps=fps,
                                   fmt=pyvirtualcam.PixelFormat.BGR, backend='obs')
    except (ImportError, RuntimeError) as exc:
        raise RuntimeError(
            'Camera virtual indisponivel. Instale .venv/bin/python -m pip install -e ".[effects]"; '
            'abra OBS, autorize a extensao de camera no macOS, inicie/pare a camera virtual '
            'e encerre OBS (Cmd+Q). Depois tente novamente. '
            'Para testar apenas a webcam, use --preview-only. Detalhe: ' + str(exc)) from exc
