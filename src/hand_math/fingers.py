"""Drawing-specific extension scores and per-finger temporal hysteresis.

Scores describe geometry, not model confidence. Libras classification is unchanged.
"""

from math import dist, exp, isfinite

from hand_libras.core import FINGERS, angle


def ramp(value, low, high):
    return max(0.0, min(1.0, (value - low) / (high - low)))


def extension_scores(points):
    if len(points) != 21 or any(len(p) != 3 or not all(isfinite(v) for v in p) for p in points):
        return None
    if dist(points[0], points[9]) < 1e-8:
        return None
    scores = {}
    for name, (mcp, pip, dip, tip) in FINGERS.items():
        first = angle(points[mcp], points[pip], points[dip])
        second = angle(points[pip], points[dip], points[tip])
        if name == 'polegar':
            # Thumb opposition differs from the other fingers. Natural lateral
            # opening need not make the CMC/MCP/IP chain perfectly straight.
            width = max(1e-8, dist(points[5], points[17]))
            spread = ramp(dist(points[tip], points[5]) / width, .25, .85)
            bend = .55 * ramp(second, 110, 155) + .45 * ramp(first, 95, 155)
            scores[name] = bend * (.35 + .65 * spread)
        else:
            length = sum(dist(points[a], points[b]) for a, b in ((mcp, pip), (pip, dip), (dip, tip)))
            reach = (dist(points[tip], points[0]) - dist(points[pip], points[0])) / max(length, 1e-8)
            knuckle = angle(points[0], points[mcp], points[pip])
            scores[name] = (.55 * ramp(first, 130, 165) + .2 * ramp(second, 120, 165)
                            + .25 * ramp(reach, -.12, .15)) * (.25 + .75 * ramp(knuckle, 85, 140))
    return scores


def attach_world_points(hands, result):
    """Keep world landmarks for drawing without modifying the Libras pipeline."""
    world = result.hand_world_landmarks
    if isinstance(world, (list, tuple)):
        for hand, landmarks in zip(hands, world):
            hand['world_points'] = tuple((p.x, p.y, p.z) for p in landmarks)


class FingerTracker:
    def __init__(self, on=.64, off=.38, hold=.1, tau=.065):
        self.on, self.off, self.hold, self.tau = on, off, hold, tau
        self.reset()

    def reset(self):
        self.states = {}
        self.previous = None
        self.count = None

    def update(self, hands, now):
        if len(hands) != self.count or (self.previous is not None and now - self.previous > .35):
            self.reset()
        dt = 0 if self.previous is None else max(0, now - self.previous)
        self.previous, self.count = now, len(hands)
        alpha = 1 - exp(-dt / self.tau)
        output = []
        for side, original in enumerate(sorted(hands, key=lambda hand: hand['points'][0][0])):
            hand = dict(original)
            points = hand.get('world_points')
            if points is None:
                # Allows explicitly supplied states in offline fixtures; real
                # MediaPipe results always supply world landmarks above.
                scores = {name: float(hand['fingers'].get(name, False)) for name in FINGERS}
            else:
                scores = extension_scores(points)
            hand['finger_quality'] = scores is not None
            if scores is None:
                self.states.pop(side, None)
                hand.update(fingers={name: False for name in FINGERS}, finger_scores={}, finger_pending={})
                output.append(hand)
                continue
            state = self.states.get(side)
            if state is None:
                state = {name: dict(score=score, active=score >= self.on, candidate=None, since=None)
                         for name, score in scores.items()}
                self.states[side] = state
            for name, raw_score in scores.items():
                finger = state[name]
                finger['score'] += alpha * (raw_score - finger['score'])
                score = finger['score']
                desired = True if score >= self.on else False if score <= self.off else finger['active']
                if desired == finger['active']:
                    finger['candidate'] = finger['since'] = None
                else:
                    if finger['candidate'] != desired:
                        finger['candidate'], finger['since'] = desired, now
                    if now - finger['since'] >= self.hold:
                        finger['active'] = desired
                        finger['candidate'] = finger['since'] = None
            hand['fingers'] = {name: info['active'] for name, info in state.items()}
            hand['finger_scores'] = {name: info['score'] for name, info in state.items()}
            hand['finger_pending'] = {name: info['candidate'] is not None for name, info in state.items()}
            output.append(hand)
        return output
