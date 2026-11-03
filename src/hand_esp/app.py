"""Webcam -> independently identified fingers -> local ESP8266 HTTP receiver."""

import argparse
import json
import os
from pathlib import Path
import sys
import time

from hand_libras.app import ROOT, describe, draw_hands
from hand_math.app import panel
from hand_math.fingers import FingerTracker, attach_world_points
from .client import EspClient
from .protocol import FINGERS, NEUTRAL, FingerState, StableState, mask_from_ids, select_hand, state_from_hand
from .publisher import Publisher

WINDOW = 'hand gesture control - esp8266'


def parse_ids(value):
    try:
        ids = tuple(int(item.strip()) for item in value.split(',')) if value.strip() else ()
        return mask_from_ids(ids)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('Use IDs separados por virgula: 1,4 ou 1,2,3') from exc


def state_label(state):
    return state.label if state.tracking else 'Sem mao / liberado'


def dry_sender():
    previous = [None]
    def send(state, sequence):
        if state != previous[0]:
            print(json.dumps(dict(simulacao=True, dedos=list(state.ids), rastreando=state.tracking,
                                  mao=state.hand), ensure_ascii=False), flush=True)
            previous[0] = state
        return dict(ok=True, sequencia=sequence)
    return send


def draw_channels(cv2, frame, raw_hands, selected):
    draw_hands(cv2, frame, raw_hands)
    for hand in raw_hands:
        chosen = selected if selected and hand['side'] == selected['side'] else None
        for value, name, tip in FINGERS:
            x, y, _ = hand['points'][tip]
            point = (int(x * frame.shape[1]), int(y * frame.shape[0]))
            active = chosen and chosen['fingers'].get(name, False)
            color = (70, 240, 110) if active else (150, 150, 150)
            cv2.circle(frame, point, 12, color, 2, cv2.LINE_AA)
            cv2.putText(frame, str(value), (point[0] + 12, point[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, .7, color, 2, cv2.LINE_AA)
    for i, (value, name, _) in enumerate(FINGERS):
        x = 15 + i * 90
        active = selected and selected['fingers'].get(name, False)
        color = (60, 190, 90) if active else (65, 65, 65)
        cv2.rectangle(frame, (x, 15), (x + 75, 75), color, -1)
        cv2.putText(frame, str(value), (x + 23, 58), cv2.FONT_HERSHEY_SIMPLEX, 1., (245, 245, 245), 2)


def run_camera(cv2, mp, detector, args, publisher):
    camera = cv2.VideoCapture(args.camera)
    tracker, gate = FingerTracker(), StableState(args.hold)
    previous_hand = None
    frames = failures = capture_failures = 0
    timestamp, previous, fps = -1, time.monotonic(), 0.
    try:
        if not camera.isOpened():
            raise RuntimeError('Camera indisponivel. Confira --camera e permissao de Camera no macOS.')
        if args.width:
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        while not args.max_frames or frames < args.max_frames:
            ok, frame = camera.read()
            if not ok or frame is None or frame.size == 0:
                failures += 1
                capture_failures += 1
                publisher.set(NEUTRAL)
                gate.reset()
                tracker.reset()
                previous_hand = None
                if failures >= 20:
                    raise RuntimeError('20 leituras sem imagem. Confira USB ou tente --width 640 --height 480.')
                if not args.headless and frames:
                    if cv2.waitKey(100) & 0xFF in (27, ord('q')):
                        break
                    if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                        break
                else:
                    time.sleep(.1)
                continue
            failures = 0
            frame = cv2.flip(frame, 1)
            now = time.monotonic()
            timestamp = max(timestamp + 1, int(now * 1000))
            result = detector.detect_for_video(mp.Image(
                image_format=mp.ImageFormat.SRGBA, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)), timestamp)
            hands = describe(result, frame.shape[1], frame.shape[0])
            attach_world_points(hands, result)
            chosen = select_hand(hands, args.hand)
            identity = chosen['side'] if chosen else None
            if identity != previous_hand:
                tracker.reset()
                gate.reset()
                publisher.set(NEUTRAL)
            previous_hand = identity
            processed = tracker.update([chosen] if chosen else [], now)
            chosen = processed[0] if processed else None
            detected = state_from_hand(chosen)
            confirmed = gate.update(detected, now)
            publisher.set(confirmed)
            frames += 1
            fps = .9 * fps + .1 / max(time.monotonic() - previous, 1e-6)
            previous = time.monotonic()
            if args.headless:
                continue
            draw_channels(cv2, frame, hands, chosen)
            delivery = publisher.status()
            if args.dry_run:
                network = 'SIMULACAO: nenhum dado enviado'
            elif delivery.error:
                network = 'Falha de envio: ' + delivery.error[:45]
            elif delivery.acknowledged == confirmed and now - delivery.acknowledged_at < 2.5:
                network = 'ESP confirmou o estado atual'
            else:
                network = 'Aguardando confirmacao do ESP'
            lines = ['DEDOS -> ESP8266', f'FPS: {fps:.1f}', '',
                     '1 = INDICADOR', '2 = MEDIO', '3 = ANELAR', '4 = MINDINHO',
                     'Polegar ignorado', '',
                     'Detectado: ' + state_label(detected),
                     'Confirmado: ' + state_label(confirmed),
                     'ACK ESP: ' + (state_label(delivery.acknowledged) if delivery.acknowledged else 'aguardando'),
                     network, '',
                     '1 + 4: indicador E mindinho',
                     '1 + 2 + 3: indicador, medio e anelar', '',
                     'Mostre uma unica mao inteira.' if args.hand == 'any' else
                     'Mao selecionada: ' + ('direita' if args.hand == 'right' else 'esquerda'),
                     f'Mantenha a pose por {args.hold:.2f}s.',
                     'Sem mao: o estado enviado e liberado.',
                     'Sem comunicacao: ESP expira em 2,5s.', '',
                     'Q / Esc: sair e enviar estado neutro']
            cv2.imshow(WINDOW, panel(cv2, frame, lines))
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q')) or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
        return dict(frames=frames, capture_failures=capture_failures, loop_fps=round(fps, 1))
    finally:
        publisher.set(NEUTRAL)
        camera.release()
        if not args.headless:
            cv2.destroyAllWindows()


def main(argv=None):
    parser = argparse.ArgumentParser(description='Dedos 1=indicador, 2=medio, 3=anelar, 4=mindinho -> ESP8266')
    parser.add_argument('--esp', default='http://192.168.0.105', help='URL base do receptor V4')
    parser.add_argument('--camera', type=int, default=1)
    parser.add_argument('--hand', choices=('any', 'right', 'left'), default='any')
    parser.add_argument('--dry-run', action='store_true', help='Reconhecer sem enviar dados pela rede')
    parser.add_argument('--hold', type=float, default=.2, help='Tempo de confirmacao de uma combinacao')
    parser.add_argument('--timeout', type=float, default=.8, help='Timeout de cada requisicao HTTP')
    parser.add_argument('--width', type=int, default=0)
    parser.add_argument('--height', type=int, default=0)
    parser.add_argument('--model', type=Path, default=ROOT / 'models/hand_landmarker.task')
    parser.add_argument('--delegate', choices=('cpu', 'gpu'), default='cpu')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--max-frames', type=int, default=0)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--check', action='store_true', help='Consultar firmware e ultimo estado sem usar camera')
    actions.add_argument('--send', type=parse_ids, default=None, metavar='1,4', help='Enviar uma combinacao de teste, sem camera')
    actions.add_argument('--clear', action='store_true', help='Enviar estado neutro sem usar camera')
    args = parser.parse_args(argv)
    if (not .05 <= args.hold <= 2 or not .1 <= args.timeout <= 5 or args.max_frames < 0
            or args.width < 0 or args.height < 0 or bool(args.width) != bool(args.height)):
        parser.error('Use hold 0.05..2, timeout 0.1..5, frames >= 0 e largura/altura juntas')
    publisher = None
    try:
        if args.dry_run and args.check:
            parser.error('--check consulta o ESP; remova --dry-run')
        client = EspClient(args.esp, args.timeout)
        if not args.dry_run:
            health = client.check()
            if args.check:
                print(json.dumps(dict(health=health, state=client.read_state()), ensure_ascii=False))
                return 0
        if args.send is not None or args.clear:
            state = NEUTRAL if args.clear else FingerState(args.send, True, 'Left' if args.hand == 'left' else 'Right')
            result = dry_sender()(state, 1) if args.dry_run else client.send(state, 1)
            print(json.dumps(result, ensure_ascii=False))
            return 0
        if not args.model.is_file():
            raise RuntimeError('Modelo ausente. Execute .venv/bin/hand-libras --download-model')
        os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache/matplotlib'))
        import cv2
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision

        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(args.model), delegate=(
                BaseOptions.Delegate.GPU if args.delegate == 'gpu' else BaseOptions.Delegate.CPU)),
            running_mode=vision.RunningMode.VIDEO, num_hands=2,
            min_hand_detection_confidence=.6, min_hand_presence_confidence=.6,
            min_tracking_confidence=.6)
        publisher = Publisher(dry_sender() if args.dry_run else client.send)
        with vision.HandLandmarker.create_from_options(options) as detector:
            report = run_camera(cv2, mp, detector, args, publisher)
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        return 1
    finally:
        if publisher:
            publisher.close()


if __name__ == '__main__':
    raise SystemExit(main())
