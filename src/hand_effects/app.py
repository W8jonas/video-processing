"""Stage 1: tracked hands -> clean preview and OBS virtual camera."""

import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys
import time

from hand_libras.app import ROOT, describe, draw_hands
from hand_math.fingers import FingerTracker, attach_world_points
from .output import fit_frame, open_virtual, test_pattern

WINDOW = 'hand effects - camera output'
FINGERS = ((1, 'indicador', 8), (2, 'medio', 12), (3, 'anelar', 16), (4, 'minimo', 20))


def parser():
    result = argparse.ArgumentParser(description='Maos na camera virtual para Google Meet (etapa 1)')
    result.add_argument('--camera', type=int, default=1)
    result.add_argument('--preview-only', action='store_true', help='Somente janela local; nao abre camera virtual')
    result.add_argument('--check', action='store_true', help='Testar abertura da saida virtual sem acessar webcam')
    result.add_argument('--test-pattern', action='store_true', help='Barras RGB e contador, sem acessar webcam')
    result.add_argument('--width', type=int, default=1280, help='Largura da saida; nao altera modo da USB')
    result.add_argument('--height', type=int, default=720)
    result.add_argument('--fps', type=int, default=30, help='Limite de FPS; desempenho real depende da inferencia')
    orientation = result.add_mutually_exclusive_group()
    orientation.add_argument('--mirror', dest='no_mirror', action='store_false',
                             help='Espelhar o video enviado (opcional)')
    orientation.add_argument('--no-mirror', dest='no_mirror', action='store_true',
                             help='Manter orientacao original da camera (padrao)')
    result.set_defaults(no_mirror=True)
    result.add_argument('--headless', action='store_true')
    result.add_argument('--max-frames', type=int, default=0)
    result.add_argument('--model', type=Path, default=ROOT / 'models/hand_landmarker.task')
    return result


def annotate(cv2, frame, hands):
    draw_hands(cv2, frame, hands)
    for hand in hands:
        for number, name, tip in FINGERS:
            x, y, _ = hand['points'][tip]
            point = (int(x * frame.shape[1]), int(y * frame.shape[0]))
            color = (70, 240, 110) if hand['fingers'].get(name, False) else (140, 140, 140)
            cv2.circle(frame, point, 12, color, 2, cv2.LINE_AA)
            cv2.putText(frame, str(number), (point[0] + 13, point[1]),
                        cv2.FONT_HERSHEY_SIMPLEX, .7, color, 2, cv2.LINE_AA)


def run(args):
    import cv2

    frames = failures = total_failures = 0
    timestamp = -1
    annotations = True
    with ExitStack() as stack:
        if not args.headless:
            stack.callback(cv2.destroyAllWindows)
        virtual = None
        if not args.preview_only:
            virtual = stack.enter_context(open_virtual(args.width, args.height, args.fps))
            print(f'Camera virtual: {virtual.device}', flush=True)
        if args.check:
            frame = test_pattern(cv2, args.width, args.height, 0)
            virtual.send(frame)
            return dict(ok=True, device=virtual.device, width=args.width, height=args.height)
        detector = camera = None
        tracker = FingerTracker()
        if not args.test_pattern:
            if not args.model.is_file():
                raise RuntimeError('Modelo ausente. Execute .venv/bin/hand-libras --download-model')
            os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache/matplotlib'))
            import mediapipe as mp
            from mediapipe.tasks.python import BaseOptions, vision
            detector = stack.enter_context(vision.HandLandmarker.create_from_options(
                vision.HandLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=str(args.model)),
                    running_mode=vision.RunningMode.VIDEO, num_hands=2,
                    min_hand_detection_confidence=.6, min_hand_presence_confidence=.6,
                    min_tracking_confidence=.6)))
            camera = cv2.VideoCapture(args.camera)
            stack.callback(camera.release)
            if not camera.isOpened():
                raise RuntimeError('Webcam indisponivel. Confira --camera, permissao do macOS e outros apps.')
        print('Q/Esc: sair | H: alternar marcacoes. Janela e saida virtual mostram o mesmo video.', flush=True)
        started = time.monotonic()
        while not args.max_frames or frames < args.max_frames:
            iteration = time.monotonic()
            if args.test_pattern:
                output = test_pattern(cv2, args.width, args.height, frames)
            else:
                ok, raw = camera.read()
                if not ok or raw is None or not raw.size:
                    failures += 1
                    total_failures += 1
                    tracker.reset()
                    if failures >= 20:
                        raise RuntimeError('20 falhas de captura. Confira USB, indice --camera e outros apps.')
                    time.sleep(.05)
                    continue
                failures = 0
                # Infer on original video before drawing/composition (future invisibility).
                original = cv2.flip(raw, 1) if not args.no_mirror else raw
                now = time.monotonic()
                timestamp = max(timestamp + 1, int(now * 1000))
                result = detector.detect_for_video(mp.Image(
                    image_format=mp.ImageFormat.SRGBA,
                    data=cv2.cvtColor(original, cv2.COLOR_BGR2RGBA)), timestamp)
                hands = describe(result, original.shape[1], original.shape[0])
                attach_world_points(hands, result)
                hands = tracker.update(hands, now)
                processed = original.copy()
                if annotations:
                    annotate(cv2, processed, hands)
                output = fit_frame(cv2, processed, args.width, args.height)
            if virtual:
                virtual.send(output)
            frames += 1
            if not args.headless:
                cv2.imshow(WINDOW, output)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord('q')) or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                    break
                if key == ord('h'):
                    annotations = not annotations
            # Bound capture/preview rate too; no frame queue grows under load.
            time.sleep(max(0., 1 / args.fps - (time.monotonic() - iteration)))
    return dict(frames=frames, capture_failures=total_failures,
                loop_fps=round(frames / max(time.monotonic() - started, .001), 1))


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    if (not 64 <= args.width <= 3840 or not 64 <= args.height <= 2160
            or args.width % 2 or args.height % 2 or not 1 <= args.fps <= 60 or args.max_frames < 0):
        cli.error('Use dimensoes pares entre 64..3840 x 64..2160, fps 1..60 e max-frames >= 0')
    if args.check and (args.preview_only or args.test_pattern):
        cli.error('--check testa somente a saida virtual; remova --preview-only/--test-pattern')
    try:
        print(json.dumps(run(args), ensure_ascii=False))
        return 0
    except KeyboardInterrupt:
        return 130
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
