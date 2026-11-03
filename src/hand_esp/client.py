"""Direct local HTTP transport with validated, matching acknowledgements."""

import json
from urllib.parse import urlencode, urlsplit
from urllib.request import ProxyHandler, Request, build_opener

from .protocol import FingerState, HAND_NAMES


class ProtocolError(ValueError):
    pass


class EspClient:
    def __init__(self, base_url='http://192.168.0.105', timeout=.8):
        url = urlsplit(base_url)
        if (url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password
                or url.path not in ('', '/') or url.query or url.fragment):
            raise ValueError('Use a URL base do ESP, por exemplo http://192.168.0.105')
        if timeout <= 0:
            raise ValueError('Timeout deve ser positivo')
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        # Local ESP traffic must not go through corporate/system HTTP proxies.
        self.opener = build_opener(ProxyHandler({}))

    def request(self, path, data=None):
        body = urlencode(data).encode('ascii') if data is not None else None
        headers = {'Accept': 'application/json'}
        if body is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        request = Request(self.base_url + path, data=body, headers=headers)
        with self.opener.open(request, timeout=self.timeout) as response:
            raw = response.read(8193)
        if len(raw) > 8192:
            raise ProtocolError('Resposta HTTP grande demais')
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise ProtocolError('ESP nao retornou JSON valido') from exc
        if not isinstance(result, dict):
            raise ProtocolError('Resposta JSON deve ser um objeto')
        return result

    def check(self):
        health = self.request('/health')
        if type(health.get('finger_api')) is not int or health['finger_api'] != 1:
            raise ProtocolError('Firmware sem API de dedos. Instale o receptor V4 descrito em docs/esp8266.md')
        if health.get('finger_lease_ms') != 2500:
            raise ProtocolError('Tempo de expiracao do receptor incompativel')
        return health

    def read_state(self):
        return self.request('/dedos')

    def send(self, state: FingerState, sequence):
        if type(sequence) is not int or not 0 <= sequence <= 0xFFFFFFFF:
            raise ValueError('Sequencia deve ser uint32')
        ack = self.request('/dedos', state.form(sequence))
        if (ack.get('ok') is not True or type(ack.get('sequencia')) is not int
                or ack['sequencia'] != sequence or type(ack.get('mascara')) is not int
                or ack['mascara'] != state.mask or not isinstance(ack.get('dedos'), list)
                or any(type(value) is not int for value in ack['dedos']) or ack['dedos'] != list(state.ids)
                or type(ack.get('rastreando')) is not bool or ack['rastreando'] != state.tracking
                or ack.get('mao') != HAND_NAMES[state.hand]):
            raise ProtocolError('Confirmacao do ESP nao corresponde ao estado enviado')
        return ack
