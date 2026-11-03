from io import BytesIO
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from threading import Event, Timer
import time
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs

from hand_esp.app import run_camera
from hand_esp.client import EspClient, ProtocolError
from hand_esp.protocol import (NEUTRAL, FingerState, StableState, ids_from_mask,
                               mask_from_ids, select_hand, state_from_hand)
from hand_esp.publisher import Publisher


def ack(state, sequence):
    return dict(ok=True, mascara=state.mask, sequencia=sequence, dedos=list(state.ids),
                rastreando=state.tracking, mao=state.form(sequence)['mao'])


class ProtocolTests(unittest.TestCase):
    def test_all_sixteen_independent_combinations_round_trip(self):
        for mask in range(16):
            self.assertEqual(mask_from_ids(ids_from_mask(mask)), mask)
        self.assertEqual(ids_from_mask(9), (1, 4))
        self.assertEqual(mask_from_ids((1, 2, 3)), 7)
        self.assertNotEqual(mask_from_ids((1, 4)), len((1, 4)))

    def test_thumb_is_ignored_and_each_other_finger_has_its_own_id(self):
        hand = dict(side='Right', fingers=dict(polegar=True, indicador=True, medio=False, anelar=False, minimo=True))
        self.assertEqual(state_from_hand(hand).ids, (1, 4))
        hand['fingers'].update(indicador=False, minimo=False)
        self.assertEqual(state_from_hand(hand).ids, ())
        self.assertTrue(state_from_hand(hand).tracking)
        hand['finger_quality'] = False
        self.assertEqual(state_from_hand(hand), NEUTRAL)

    def test_invalid_channels_masks_and_tracking_states_are_rejected(self):
        for ids in ((0,), (5,), (1, 1), (True,), ('1',)):
            with self.assertRaises(ValueError):
                mask_from_ids(ids)
        for mask in (-1, 16, True, '1'):
            with self.assertRaises(ValueError):
                ids_from_mask(mask)
        with self.assertRaises(ValueError):
            FingerState(1, False, 'None')

    def test_two_hands_are_never_merged_and_explicit_side_can_be_selected(self):
        right, left = dict(side='Right'), dict(side='Left')
        self.assertIsNone(select_hand([right, left]))
        self.assertIs(select_hand([right, left], 'left'), left)
        self.assertIs(select_hand([right]), right)
        self.assertIsNone(select_hand([left], 'right'))

    def test_stability_requires_time_but_hand_loss_clears_immediately(self):
        gate = StableState(.2)
        state = FingerState(9, True, 'Right')
        self.assertEqual(gate.update(state, 0), NEUTRAL)
        self.assertEqual(gate.update(state, .1), NEUTRAL)
        self.assertEqual(gate.update(state, .21), state)
        self.assertEqual(gate.update(NEUTRAL, .22), NEUTRAL)


class HttpClientTests(unittest.TestCase):
    def setUp(self):
        self.client = EspClient()

    def test_post_uses_form_with_independent_mask_and_validates_ack(self):
        state = FingerState(9, True, 'Right')
        with patch.object(self.client.opener, 'open', return_value=BytesIO(json.dumps(ack(state, 12)).encode())) as request:
            self.client.send(state, 12)
        sent = request.call_args.args[0]
        self.assertEqual(sent.get_method(), 'POST')
        self.assertEqual(sent.full_url, 'http://192.168.0.105/dedos')
        self.assertEqual(parse_qs(sent.data.decode()), {key: [value] for key, value in state.form(12).items()})

    def test_stale_mismatched_and_wrongly_typed_acknowledgements_are_rejected(self):
        state = FingerState(9, True, 'Right')
        for field, value in (('mascara', 3), ('sequencia', 11), ('dedos', [1, 2]),
                             ('dedos', [True, 4]), ('rastreando', 1), ('ok', False)):
            response = ack(state, 12)
            response[field] = value
            with patch.object(self.client, 'request', return_value=response):
                with self.assertRaises(ProtocolError):
                    self.client.send(state, 12)

    def test_v3_firmware_is_reported_as_missing_receiver(self):
        with patch.object(self.client, 'request', return_value=dict(firmware='WIFI OTA HTTP V3')):
            with self.assertRaisesRegex(ProtocolError, 'sem API'):
                self.client.check()

    def test_invalid_json_and_nonobject_responses_are_rejected(self):
        for raw in (b'not json', b'[]', b'x' * 8193):
            with patch.object(self.client.opener, 'open', return_value=BytesIO(raw)):
                with self.assertRaises(ProtocolError):
                    self.client.read_state()

    def test_url_rejects_credentials_and_unexpected_paths(self):
        for url in ('ftp://esp', 'http://user:pass@esp', 'http://esp/command', 'http://esp?x=1'):
            with self.assertRaises(ValueError):
                EspClient(url)


