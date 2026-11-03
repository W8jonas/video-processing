"""Webcam UI, image smoke test, and explicit model download."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import ssl
import sys
import time
from urllib.request import urlopen
from uuid import uuid4
from zipfile import ZipFile, is_zipfile

from .core import CONNECTIONS, LETTERS, PoseLibrary, StableLabel, features, finger_states

ROOT = Path(__file__).resolve().parents[2]
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"


def download_model(path):
    if path.exists():
        print(f"Modelo ja existe: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".download")
    try:
        # Python.org builds on macOS may lack a configured system CA bundle.
        # certifi is provided by MediaPipe; preserve TLS verification with it.
        try:
            import certifi
        except ImportError:
            context = ssl.create_default_context()
        else:
            context = ssl.create_default_context(cafile=certifi.where())
        with urlopen(MODEL_URL, timeout=60, context=context) as response, temporary.open("wb") as output:
            while block := response.read(1024 * 1024):
                output.write(block)
        if not is_zipfile(temporary):
            raise ValueError("Download nao e um modelo Tasks valido")
        with ZipFile(temporary) as archive:
            if archive.testzip() or len([n for n in archive.namelist() if n.endswith('.tflite')]) < 2:
                raise ValueError("Modelo Tasks incompleto")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Modelo salvo: {path}")


def parser():
    result = argparse.ArgumentParser(description="Maos e poses estaticas: prototipo Libras")
    result.add_argument("--camera", type=int, default=0, help="Indice da webcam (padrao: 0)")
    result.add_argument("--width", type=int, default=0, help="Largura de captura (0: padrao da camera)")
    result.add_argument("--height", type=int, default=0, help="Altura de captura (0: padrao da camera)")
    result.add_argument("--model", type=Path, default=ROOT / "models/hand_landmarker.task")
    result.add_argument("--data", type=Path, default=ROOT / "data/poses.jsonl")
    result.add_argument("--download-model", action="store_true", help="Baixar modelo oficial e sair")
    result.add_argument("--delegate", choices=("cpu", "gpu"), default="cpu")
    result.add_argument("--image", type=Path, help="Testar imagem sem abrir webcam ou janela")
    result.add_argument("--headless", action="store_true", help="Webcam sem janela; imprime resumo JSON")
    result.add_argument("--max-frames", type=int, default=0, help="Parar apos N frames (0: ilimitado)")
    result.add_argument("--threshold", type=float, default=0.18, help="Distancia RMS maxima; nao e probabilidade")
    result.add_argument("--margin", type=float, default=0.035, help="Separacao minima entre as duas melhores classes")
    return result


def coordinates(landmarks):
    return [(p.x, p.y, p.z) for p in landmarks]


def describe(result, width, height):
    hands = []
    for image, world, categories in zip(result.hand_landmarks, result.hand_world_landmarks, result.handedness):
        side = categories[0].category_name
        points = coordinates(image)
        hands.append(dict(
            side=side,
            points=points,
            vector=features(points, side, width / height),
            fingers=finger_states(coordinates(world)),
        ))
    return hands


def draw_hands(cv2, frame, hands):
    height, width = frame.shape[:2]
    colors = [(110, 220, 100), (255, 180, 80)]
    for index, hand in enumerate(hands):
        pixels = [(int(x * width), int(y * height)) for x, y, _ in hand["points"]]
        color = colors[index % len(colors)]
        for a, b in CONNECTIONS:
            cv2.line(frame, pixels[a], pixels[b], color, 2, cv2.LINE_AA)
        for number, point in enumerate(pixels):
            cv2.circle(frame, point, 4, (240, 240, 240), -1, cv2.LINE_AA)
            cv2.putText(frame, str(number), (point[0] + 5, point[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA)


def panel(cv2, frame, lines):
    height, width = frame.shape[:2]
    frame = cv2.copyMakeBorder(frame, 0, max(0, len(lines) * 25 + 30 - height), 0, 460, cv2.BORDER_CONSTANT, value=(25, 25, 25))
    for index, line in enumerate(lines):
        cv2.putText(frame, line, (width + 15, 30 + index * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (225, 230, 235), 1, cv2.LINE_AA)
    return frame


def run_camera(cv2, mp, landmarker, library, args):
    camera = cv2.VideoCapture(args.camera)
    session = datetime.now(timezone.utc).isoformat() + ":" + uuid4().hex[:8]
    smoother = StableLabel()
    selected, text = LETTERS[0], ""
    recording = None
    status = "Cadastre >=10 amostras por letra; >=2 letras."
    previous_side = None
    frames, max_hands, last_timestamp = 0, 0, -1
    consecutive_failures, capture_failures = 0, 0
    fps, previous_frame = 0.0, time.monotonic()
    try:
        if not camera.isOpened():
            raise RuntimeError("Webcam indisponivel. Confira --camera e a permissao de Camera do terminal/app no macOS.")
        # Keep the device's default mode unless explicitly requested. Forcing
        # 960x720 can trigger unsupported mode negotiation on USB cameras.
        if args.width:
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        while args.max_frames == 0 or frames < args.max_frames:
            ok, frame = camera.read()
            if not ok or frame is None or frame.size == 0:
                consecutive_failures += 1
                capture_failures += 1
                smoother.update(None)
                previous_side = None
                recording = None
                status = "Coleta interrompida por falha na captura; reinicie com Espaco."
                if consecutive_failures == 1:
                    print("Aviso: frame indisponivel; tentando recuperar a captura.", file=sys.stderr)
                if consecutive_failures >= 20:
                    raise RuntimeError(
                        f"Falha ao ler a webcam {args.camera}: 20 leituras consecutivas sem imagem. "
                        "Feche outros apps de camera, confira a conexao USB e tente "
                        "--width 640 --height 480."
                    )
                if not args.headless and frames:
                    if cv2.waitKey(100) & 0xFF in (27, ord('q')):
                        break
                    if cv2.getWindowProperty("Maos e dedos | Libras", cv2.WND_PROP_VISIBLE) < 1:
                        break
                else:
                    time.sleep(0.1)
                continue
            consecutive_failures = 0
            frame = cv2.flip(frame, 1)  # Mirrored inference and display share the same coordinates.
            now = time.monotonic()
            timestamp = max(last_timestamp + 1, int(now * 1000))
            last_timestamp = timestamp
            image = mp.Image(image_format=mp.ImageFormat.SRGBA, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA))
            result = landmarker.detect_for_video(image, timestamp)
            hands = describe(result, frame.shape[1], frame.shape[0])
            frames += 1
            max_hands = max(max_hands, len(hands))
            single = hands[0] if len(hands) == 1 else None
            side = single["side"] if single else None
            if side != previous_side:
                smoother.update(None)
                if recording:
                    status = "Coleta interrompida: mantenha uma unica mao."
                    recording = None
            previous_side = side
            prediction = library.predict(single["vector"]) if single and recording is None else None
            stable = smoother.update(prediction.label if prediction else None)
            if recording:
                start, next_sample, label = recording
                if now - start >= 4:
                    status = f"Coleta de {label} concluida. Retire a mao e teste."
                    recording = None
                    smoother.update(None)
                elif now >= next_sample and single:
                    library.add(label, single["vector"], session)
                    recording = (start, now + 0.1, label)
                    status = f"Gravando {label}: {library.counts[label]} amostras"
                else:
                    status = "Prepare a pose..." if now - start < 1 else status
            interval = time.monotonic() - previous_frame
            previous_frame = time.monotonic()
            fps = 0.9 * fps + 0.1 / max(interval, 1e-6)
            if args.headless:
                continue
            draw_hands(cv2, frame, hands)
            lines = [
                "MAOS / LIBRAS - poses calibradas", f"FPS do loop: {fps:.1f} | Maos: {len(hands)}",
                f"Letra: {stable or '---'}", f"Texto: {text[-32:]}",
                "",
            ]
            for hand in hands:
                side_name = "direita" if hand["side"] == "Right" else "esquerda"
                lines.append(f"Mao {side_name}: dedos estendidos (estimativa)")
                lines.append(" ".join(name[:3] + (":1" if value else ":0") for name, value in hand["fingers"].items()))
            lines += ["", f"Cadastrar: {selected} ({library.counts.get(selected, 0)} amostras)",
                      "Letras: " + " ".join(LETTERS), "Letra no teclado: selecionar",
                      "Espaco: preparar 1s + coletar 3s", "Enter: adicionar letra | Backspace: apagar",
                      "Q / Esc: sair", "", status,
                      "Use uma mao para cadastrar/reconhecer.",
                      "Sem modelo de Libras pre-treinado.", "Movimentos ainda nao sao reconhecidos."]
            if prediction and prediction.distance is not None:
                lines.append(f"Distancia: {prediction.distance:.3f} (menor=melhor)")
                lines.append(f"Candidatas: {prediction.candidate} / {prediction.alternative}")
                lines.append(f"Margem: {prediction.margin:.3f} (min: {library.min_margin:.3f})")
                reasons = {"accepted": "Pose aceita; aguardando estabilidade",
                           "ambiguous": "Indefinida: letras muito semelhantes",
                           "distant": "Indefinida: longe dos exemplos"}
                lines.append(reasons[prediction.reason])
            cv2.imshow("Maos e dedos | Libras", panel(cv2, frame, lines))
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q')):
                break
            if cv2.getWindowProperty("Maos e dedos | Libras", cv2.WND_PROP_VISIBLE) < 1:
                break
            if key == 32 and recording is None:
                if single:
                    recording = (now, now + 1, selected)
                    smoother.update(None)
                else:
                    status = "Mostre apenas uma mao para iniciar a coleta."
            elif key in (10, 13) and stable and recording is None:
                text += stable
            elif key in (8, 127):
                text = text[:-1]
            elif chr(key).upper() in LETTERS and recording is None:
                selected = chr(key).upper()
        return dict(frames=frames, max_hands=max_hands, loop_fps=round(fps, 1), capture_failures=capture_failures, samples=library.counts)
    finally:
        camera.release()
        if not args.headless:
            cv2.destroyAllWindows()


def main(argv=None):
    argument_parser = parser()
    args = argument_parser.parse_args(argv)
    if args.max_frames < 0 or not 0 < args.threshold < 2 or not 0 <= args.margin < 2:
        argument_parser.error("Use --max-frames >= 0, 0 < --threshold < 2 e 0 <= --margin < 2")
    if args.width < 0 or args.height < 0 or bool(args.width) != bool(args.height):
        argument_parser.error("Informe --width e --height juntos, com valores positivos, ou deixe ambos em 0")
    try:
        if args.download_model:
            download_model(args.model)
            return 0
        if not args.model.is_file():
            raise RuntimeError("Modelo ausente. Execute: hand-libras --download-model")
        os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
        import cv2
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision

        library = PoseLibrary(args.data, args.threshold, args.margin)
        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(args.model), delegate=(BaseOptions.Delegate.GPU if args.delegate == "gpu" else BaseOptions.Delegate.CPU)),
            running_mode=vision.RunningMode.IMAGE if args.image else vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        with vision.HandLandmarker.create_from_options(options) as landmarker:
            if args.image:
                frame = cv2.imread(str(args.image))
                if frame is None:
                    raise RuntimeError(f"Imagem ilegivel: {args.image}")
                # Still images use selfie mirroring too, for consistent handedness/features.
                frame = cv2.flip(frame, 1)
                result = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGBA, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)))
                hands = describe(result, frame.shape[1], frame.shape[0])
                report = dict(hands=[dict(side=h["side"], landmarks=len(h["points"]), fingers=h["fingers"], label=library.predict(h["vector"]).label) for h in hands])
            else:
                report = run_camera(cv2, mp, landmarker, library, args)
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (OSError, RuntimeError, ValueError, ImportError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
