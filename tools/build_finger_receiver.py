#!/usr/bin/env python3
"""Stage private Wi-Fi settings under .build and compile the finger receiver."""

import argparse
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--secrets', type=Path, required=True)
    args = parser.parse_args()
    if not args.secrets.is_file():
        parser.error('Arquivo secrets.h nao encontrado')
    stage = ROOT / '.build/staging/finger-receiver'
    build = ROOT / '.build/finger-receiver'
    stage.mkdir(parents=True, exist_ok=True)
    for name in ('finger-receiver.ino', 'finger_protocol.h', 'finger_leds.h',
                 'leds_config.example.h', 'status_image.h', 'secrets.example.h'):
        shutil.copyfile(ROOT / 'firmware/finger-receiver' / name, stage / name)
    config = ROOT / 'firmware/finger-receiver/leds_config.h'
    staged_config = stage / 'leds_config.h'
    if config.is_file():
        shutil.copyfile(config, staged_config)
    elif staged_config.exists():
        staged_config.unlink()
    destination = stage / 'secrets.h'
    destination.touch(mode=0o600, exist_ok=True)
    destination.chmod(0o600)
    destination.write_bytes(args.secrets.read_bytes())
    subprocess.run(['arduino-cli', 'compile', '--fqbn', 'esp8266:esp8266:nodemcuv2',
                    '--build-path', str(build), str(stage)], check=True)
    print('Firmware compilado:', build / 'finger-receiver.ino.bin')
    print('Binario e configuracao privada ficam em .build/, ignorado pelo Git.')


if __name__ == '__main__':
    main()
