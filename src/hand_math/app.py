"""A filtered 2D portal and a laboratory of rigid solids controlled by two hands."""

import argparse
import json
from math import degrees
import os
from pathlib import Path
import sys
import time

from hand_libras.app import ROOT, describe, draw_hands
from .geometry import SmoothQuad, measurements, quad_from_hands
from .gestures import PortalGestures
from .cube import STYLES, draw_cube, pose_from_quad
from .solids import SOLIDS, SOLID_STATS, AutoRotation

MODES = ('Original', 'Negativo', 'Termico', 'Bordas')
WINDOW = 'Matematica com as maos'


def panel(cv2, frame, lines):
    height, width = frame.shape[:2]
    result = cv2.copyMakeBorder(frame, 0, max(0, 30 + len(lines) * 21 - height),
                               0, 470, cv2.BORDER_CONSTANT, value=(25, 25, 25))
    for i, line in enumerate(lines):
        cv2.putText(result, line, (width + 14, 26 + i * 21), cv2.FONT_HERSHEY_SIMPLEX,
                    .43, (225, 230, 235), 1, cv2.LINE_AA)
    return result


def draw_portal(cv2, np, frame, points, mode, grid):
    polygon = np.rint(points).astype(np.int32)
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    cv2.fillConvexPoly(mask, polygon, 255)
    if mode == 1:
        filtered = cv2.bitwise_not(frame)
    elif mode == 2:
        filtered = cv2.applyColorMap(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.COLORMAP_TURBO)
    elif mode == 3:
        edges = cv2.Canny(frame, 70, 140)
        filtered = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    else:
        filtered = frame
    output = frame.copy()
    output[mask > 0] = filtered[mask > 0]
    if grid:
        # Project a unit square into the hand-defined quadrilateral.
        transform = cv2.getPerspectiveTransform(
            np.float32([[0, 0], [1, 0], [1, 1], [0, 1]]), np.float32(points))
        for t in (0.2, 0.4, 0.6, 0.8):
            endpoints = np.float32([[[t, 0]], [[t, 1]], [[0, t]], [[1, t]]])
            projected = np.rint(cv2.perspectiveTransform(endpoints, transform)).astype(np.int32).reshape(4, 2)
            cv2.line(output, tuple(projected[0]), tuple(projected[1]), (150, 220, 240), 1, cv2.LINE_AA)
            cv2.line(output, tuple(projected[2]), tuple(projected[3]), (150, 220, 240), 1, cv2.LINE_AA)
    cv2.polylines(output, [polygon], True, (80, 255, 160), 2, cv2.LINE_AA)
    for i, point in enumerate(polygon):
        cv2.circle(output, tuple(point), 7, (60, 240, 250), -1)
        cv2.putText(output, f'P{i}', tuple(point + (10, -10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (60, 240, 250), 2)
    return output


def run(cv2, mp, np, detector, args):
    camera = cv2.VideoCapture(args.camera)
    smoother = SmoothQuad()
    gestures = PortalGestures()
    mode, grid, skeleton, frozen = 1, True, False, None
    scene = getattr(args, 'scene', 'portal')
    solid_index = next(i for i, solid in enumerate(SOLIDS) if solid.key == getattr(args, 'shape', 'cube'))
    rotation = AutoRotation()
    rotation.enabled = getattr(args, 'auto_rotate', False)
    last_live = None
    points = None
    frames, failures, total_failures, active_frames = 0, 0, 0, 0
    timestamp, previous, fps = -1, time.monotonic(), 0.0
    try:
        if not camera.isOpened():
            raise RuntimeError('Camera indisponivel. Confira --camera e as permissoes do macOS.')
        if args.width:
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        while not args.max_frames or frames < args.max_frames:
            ok, frame = camera.read()
            if not ok or frame is None or frame.size == 0:
                failures += 1
                total_failures += 1
                smoother.update(None, time.monotonic())
                gestures.update([], time.monotonic())
                if failures >= 20:
                    raise RuntimeError('20 leituras sem imagem. Confira a conexao USB ou tente --width 640 --height 480.')
                if not args.headless and frames:
                    if cv2.waitKey(100) & 0xFF in (27, ord('q')):
                        break
                    if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                        break
                else:
                    time.sleep(0.1)
                continue
            failures = 0
            frame = cv2.flip(frame, 1)
            now = time.monotonic()
            timestamp = max(timestamp + 1, int(now * 1000))
            result = detector.detect_for_video(mp.Image(
                image_format=mp.ImageFormat.SRGBA, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)), timestamp)
            hands = describe(result, frame.shape[1], frame.shape[0])
            live = smoother.update(quad_from_hands(hands, frame.shape[1], frame.shape[0]), now)
            command = gestures.update(hands, now, allow_single_pinches=scene == 'cube')
            if live is not None and not any(gestures.pinched):
                last_live = (live, now)
            controlled = live
            # A pinch collapses a corner: briefly retain the pre-gesture frame
            # while the command is held. Missing hands never activate this grace.
            if (scene == 'cube' and len(hands) == 2 and any(gestures.pinched)
                    and last_live is not None and now - last_live[1] < 3):
                controlled = last_live[0]
            if command == 'filter':
                mode = (mode + 1) % len(MODES)
            elif command == 'grid':
                grid = not grid
            elif command == 'freeze':
                frozen = controlled if frozen is None else None
            elif command == 'scene':
                scene = 'cube' if scene == 'portal' else 'portal'
                frozen = None
            elif command == 'shape':
                solid_index = (solid_index + 1) % len(SOLIDS)
            elif command == 'spin':
                rotation.enabled = not rotation.enabled
            points = frozen if frozen is not None else controlled
            rotation.update(now, active=points is not None and scene == 'cube', frozen=frozen is not None)
            frames += 1
            active_frames += int(points is not None)
            fps = 0.9 * fps + 0.1 / max(time.monotonic() - previous, 1e-6)
            previous = time.monotonic()
            if args.headless:
                continue
            if points is None:
                output = frame.copy()
            elif scene == 'cube':
                output = draw_cube(cv2, np, frame, points, mode, grid,
                                   mesh=SOLIDS[solid_index], spin=rotation.angle)
            else:
                output = draw_portal(cv2, np, frame, points, mode, grid)
            if skeleton:
                draw_hands(cv2, output, hands)
            lines = [f'LAB 3D | {SOLIDS[solid_index].name.upper()}' if scene == 'cube' else 'PORTAL 2D', f'FPS: {fps:.1f} | Maos: {len(hands)}',
                     'Objeto FIXO' if frozen is not None else 'Objeto acompanha os dedos',
                     f'Aparencia: {STYLES[mode] if scene == "cube" else MODES[mode]}', '',
                     'Mostre duas maos formando uma moldura.',
                     'Indicadores em cima, polegares embaixo.',
                     'Afaste as maos: aumenta o objeto.', '']
            if points is not None and scene == 'cube':
                pose = pose_from_quad(points)
                stats = SOLID_STATS[solid_index]
                lines += [f'Escala visual: {pose.scale:.0f} px',
                          f'Giro X / Y / Z: {degrees(pose.pitch):.0f} / {degrees(pose.yaw + rotation.angle) % 360:.0f} / {degrees(pose.roll):.0f}',
                          f'{stats["vertices"]} vertices | {stats["edges"]} arestas | {stats["faces"]} faces',
                          f'Euler: {stats["vertices"]} - {stats["edges"]} + {stats["faces"]} = {stats["euler"]}',
                          f'Area: {stats["area"]:.3f} u^2 | Volume: {stats["volume"]:.3f} u^3',
                          f'Giro automatico: {"LIGADO" if rotation.enabled else "DESLIGADO"}',
                          'Incline e varie a abertura dos dedos.']
            elif points is not None:
                stats = measurements(points)
                lines += [f'Area = {stats["area"]:.0f} px^2',
                          f'Perimetro = {stats["perimeter"]:.0f} px',
                          'Angulos: ' + ' / '.join(f'{a:.0f}' for a in stats['angles']),
                          f'Soma dos angulos = {sum(stats["angles"]):.0f} graus',
                          'Lados: ' + ' / '.join(f'{a:.0f}' for a in stats['sides'])]
            else:
                lines += ['Aguardando moldura valida...', 'Mantenha os quatro cantos separados.']
            commands = {'filter': 'TROCAR APARENCIA', 'freeze': 'FIXAR / SOLTAR', 'grid': 'ALTERNAR GRADE',
                        'scene': 'ALTERNAR 2D / 3D', 'shape': 'PROXIMO SOLIDO', 'spin': 'GIRO AUTOMATICO'}
            if gestures.pending:
                gesture_status = f'{commands[gestures.pending]}: {gestures.progress:.0%}'
            else:
                gesture_status = ('Gestos prontos' if gestures.armed else
                                  'Recolha os 3 dedos nas duas maos')
            lines += ['', 'CONTROLE SEM TECLADO (segure 0,8s)',
                      'Mantenha polegar/indicador na moldura.',
                      'Abra os outros 3 dedos:',
                      'Mao a esquerda da tela: aparencia',
                      'Mao a direita: fixar / soltar objeto',
                      'Ambas: mostrar / esconder grade',
                      'Pinca nas DUAS maos: alternar 2D / 3D',
                      *(['Pinca esquerda: proxima forma', 'Pinca direita: giro automatico'] if scene == 'cube' else []),
                      gesture_status,
                      '', '0-3: aparencia | C: alternar 2D / 3D',
                      'G: grade projetiva | H: articulacoes', 'Espaco: fixa/solta | R: reinicia',
                      *(['S: proxima forma | A: giro automatico'] if scene == 'cube' else []),
                      'Q / Esc: sair', '', 'Camera virtual; sem profundidade metrica.' if scene == 'cube' else
                      'Medidas na imagem, em pixels.']
            cv2.imshow(WINDOW, panel(cv2, output, lines))
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q')) or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
            if key in map(ord, '0123'):
                mode = key - ord('0')
            elif key == ord('g'):
                grid = not grid
            elif key == ord('h'):
                skeleton = not skeleton
            elif key == ord('c'):
                scene = 'cube' if scene == 'portal' else 'portal'
                frozen = None
            elif key == ord('s') and scene == 'cube':
                solid_index = (solid_index + 1) % len(SOLIDS)
            elif key == ord('a') and scene == 'cube':
                rotation.enabled = not rotation.enabled
            elif key == 32:
                frozen = points if frozen is None else None
            elif key == ord('r'):
                frozen = None
                rotation.reset()
                smoother.update(None, now)
        return dict(frames=frames, portal_frames=active_frames, capture_failures=total_failures,
                    loop_fps=round(fps, 1), scene=scene, shape=SOLIDS[solid_index].key,
                    auto_rotation=rotation.enabled)
    finally:
        camera.release()
        if not args.headless:
            cv2.destroyAllWindows()


def main(argv=None):
    parser = argparse.ArgumentParser(description='Desenho pelas pontas dos dedos, portal 2D e laboratorio 3D')
    parser.add_argument('--scene', choices=('portal', 'cube', 'draw'), default='portal')
    parser.add_argument('--drawing-shape', choices=('auto', 'triangle', 'rectangle', 'pyramid', 'cube'),
                        default='auto', help='Em draw: pontas fixas de uma figura, sem contar dedos')
    parser.add_argument('--shape', choices=tuple(solid.key for solid in SOLIDS), default='cube')
    parser.add_argument('--spin', dest='auto_rotate', action='store_true', help='Iniciar com giro automatico')
    parser.add_argument('--camera', type=int, default=0)
    parser.add_argument('--model', type=Path, default=ROOT / 'models/hand_landmarker.task')
    parser.add_argument('--width', type=int, default=0)
    parser.add_argument('--height', type=int, default=0)
    parser.add_argument('--delegate', choices=('cpu', 'gpu'), default='cpu')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--max-frames', type=int, default=0)
    args = parser.parse_args(argv)
    if args.max_frames < 0 or args.width < 0 or args.height < 0 or bool(args.width) != bool(args.height):
        parser.error('Use frames >= 0 e largura/altura positivas juntas, ou ambas em 0')
    try:
        if not args.model.is_file():
            raise RuntimeError('Modelo ausente. Execute hand-libras --download-model')
        os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache/matplotlib'))
        import cv2
        import mediapipe as mp
        import numpy as np
        from mediapipe.tasks.python import BaseOptions, vision

        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(args.model), delegate=(
                BaseOptions.Delegate.GPU if args.delegate == 'gpu' else BaseOptions.Delegate.CPU)),
            running_mode=vision.RunningMode.VIDEO, num_hands=2,
            min_hand_detection_confidence=0.6, min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.6)
        with vision.HandLandmarker.create_from_options(options) as detector:
            if args.scene == 'draw':
                from .drawing_app import run_drawing
                report = run_drawing(cv2, mp, np, detector, args)
            else:
                report = run(cv2, mp, np, detector, args)
        print(json.dumps(report))
        return 0
    except (OSError, RuntimeError, ValueError, ImportError) as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