class PublisherTests(unittest.TestCase):
    def test_latest_state_is_delivered_and_close_finishes_with_neutral(self):
        sent, arrived = [], Event()
        target = FingerState(9, True, 'Right')
        def send(state, sequence):
            sent.append(state)
            if state == target:
                arrived.set()
        publisher = Publisher(send, heartbeat=.1, min_interval=.01)
        try:
            publisher.set(target)
            self.assertTrue(arrived.wait(1))
        finally:
            publisher.close(timeout=.5)
        self.assertEqual(sent[-1], NEUTRAL)
        self.assertFalse(publisher.thread.is_alive())

    def test_inflight_old_state_does_not_prevent_final_neutral_or_replay_queued_states(self):
        entered, release = Event(), Event()
        sent = []
        target = FingerState(1, True, 'Right')
        def send(state, sequence):
            sent.append(state)
            if state == target:
                entered.set()
                release.wait(.5)
        publisher = Publisher(send, min_interval=.01)
        publisher.set(target)
        try:
            self.assertTrue(entered.wait(1))
            publisher.set(FingerState(4, True, 'Right'))
            Timer(.02, release.set).start()
        finally:
            publisher.close(timeout=.8)
            release.set()
        self.assertEqual(sent[-1], NEUTRAL)
        self.assertNotIn(FingerState(4, True, 'Right'), sent)

    def test_unchanged_state_is_renewed_with_bounded_rate(self):
        sent, renewed = [], Event()
        def send(state, sequence):
            sent.append(time.monotonic())
            if len(sent) >= 3:
                renewed.set()
        publisher = Publisher(send, heartbeat=.06, min_interval=.03)
        try:
            self.assertTrue(renewed.wait(1))
            self.assertTrue(all(b - a >= .025 for a, b in zip(sent, sent[1:])))
        finally:
            publisher.close(timeout=.5)

    def test_network_failure_is_reported_and_retry_uses_the_latest_target(self):
        arrived = Event()
        sent = []
        target = FingerState(9, True, 'Right')
        def send(state, sequence):
            sent.append(state)
            if len(sent) == 1:
                raise OSError('offline')
            if state == target:
                arrived.set()
        publisher = Publisher(send, min_interval=.01)
        try:
            publisher.set(target)
            self.assertTrue(arrived.wait(2))
            self.assertIsNone(publisher.status().error)
        finally:
            publisher.close(timeout=.5)


