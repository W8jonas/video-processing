"""Explicit in-memory clean-plate capture and reversible full-frame fade."""

from math import ceil


class BackgroundEffect:
    def __init__(self, countdown=5., fade=.5):
        self.countdown, self.fade = countdown, fade
        self.shape = None
        self.clear()

    def clear(self):
        self.background = self.candidate = self.deadline = None
        self.origin = self.target = self.since = 0.
        self.message = 'B: capturar fundo vazio'

    def begin_capture(self, now):
        self.clear()
        self.deadline = now + self.countdown
        self.message = 'Saia da imagem! Captura em andamento.'

    def cancel(self):
        self.candidate = self.deadline = None
        self.message = 'Captura cancelada.'

    def update(self, original, now):
        if self.shape is not None and self.shape != original.shape:
            self.clear()
            self.message = 'Resolucao mudou. Capture o fundo novamente com B.'
        self.shape = original.shape
        if self.deadline is not None and now >= self.deadline:
            self.candidate = original.copy()
            self.deadline = None
            self.message = 'Fundo capturado: ENTER confirma | C descarta | B refaz'

    def confirm(self):
        if self.candidate is None:
            self.message = 'Nenhuma captura pendente. Use B e saia da imagem.'
            return False
        self.background = self.candidate
        self.candidate = None
        self.message = 'Fundo confirmado! I: desaparecer / reaparecer'
        return True

    def strength(self, now):
        progress = 1. if self.fade == 0 else min(1., max(0., (now - self.since) / self.fade))
        return self.origin + (self.target - self.origin) * progress

    def toggle(self, now):
        if self.background is None or self.deadline is not None or self.candidate is not None:
            self.message = 'Confirme o fundo com ENTER antes de desaparecer.'
            return False
        self.origin = self.strength(now)
        self.target = 1. - self.target
        self.since = now
        self.message = 'I: alternar efeito | R: voltar ao vivo | B: novo fundo'
        return True

    def show_live(self):
        self.cancel()
        self.origin = self.target = self.since = 0.
        self.message = 'Ao vivo. I: desaparecer | B: novo fundo'

    def compose(self, cv2, live, now):
        if self.background is None:
            return live.copy()
        return cv2.addWeighted(live, 1. - self.strength(now), self.background,
                               self.strength(now), 0.)

    def status(self, now):
        if self.deadline is not None:
            return f'SAIA DA IMAGEM: {max(0, ceil(self.deadline - now))} s'
        if self.candidate is not None:
            return 'PREVIEW DO FUNDO - ENTER confirma / C descarta'
        if self.background is None:
            return 'SEM FUNDO - pressione B para capturar'
        amount = self.strength(now)
        if 0. < amount < 1.:
            return 'DESAPARECENDO...' if self.target else 'REAPARECENDO...'
        return 'INVISIVEL (foto do fundo)' if amount else 'VISIVEL'


def handle_key(effect, key, now):
    if key == ord('b'):
        effect.begin_capture(now)
    elif key in (10, 13):
        effect.confirm()
    elif key == ord('c'):
        effect.cancel()
    elif key == ord('i'):
        effect.toggle(now)
    elif key == ord('r'):
        effect.show_live()


def local_preview(cv2, effect, published, now):
    """Local instructions and candidate preview never enter the virtual camera."""
    from .output import fit_frame

    if effect.candidate is not None:
        height, width = published.shape[:2]
        preview = fit_frame(cv2, effect.candidate, width, height)
    else:
        preview = published.copy()
    cv2.rectangle(preview, (0, 0), (preview.shape[1], 90), (25, 25, 25), -1)
    for index, text in enumerate((effect.status(now), effect.message,
                                  'B: fundo | ENTER: confirmar | I: efeito | R: ao vivo | H: maos | Q: sair')):
        cv2.putText(preview, text, (12, 24 + index * 26), cv2.FONT_HERSHEY_SIMPLEX,
                    .48, (240, 240, 240), 1, cv2.LINE_AA)
    return preview
