#!/usr/bin/env python3
"""Upload the additive finger receiver, retaining existing Wi-Fi, HTTP and OTA."""

import argparse
import ast
import importlib.util
import json
import logging
from pathlib import Path
import re
import socket
import sys
import time
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]


def read_ota_password(path):
    match = re.search(r'OTA_PASSWORD\s*\[\s*\]\s*=\s*("(?:\\.|[^"\\])*")', path.read_text())
    if not match:
        raise ValueError('OTA_PASSWORD nao encontrado no arquivo informado')
    try:
        password = ast.literal_eval(match.group(1))
    except (ValueError, SyntaxError):
        raise ValueError('Nao foi possivel ler OTA_PASSWORD') from None
    if not password:
        raise ValueError('OTA_PASSWORD vazio')
    return password


def health(opener, host):
    with opener.open(f'http://{host}/health', timeout=2) as response:
        return json.loads(response.read(4096))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='192.168.0.105')
    parser.add_argument('--secrets', type=Path, required=True)
    parser.add_argument('--force', action='store_true', help='Substituir um receptor API 1 ja instalado')
    parser.add_argument('--image', type=Path, default=ROOT / '.build/finger-receiver/finger-receiver.ino.bin')
    parser.add_argument('--espota', type=Path, default=Path.home() / 'Library/Arduino15/packages/esp8266/hardware/esp8266/3.1.2/tools/espota.py')
    args = parser.parse_args()
    try:
        with args.image.open('rb') as image:
            if image.read(1) != b'\xe9':
                raise ValueError('Use um binario ESP8266 valido')
        opener = build_opener(ProxyHandler({}))
        before = health(opener, args.host)
        print('Firmware anterior:', before.get('firmware'), flush=True)
        if not before.get('ota'):
            raise ValueError('O ESP nao informa OTA ativo; upload cancelado')
        if before.get('finger_api') == 1 and not args.force:
            print('Receptor de dedos ja instalado; nenhum upload realizado.')
            return 0
        password = read_ota_password(args.secrets)
        remote_ip = socket.gethostbyname(args.host)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect((remote_ip, 8266))
            local_ip = probe.getsockname()[0]
        spec = importlib.util.spec_from_file_location('finger_espota', args.espota)
        uploader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(uploader)
        uploader.PROGRESS = False
        logging.basicConfig(level=logging.WARNING)
        print(f'OTA: {remote_ip}; retorno TCP: {local_ip}:8267', flush=True)
        result = uploader.serve(remote_ip, local_ip, 8266, 8267, password, str(args.image), uploader.FLASH)
        if result:
            raise RuntimeError('Upload nao confirmado. Nenhum reenvio automatico; consulte /health antes de repetir.')
        for _ in range(20):
            time.sleep(1)
            try:
                after = health(opener, args.host)
            except (OSError, ValueError):
                continue
            if after.get('finger_api') == 1 and after.get('ota'):
                print('Receptor confirmado apos reboot:', json.dumps(after), flush=True)
                return 0
        raise RuntimeError('Upload confirmado, mas reboot/API nao verificados; nenhum reenvio automatico.')
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
