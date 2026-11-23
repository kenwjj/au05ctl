"""Hardware-free tests. Vectors marked [device] were captured from / confirmed by a real AU05 (fw 4.6.3)."""
import json
from pathlib import Path

import pytest

import au05
import au05ctl

PAD = bytes.fromhex('38 90 C4 99 A3 60 AA AD')  # TEA(0) with the fixed key


def frame_from_first_block(block_hex: str) -> bytes:
    return bytes([0x55]) + bytes.fromhex(block_hex) + PAD * 6 + bytes(7)


# ---- framing -------------------------------------------------------------------------------
def test_zero_block_encrypts_to_known_pad():  # [device]
    assert au05.encode_frame(b'')[1:9] == PAD


def test_heartbeat_frame_vector():  # [device] heartbeat reply captured off the wire
    frame = frame_from_first_block('24 56 9E F2 28 E1 45 A1')
    plain = au05.decode_frame(frame)
    assert plain[:5] == bytes([0x06, 0x01, 0x23, 0x00, 0x01])
    assert au05.encode_frame(plain) == frame


def test_key_event_frame_vector():  # [device] key press event: 8b 10 <id> <down=1/up=0> <slot>
    plain = au05.decode_frame(frame_from_first_block('73 8A 16 2B 8F 7D E6 E1'))
    assert plain[:5] == bytes([0x8B, 0x10, 0x6E, 0x01, 0x03])


def test_roundtrip_all_blocks():
    plain = bytes(range(63))
    assert au05.decode_frame(au05.encode_frame(plain)) == plain


def test_frame_is_64_bytes_with_report_id():
    f = au05.encode_frame(b'\x01\x02')
    assert len(f) == 64 and f[0] == 0x55


def test_decode_rejects_foreign_frames():
    with pytest.raises(ValueError):
        au05.decode_frame(bytes(64))


# ---- hotkeys -------------------------------------------------------------------------------
@pytest.mark.parametrize('text,pairs', [
    ('Ctrl+Shift', [(3, 0x01), (3, 0x02)]),
    ('Ctrl+N', [(3, 0x01), (2, 0x11)]),
    ('Ctrl+Shift+]', [(3, 0x01), (3, 0x02), (2, 0x30)]),
    ('Esc', [(2, 0x29)]),
    ('NumPad Enter', [(2, 0x58)]),
    ('E0|E1|30', [(3, 0x01), (3, 0x02), (2, 0x30)]),   # raw Ulanzi form
    ('E0|10', [(3, 0x01), (2, 0x10)]),                   # Ctrl+M as the vendor app encodes it
    ('alt+f4', [(3, 0x04), (2, 0x3D)]),
    ('shift+ctrl+a', [(3, 0x02), (3, 0x01), (2, 0x04)]),  # modifiers sorted before keys
])
def test_parse_hotkey(text, pairs):
    assert au05.parse_hotkey(text) == pairs


@pytest.mark.parametrize('bad', ['', 'Ctrl+Blorp', 'Ctrl+Shift+Alt+A+B'])
def test_parse_hotkey_rejects(bad):
    with pytest.raises(ValueError):
        au05.parse_hotkey(bad)


@pytest.mark.parametrize('text', ['Ctrl+Shift', 'Ctrl+N', 'Ctrl+Shift+]', 'Esc', 'NumPad Enter', 'Ctrl+Alt+L'])
def test_format_roundtrip(text):
    assert au05.format_pairs(au05.parse_hotkey(text)) == text


# ---- packets (layout verified against device replies) --------------------------------------
def test_set_packet_layout():
    p = au05.build_set(0, au05.parse_hotkey('Ctrl+Shift'))
    assert len(p) == 63
    assert p[:11] == bytes.fromhex('01 06 50 00 00 01 02 03 01 03 02')  # device acked exactly this


def test_get_packet_layout():
    assert au05.build_get(4)[:5] == bytes.fromhex('01 06 50 01 04')


def test_parse_real_get_replies():  # [device]
    assert au05.format_pairs(au05.parse_reply(bytes.fromhex('81 06 50 11 04 01 03 03 01 03 02 02 30'))) == 'Ctrl+Shift+]'
    assert au05.format_pairs(au05.parse_reply(bytes.fromhex('81 06 50 11 01 01 01 02 58'))) == 'NumPad Enter'


# ---- transaction logic with a fake HID device ----------------------------------------------
class FakeHid:
    """Behaves like the device: stores slots, acks SET (0x10), answers GET (0x11), sprinkles heartbeats."""
    def __init__(self, awake=True):
        self.slots, self.awake, self.out = {}, awake, []

    def write(self, frame):
        plain = au05.decode_frame(bytes(frame))
        if self.awake and plain[2] == 0x50:
            slot, get = plain[4], plain[3] & 1
            if not get:
                self.slots[slot] = plain[6:7 + 2 * plain[6]]
            body = self.slots.get(slot, bytes([0]))
            reply = bytearray(63)
            reply[0:5] = bytes([0x81, 0x06, 0x50, 0x11 if get else 0x10, slot])
            reply[5] = 1
            reply[6:6 + len(body)] = body
            self.out.append(au05.encode_frame(bytes([0x06, 0x01, 0x23, 0, 1])))  # unrelated heartbeat first
            self.out.append(au05.encode_frame(bytes(reply)))
        return 64

    def read(self, n, ms):
        return list(self.out.pop(0)) if self.out else []

    def error(self):
        return 'fake'

    def close(self):
        pass


def fake_device(awake=True):
    d = au05.AU05.__new__(au05.AU05)
    d.dev = FakeHid(awake)
    return d


def test_set_get_roundtrip_ignores_unrelated_frames():
    d = fake_device()
    d.set(1, au05.parse_hotkey('Ctrl+Alt+L'))
    assert au05.format_pairs(d.get(1)) == 'Ctrl+Alt+L'


def test_asleep_device_raises_clear_error(monkeypatch):
    monkeypatch.setattr(au05.time, 'time', iter(range(0, 10_000, 1)).__next__)  # fast-forward the timeouts
    with pytest.raises(au05.DeviceError, match='awake'):
        fake_device(awake=False).get(0)


# ---- config / CLI helpers ------------------------------------------------------------------
def test_shipped_bindings_json_is_valid():
    cfg = json.loads((Path(au05ctl.HERE) / 'bindings.json').read_text(encoding='utf-8'))
    for slot, hotkey in cfg['bindings'].items():
        assert au05ctl.slot_id(slot) in range(6)
        au05.parse_hotkey(hotkey)


def test_slot_names():
    assert [au05ctl.slot_id(n) for n in ('key1', 'knob_left', '3')] == [0, 5, 3]
    with pytest.raises(SystemExit):
        au05ctl.slot_id('nope')