class CameraBridgeTests(unittest.TestCase):
    def test_one_and_four_are_published_and_no_hand_releases_them(self):
        hand = dict(side='Right', points=[(.3, .5, 0)] * 21,
                    fingers=dict(indicador=True, medio=False, anelar=False, minimo=True))
        sequence = [(0, [hand]), (.3, [hand]), (.35, [])]
        frame = SimpleNamespace(shape=(480, 640, 3), size=480 * 640 * 3)
        cv2, mp, detector, publisher = (MagicMock() for _ in range(4))
        cv2.VideoCapture.return_value.isOpened.return_value = True
        cv2.flip.return_value = frame
        tick = [-1]
        def read():
            tick[0] += 1
            return True, frame
        cv2.VideoCapture.return_value.read.side_effect = read
        args = SimpleNamespace(camera=1, width=0, height=0, headless=True, max_frames=3, hand='any', hold=.2)
        with patch('hand_esp.app.describe', side_effect=[entry[1] for entry in sequence]), \
                patch('hand_esp.app.time.monotonic', side_effect=lambda: sequence[max(0, tick[0])][0]):
            run_camera(cv2, mp, detector, args, publisher)
        values = [call.args[0] for call in publisher.set.call_args_list]
        self.assertIn(FingerState(9, True, 'Right'), values)
        self.assertEqual(values[-1], NEUTRAL)
        cv2.VideoCapture.return_value.release.assert_called_once()


class FirmwareParserTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('clang++') or shutil.which('g++'), 'C++ compiler not installed')
    def test_led_channels_are_independent_and_disabled_configuration_writes_nothing(self):
        root = Path(__file__).resolve().parents[1]
        source = r'''
#include <cassert>
#include "finger_leds.h"
int main() {
  const uint8_t pins[4] = {16, 5, 4, 13};
  int writes = 0;
  uint8_t levels[17] = {};
  const auto write = [&](uint8_t pin, uint8_t level) { ++writes; levels[pin] = level; };
  fingers::applyLeds(15, true, false, pins, write);
  assert(writes == 0);
  for (uint8_t mask = 0; mask < 16; ++mask) {
    fingers::applyLeds(mask, true, true, pins, write);
    for (uint8_t i = 0; i < 4; ++i) assert(levels[pins[i]] == !!(mask & (1 << i)));
  }
  fingers::applyLeds(15, false, true, pins, write);
  for (uint8_t pin : pins) assert(levels[pin] == 0);
}
'''
        source = '#include <initializer_list>\n' + source
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'leds.cpp').write_text(source)
            subprocess.run([shutil.which('clang++') or shutil.which('g++'), '-std=c++11',
                            '-I', str(root / 'firmware/finger-receiver'), str(path / 'leds.cpp'),
                            '-o', str(path / 'leds')], check=True, capture_output=True)
            subprocess.run([str(path / 'leds')], check=True, capture_output=True)

    @unittest.skipUnless(shutil.which('clang++') or shutil.which('g++'), 'C++ compiler not installed')
    def test_embedded_parser_boundaries_and_all_channel_combinations(self):
        root = Path(__file__).resolve().parents[1]
        source = r'''
#include <cassert>
#include "finger_protocol.h"
int main() {
  uint32_t value = 0;
  assert(fingers::parseUnsigned("4294967295", UINT32_MAX, value) && value == UINT32_MAX);
  assert(!fingers::parseUnsigned("4294967296", UINT32_MAX, value));
  for (const char* bad : {"", "-1", " 1", "1x", "+1", "16"})
    assert(!fingers::parseUnsigned(bad, 15, value));
  for (uint32_t mask = 0; mask < 16; ++mask) {
    assert(fingers::validState(mask, 1, fingers::handCode("direita")));
    assert(!fingers::validState(mask, 1, 0));
    assert(!fingers::validState(mask, 0, 1));
  }
  assert(fingers::validState(0, 0, 0));
  assert(!fingers::validState(16, 1, 1));
  assert(!fingers::validState(1, 2, 1));
  assert(fingers::handCode("unknown") == 255);
}
'''
        source = '#include <initializer_list>\n' + source
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'check.cpp').write_text(source)
            subprocess.run([shutil.which('clang++') or shutil.which('g++'), '-std=c++11',
                            '-I', str(root / 'firmware/finger-receiver'), str(path / 'check.cpp'),
                            '-o', str(path / 'check')], check=True, capture_output=True)
            subprocess.run([str(path / 'check')], check=True, capture_output=True)
