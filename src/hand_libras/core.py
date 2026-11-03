"""Geometry and template matching, independent of camera and ML dependencies."""

from collections import Counter, deque
from dataclasses import dataclass
import json
from math import acos, degrees, dist, isfinite, sqrt
from pathlib import Path

# Intentionally restricted to an initial subset of static configurations.
LETTERS = tuple("ABCDEFILOSUVW")
FEATURE_VERSION = 1
MIN_SAMPLES = 10
CONFUSION_PAIRS = (frozenset(("A", "S")), frozenset(("U", "V")))
FINGERS = {
    "polegar": (1, 2, 3, 4),
    "indicador": (5, 6, 7, 8),
    "medio": (9, 10, 11, 12),
    "anelar": (13, 14, 15, 16),
    "minimo": (17, 18, 19, 20),
}
CONNECTIONS = tuple(
    edge
    for joints in FINGERS.values()
    for edge in zip((0,) + joints, joints)
) + ((5, 9), (9, 13), (13, 17))


def features(points, handedness, aspect=1.0):
    """Remove translation/scale, mirror left hands, retain camera orientation.

    Input is MediaPipe normalized image landmarks. x and z use image width;
    convert them to image-height units before computing distances.
    """
    if handedness not in ("Left", "Right"):
        raise ValueError("Lateralidade invalida")
    if len(points) != 21 or not isfinite(aspect) or aspect <= 0:
        raise ValueError("Esperados 21 pontos e proporcao positiva")
    if any(len(p) != 3 or not all(isfinite(v) for v in p) for p in points):
        raise ValueError("Coordenadas invalidas")
    wrist = points[0]
    centered = [
        ((p[0] - wrist[0]) * aspect, p[1] - wrist[1], (p[2] - wrist[2]) * aspect)
        for p in points
    ]
    scale = dist(centered[0], centered[9])
    if scale < 1e-6:
        raise ValueError("Mao degenerada: pulso e base do medio coincidem")
    mirror = -1 if handedness == "Left" else 1
    return tuple(v for x, y, z in centered for v in (mirror * x / scale, y / scale, z / scale))


def angle(a, b, c):
    u = tuple(x - y for x, y in zip(a, b))
    v = tuple(x - y for x, y in zip(c, b))
    norm = sqrt(sum(x * x for x in u) * sum(x * x for x in v))
    if norm < 1e-12:
        return 0.0
    cosine = max(-1.0, min(1.0, sum(x * y for x, y in zip(u, v)) / norm))
    return degrees(acos(cosine))


def finger_states(world_points):
    """Heuristic extension flags, not a linguistic classifier."""
    result = {}
    for name, (mcp, pip, dip, tip) in FINGERS.items():
        straight = angle(world_points[mcp], world_points[pip], world_points[dip]) > 155
        straight &= angle(world_points[pip], world_points[dip], world_points[tip]) > 150
        # Avoid calling a straight finger folded at the MCP 'extended'.
        straight &= dist(world_points[tip], world_points[0]) > dist(world_points[pip], world_points[0]) * 1.1
        result[name] = bool(straight)
    return result


def pair_geometry(vector, pair):
    """Rotation-invariant local cues, learned from the existing labeled samples.

    Distances use the same palm scale as stored features. These are geometric
    descriptors, not hardcoded linguistic thresholds or new training labels.
    """
    points = [vector[i:i + 3] for i in range(0, 63, 3)]
    if pair == frozenset(("A", "S")):
        return tuple(dist(points[thumb], points[anchor]) for thumb in (3, 4) for anchor in (5, 9, 17))
    if pair == frozenset(("U", "V")):
        index = tuple(a - b for a, b in zip(points[8], points[5]))
        middle = tuple(a - b for a, b in zip(points[12], points[9]))
        return (dist(points[8], points[12]), angle(index, (0, 0, 0), middle) / 90)
    raise ValueError("Par de confusao desconhecido")


def rms_distance(a, b):
    return sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))


def nearest_score(distances):
    return sum(sorted(distances)[:3]) / 3


