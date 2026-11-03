"""Finger IDs are independent channels, never a sum or finger count."""

from dataclasses import dataclass

FINGERS = ((1, 'indicador', 8), (2, 'medio', 12), (3, 'anelar', 16), (4, 'minimo', 20))
HAND_NAMES = {'Right': 'direita', 'Left': 'esquerda', 'None': 'nenhuma'}


def mask_from_ids(ids):
    values = tuple(ids)
    if any(type(value) is not int or value not in range(1, 5) for value in values):
        raise ValueError('Use apenas os dedos 1, 2, 3 e 4')
    if len(set(values)) != len(values):
        raise ValueError('Nao repita o mesmo dedo')
    return sum(1 << (value - 1) for value in values)


def ids_from_mask(mask):
    if type(mask) is not int or not 0 <= mask <= 15:
        raise ValueError('Mascara deve estar entre 0 e 15')
    return tuple(value for value in range(1, 5) if mask & (1 << (value - 1)))


@dataclass(frozen=True)
class FingerState:
    mask: int = 0
    tracking: bool = False
    hand: str = 'None'

    def __post_init__(self):
        ids_from_mask(self.mask)
        if type(self.tracking) is not bool or self.hand not in HAND_NAMES:
            raise ValueError('Estado de rastreamento invalido')
        if self.tracking and self.hand == 'None':
            raise ValueError('Informe qual mao foi rastreada')
        if not self.tracking and (self.mask != 0 or self.hand != 'None'):
            raise ValueError('Sem rastreamento, envie estado neutro')

    @property
    def ids(self):
        return ids_from_mask(self.mask)

    @property
    def label(self):
        return ' + '.join(map(str, self.ids)) if self.ids else 'Nenhum'

    def form(self, sequence):
        return dict(mascara=str(self.mask), sequencia=str(sequence),
                    rastreando='1' if self.tracking else '0', mao=HAND_NAMES[self.hand])


NEUTRAL = FingerState()


def state_from_hand(hand):
    if not hand or not hand.get('finger_quality', True):
        return NEUTRAL
    ids = [value for value, name, _ in FINGERS if hand['fingers'].get(name, False)]
    return FingerState(mask_from_ids(ids), True, hand['side'])


def select_hand(hands, choice='any'):
    if choice == 'any':
        return hands[0] if len(hands) == 1 else None
    wanted = 'Right' if choice == 'right' else 'Left'
    matches = [hand for hand in hands if hand['side'] == wanted]
    return matches[0] if len(matches) == 1 else None


class StableState:
    def __init__(self, hold_seconds=.2):
        self.hold_seconds = hold_seconds
        self.reset()

    def reset(self):
        self.current = NEUTRAL
        self.candidate = None
        self.since = None

    def update(self, state, now):
        if not state.tracking:
            self.reset()
            return self.current
        if state != self.candidate:
            self.candidate, self.since = state, now
        if now - self.since >= self.hold_seconds:
            self.current = state
        return self.current
