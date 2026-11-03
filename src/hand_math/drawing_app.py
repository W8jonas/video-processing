"""Camera UI for constructing shapes from fingertip counts and positions."""

import sys
import time
from math import dist, isfinite

from hand_libras.app import describe, draw_hands
from .cube import STYLES, draw_mesh
from .drawing import DrawingCommands, FingerDrawing, NAMES, TIPS, active_tips
from .fingers import FingerTracker, attach_world_points
from .geometry import area


WINDOW = 'Construir com os dedos'


def draw_drawing(cv2, np, frame, drawing, style, grid):
    mesh = drawing.mesh
    output = draw_mesh(cv2, np, frame, mesh.vertices, drawing.pose, mesh.faces, mesh.edges, style, grid)
    for point, binding in zip(drawing.screen, drawing.bindings):
        pixel = tuple(int(round(v)) for v in point)
        if binding is None:
            cv2.circle(output, pixel, 6, (255, 220, 80), 2, cv2.LINE_AA)
            label = '*'
        else:
            cv2.circle(output, pixel, 7, (70, 245, 255), -1, cv2.LINE_AA)
            label = ('E' if binding.side == 0 else 'D') + ':' + binding.finger[:3]
        cv2.putText(output, label, (pixel[0] + 10, pixel[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, .45, (225, 245, 255), 1, cv2.LINE_AA)
    return output


def draw_tip_diagnostics(cv2, output, hands):
    """Always show all detected tips, including those excluded from the count."""
    height, width = output.shape[:2]
    for hand in hands:
        for name, index in TIPS:
            x, y, _ = hand['points'][index]
            if not (isfinite(x) and isfinite(y)):
                continue
            point = (int(x * width), int(y * height))
            active = hand['fingers'].get(name, False)
            pending = hand.get('finger_pending', {}).get(name, False)
            color = (0, 190, 255) if pending else (90, 240, 95) if active else (130, 130, 130)
            cv2.circle(output, point, 10, color, 2, cv2.LINE_AA)
            cv2.putText(output, name[:3], (point[0] + 9, point[1] + 17),
                        cv2.FONT_HERSHEY_SIMPLEX, .35, color, 1, cv2.LINE_AA)


def run_drawing(cv2, mp, np, detector, args):
    # Import locally: the shared CLI imports this module only for --scene draw.
    from .app import panel

    camera = cv2.VideoCapture(args.camera)
    profile = getattr(args, 'drawing_shape', 'auto')
    controller, commands, tracker = FingerDrawing(profile=profile), DrawingCommands(), FingerTracker()
    frozen = last_valid = None
    style, grid, skeleton = 1, True, False
    frames, failures, total_failures, active_frames = 0, 0, 0, 0
    timestamp, previous, fps = -1, time.monotonic(), 0.0
    seen_shapes = set()
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
                controller.reset()
                tracker.reset()
                commands.update((), time.monotonic())
                last_valid = None
                if failures == 1:
                    print('Aviso: frame indisponivel; tentando recuperar a captura.', file=sys.stderr)
                if failures >= 20:
                    raise RuntimeError('20 leituras sem imagem. Confira a conexao USB ou tente --width 640 --height 480.')
                if not args.headless and frames:
                    if cv2.waitKey(100) & 0xFF in (27, ord('q')):
                        break
                    if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                        break
                else:
                    time.sleep(.1)
                continue
            failures = 0
            now = time.monotonic()
            frame = cv2.flip(frame, 1)
            timestamp = max(timestamp + 1, int(now * 1000))
            result = detector.detect_for_video(mp.Image(
                image_format=mp.ImageFormat.SRGBA, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)), timestamp)
            hands = describe(result, frame.shape[1], frame.shape[0])
            attach_world_points(hands, result)
            hands = tracker.update(hands, now)
            counts, _ = active_tips(hands, frame.shape[1], frame.shape[0])
            live = controller.update(hands, frame.shape[1], frame.shape[0], now)
            if live is not None:
                last_valid = (live, now)
            command = commands.update(counts, now)
            recent = last_valid[0] if last_valid and now - last_valid[1] < 2 else None
            if command == 'style':
                style = (style + 1) % len(STYLES)
            elif command == 'freeze':
                frozen = recent if frozen is None else None
            drawing = frozen if frozen is not None else live
            if drawing is None and counts in ((0, 0), (5, 5)):
                drawing = recent
            frames += 1
            active_frames += int(drawing is not None)
            if drawing:
                seen_shapes.add(drawing.source.kind)
            fps = .9 * fps + .1 / max(time.monotonic() - previous, 1e-6)
            previous = time.monotonic()
            if args.headless:
                continue
            output = draw_drawing(cv2, np, frame, drawing, style, grid) if drawing else frame.copy()
            if skeleton:
                draw_hands(cv2, output, hands)
            draw_tip_diagnostics(cv2, output, hands)
            lines = ['CONSTRUIR COM OS DEDOS', f'FPS: {fps:.1f} | Maos: {len(hands)}',
                     f'Dedos E / D: {counts[0]} / {counts[1]}' if counts else 'Mostre as duas maos',
                     f'Aparencia: {STYLES[style]}',
                     'Figura FIXA' if frozen is not None else 'Pontas controlam a figura', '']
            if profile != 'auto':
                lines.append(f'PONTAS FIXAS: {NAMES[profile]}')
            for side, hand in enumerate(hands):
                chosen = ' '.join(name[:3] for name, _ in TIPS if hand['fingers'].get(name, False)) or 'nenhum'
                lines.append(('E' if side == 0 else 'D') + ': ' + chosen)
            if any(not hand.get('finger_quality', True) for hand in hands):
                lines.append('Landmarks instaveis: reabra a mao.')
            if drawing:
                mesh = drawing.mesh
                inferred = sum(binding is None for binding in drawing.bindings)
                lines += [NAMES[drawing.source.kind].upper(),
                          f'{len(mesh.vertices)} vertices | {len(mesh.edges)} arestas | {len(mesh.faces)} faces',
                          f'Pontas usadas: {len(drawing.source.tips)} | Inferidos: {inferred}']
                if drawing.source.kind == 'cube':
                    lines += ['Dois cantos completados: marcados com *.', 'Bloco livre: pode deformar com os dedos.']
                elif drawing.source.kind == 'pyramid':
                    lines += ['3 pontas: base | 1 ponta: apice']
                else:
                    perimeter = sum(dist(a, b) for a, b in zip(drawing.screen, drawing.screen[1:] + drawing.screen[:1]))
                    lines += [f'Area: {area(drawing.screen):.0f} px^2 | Perimetro: {perimeter:.0f} px']
            else:
                reasons = {'two_hands': 'Preciso localizar as duas maos inteiras.',
                           'unsupported_counts': 'Contagem fora das combinacoes abaixo.',
                           'degenerate_geometry': 'Pontas proximas/alinhadas: abra os cantos.',
                           'settling': f'Confirmando figura: {controller.progress:.0%}'}
                lines += [reasons.get(controller.status, 'Mantenha a pose por 0,3 segundo.')]
            lines += ['', '2 + 1: TRIANGULO', '2 + 2: RETANGULO / QUADRILATERO',
                      '3 + 1: PIRAMIDE TRIANGULAR', '3 + 3: CUBO LIVRE', '',
                      'Sugestao para abrir bem os cantos:',
                      '1: indicador | 2: polegar + indicador',
                      '3: polegar + indicador + medio', '',
                      'CONTROLES SEM TECLADO (0,8s)',
                      'Duas maos fechadas: proxima aparencia',
                      'Duas maos abertas (5+5): fixa / solta']
            if commands.pending:
                label = 'APARENCIA' if commands.pending == 'style' else 'FIXAR / SOLTAR'
                lines.append(f'{label}: {commands.progress:.0%}')
            else:
                lines.append('Volte a pose de desenho entre comandos.')
            lines += ['', '0-3: aparencia | G: grade | H: dedos',
                      'Espaco: fixa / solta | R: reinicia', 'Q / Esc: sair', '',
                      'Aneis: verde=ativo, cinza=recolhido',
                      'Laranja=confirmando | *=canto inferido',
                      'Profundidade virtual; sem centimetros.']
            cv2.imshow(WINDOW, panel(cv2, output, lines))
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q')) or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
            if key in map(ord, '0123'):
                style = key - ord('0')
            elif key == ord('g'):
                grid = not grid
            elif key == ord('h'):
                skeleton = not skeleton
            elif key == 32:
                frozen = drawing if frozen is None else None
            elif key == ord('r'):
                frozen = last_valid = None
                controller.reset()
                tracker.reset()
        return dict(frames=frames, drawing_frames=active_frames, shapes=sorted(seen_shapes),
                    capture_failures=total_failures, loop_fps=round(fps, 1), scene='draw')
    finally:
        camera.release()
        if not args.headless:
            cv2.destroyAllWindows()