@dataclass(frozen=True)
class Prediction:
    label: str | None
    distance: float | None = None
    margin: float | None = None
    candidate: str | None = None
    alternative: str | None = None
    reason: str = "insufficient_samples"


class PoseLibrary:
    """Small local nearest-template baseline with distance and ambiguity rejection."""

    def __init__(self, path: Path, threshold=0.18, min_margin=0.035):
        self.path = path
        self.threshold = threshold
        self.min_margin = min_margin
        self.samples = {}
        if path.exists():
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    label, vector = record["label"], record["features"]
                    self._validate(label, vector)
                    if record["version"] != FEATURE_VERSION:
                        raise ValueError("Versao de features incompativel")
                    self.samples.setdefault(label, []).append(tuple(vector))
                except (ValueError, KeyError, TypeError) as exc:
                    raise ValueError(f"{path}, linha {number}: amostra invalida ({exc})") from exc

    @staticmethod
    def _validate(label, vector):
        if label not in LETTERS:
            raise ValueError("Letra fora do subconjunto estatico inicial")
        if len(vector) != 63 or not all(isfinite(v) for v in vector):
            raise ValueError("Esperadas 63 coordenadas finitas")

    def add(self, label, vector, session):
        self._validate(label, vector)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = dict(version=FEATURE_VERSION, label=label, features=list(vector), session=session)
        with self.path.open("a") as output:
            output.write(json.dumps(record, allow_nan=False) + "\n")
        self.samples.setdefault(label, []).append(tuple(vector))

    @property
    def counts(self):
        return {label: len(vectors) for label, vectors in self.samples.items()}

    def predict(self, vector):
        if len(vector) != 63 or not all(isfinite(v) for v in vector):
            raise ValueError("Feature invalida")
        scores = []
        for label, samples in self.samples.items():
            if len(samples) < MIN_SAMPLES:
                continue
            scores.append((nearest_score(rms_distance(vector, sample) for sample in samples), label))
        # One enrolled class is insufficient for even a basic ambiguity check.
        if len(scores) < 2:
            return Prediction(None)
        scores.sort()
        distance, label = scores[0]
        margin = scores[1][0] - distance
        alternative = scores[1][1]
        pair = frozenset((label, alternative))
        if pair in CONFUSION_PAIRS:
            query_geometry = pair_geometry(vector, pair)
            refined = []
            for _, candidate in scores[:2]:
                # Match a template jointly by whole-hand pose and local cues;
                # do not combine distances to unrelated individual templates.
                refined.append((nearest_score(
                    sqrt(0.5 * rms_distance(vector, sample) ** 2
                         + 0.5 * rms_distance(query_geometry, pair_geometry(sample, pair)) ** 2)
                    for sample in self.samples[candidate]
                ), candidate))
            refined.sort()
            distance, label = refined[0]
            alternative = refined[1][1]
            margin = refined[1][0] - distance
            raw_distance = next(score for score, candidate in scores if candidate == label)
            # Keep rejection against other letters in the original metric.
            if raw_distance > self.threshold:
                return Prediction(None, raw_distance, margin, label, alternative, "distant")
            if len(scores) > 2 and scores[2][0] - raw_distance < self.min_margin:
                return Prediction(None, distance, margin, label, scores[2][1], "ambiguous")
        accepted = distance <= self.threshold and margin >= self.min_margin
        reason = "accepted" if accepted else ("distant" if distance > self.threshold else "ambiguous")
        return Prediction(label if accepted else None, distance, margin, label, alternative, reason)


class StableLabel:
    """Require a full recent window; clear immediately on loss or ambiguity."""

    def __init__(self, size=7):
        self.history = deque(maxlen=size)

    def update(self, label):
        if label is None:
            self.history.clear()
            return None
        self.history.append(label)
        winner, votes = Counter(self.history).most_common(1)[0]
        if len(self.history) == self.history.maxlen and winner == label and votes >= self.history.maxlen - 1:
            return winner
        return None
