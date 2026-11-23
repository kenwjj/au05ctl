"""Ulanzi AU05 (Vibe Key) host protocol - standalone, no Ulanzi software needed.

Reverse engineered from Ulanzi Studio 3.x; verified against a real AU05 (fw 4.6.3).

Transport : vendor HID interface VID 0xFFF1 / PID 0x00DD, usage page 0xFFFC, report id 0x55, 64-byte reports.
Frame     : 0x55 | TEA-ECB(plain[0:56]) | plain[56:63]        (plain = 63 bytes, zero padded)
Cipher    : TEA, 32 rounds, little-endian dwords, fixed 16-byte key (KEY).
Shortcut  : plain = 01 06 50 <b3> <slot> 01 <count> (<type> <value>)*count ...
              b3 = 0 SET / 1 GET.  Reply = 81 06 50 10|11 <slot> 01 <count> pairs...
              pair type 2 = HID keyboard usage, 3 = modifier bitmask (1 L-Ctrl 2 L-Shift 4 L-Alt 8 L-Win,
              0x10..0x80 = right-hand versions), max 4 pairs per slot.
Slots     : 0,1,2 = the three keys; 3 = knob press; 4 = knob rotate right; 5 = knob rotate left.
The device must be awake; the dongle alone answers heartbeats but not slot commands.
"""
import struct
import time

VID, PID, USAGE_PAGE = 0xFFF1, 0x00DD, 0xFFFC
REPORT_ID = 0x55
KEY = struct.unpack('<4I', bytes.fromhex('cabaa5ca6d8a2abcba9e5acaca8bb89b'))
M, DELTA = 0xFFFFFFFF, 0x9E3779B9
SLOT_NAMES = {'key1': 0, 'key2': 1, 'key3': 2, 'knob_press': 3, 'knob_right': 4, 'knob_left': 5}
T_KEY, T_MOD = 2, 3
MAX_PAIRS = 4


# ---- TEA framing ---------------------------------------------------------------------------
def _enc(v0, v1, k=KEY):
    s = 0
    for _ in range(32):
        s = (s + DELTA) & M
        v0 = (v0 + ((((v1 << 4) + k[0]) ^ (v1 + s) ^ ((v1 >> 5) + k[1])) & M)) & M
        v1 = (v1 + ((((v0 << 4) + k[2]) ^ (v0 + s) ^ ((v0 >> 5) + k[3])) & M)) & M
    return v0, v1


def _dec(v0, v1, k=KEY):
    s = (DELTA * 32) & M
    for _ in range(32):
        v1 = (v1 - ((((v0 << 4) + k[2]) ^ (v0 + s) ^ ((v0 >> 5) + k[3])) & M)) & M
        v0 = (v0 - ((((v1 << 4) + k[0]) ^ (v1 + s) ^ ((v1 >> 5) + k[1])) & M)) & M
        s = (s - DELTA) & M
    return v0, v1


def encode_frame(plain: bytes) -> bytes:
    plain = plain.ljust(63, b'\0')[:63]
    out = bytearray([REPORT_ID])
    for i in range(7):
        out += struct.pack('<2I', *_enc(*struct.unpack('<2I', plain[i * 8:i * 8 + 8])))
    return bytes(out + plain[56:63])


def decode_frame(frame: bytes) -> bytes:
    if len(frame) < 64 or frame[0] != REPORT_ID:
        raise ValueError('not a 0x55 frame')
    out = bytearray()
    for i in range(7):
        out += struct.pack('<2I', *_dec(*struct.unpack('<2I', frame[1 + i * 8:9 + i * 8])))
    return bytes(out + frame[57:64])


# ---- hotkey names <-> HID usages -----------------------------------------------------------
MODS = {'ctrl': 0x01, 'control': 0x01, 'shift': 0x02, 'alt': 0x04, 'win': 0x08, 'gui': 0x08, 'meta': 0x08,
        'rctrl': 0x10, 'rshift': 0x20, 'ralt': 0x40, 'altgr': 0x40, 'rwin': 0x80}
KEYS = {chr(ord('a') + i): 0x04 + i for i in range(26)}
KEYS.update({str(n): 0x1E + n - 1 for n in range(1, 10)})
KEYS['0'] = 0x27
KEYS.update({'f%d' % n: 0x3A + n - 1 for n in range(1, 13)})
KEYS.update({'f%d' % n: 0x68 + n - 13 for n in range(13, 25)})
KEYS.update({'enter': 0x28, 'return': 0x28, 'esc': 0x29, 'escape': 0x29, 'backspace': 0x2A, 'tab': 0x2B,
             'space': 0x2C, '-': 0x2D, '=': 0x2E, '[': 0x2F, ']': 0x30, '\\': 0x31, ';': 0x33, "'": 0x34,
             '`': 0x35, ',': 0x36, '.': 0x37, '/': 0x38, 'capslock': 0x39, 'printscreen': 0x46,
             'scrolllock': 0x47, 'pause': 0x48, 'insert': 0x49, 'home': 0x4A, 'pageup': 0x4B, 'delete': 0x4C,
             'end': 0x4D, 'pagedown': 0x4E, 'right': 0x4F, 'left': 0x50, 'down': 0x51, 'up': 0x52,
             'numlock': 0x53, 'numpad/': 0x54, 'numpad*': 0x55, 'numpad-': 0x56, 'numpad+': 0x57,
             'numpadenter': 0x58, 'numpad enter': 0x58, 'menu': 0x65, 'mute': 0x7F})
KEYS.update({'numpad%d' % n: 0x59 + n - 1 for n in range(1, 10)})
KEYS['numpad0'] = 0x62
KEYS['numpad.'] = 0x63
USAGE_NAME = {}
for _n, _u in KEYS.items():
    USAGE_NAME.setdefault(_u, _n)
MOD_NAME = {0x01: 'Ctrl', 0x02: 'Shift', 0x04: 'Alt', 0x08: 'Win', 0x10: 'RCtrl', 0x20: 'RShift', 0x40: 'RAlt',
            0x80: 'RWin'}
USAGE_MOD = {0xE0: 0x01, 0xE1: 0x02, 0xE2: 0x04, 0xE3: 0x08, 0xE4: 0x10, 0xE5: 0x20, 0xE6: 0x40, 0xE7: 0x80}


def parse_hotkey(text: str):
    """'Ctrl+Shift+]' or raw Ulanzi 'E0|E1|30' -> [(type, value), ...]."""
    text = text.strip()
    if '|' in text or (len(text) <= 3 and all(c in '0123456789abcdefABCDEF' for c in text) and text not in KEYS):
        pairs = []
        for tok in text.split('|'):
            u = int(tok, 16)
            pairs.append((T_MOD, USAGE_MOD[u]) if u in USAGE_MOD else (T_KEY, u))
    else:
        pairs = []
        parts = text.replace(' + ', '+').split('+') if text != '+' else ['+']
        if text.endswith('++'):  # "Ctrl++"
            parts = text[:-2].split('+') + ['+']
        for p in parts:
            k = p.strip().lower()
            if k in MODS:
                pairs.append((T_MOD, MODS[k]))
            elif k in KEYS:
                pairs.append((T_KEY, KEYS[k]))
            else:
                raise ValueError('unknown key %r in %r' % (p, text))
    pairs.sort(key=lambda p: p[0] != T_MOD)  # modifiers first, as the vendor app does
    if not 1 <= len(pairs) <= MAX_PAIRS:
        raise ValueError('a slot holds 1..%d keys, got %d in %r' % (MAX_PAIRS, len(pairs), text))
    return pairs


def format_pairs(pairs) -> str:
    out = []
    for t, v in pairs:
        if t == T_MOD:
            out += [MOD_NAME[b] for b in sorted(MOD_NAME) if v & b]
        else:
            n = USAGE_NAME.get(v)
            if v == 0x58:
                out.append('NumPad Enter')
            elif n and n.startswith('numpad') and len(n) > 6:
                out.append('NumPad' + n[6:].upper())
            else:
                out.append(n.title() if n and len(n) > 1 else (n.upper() if n else 'usage%02X' % v))
    return '+'.join(out)


# ---- packets -------------------------------------------------------------------------------
def build_set(slot: int, pairs) -> bytes:
    p = bytearray(63)
    p[0:4] = bytes([0x01, 0x06, 0x50, 0x00])
    p[4], p[5], p[6] = slot, 0x01, len(pairs)
    for i, (t, v) in enumerate(pairs):
        p[7 + 2 * i], p[8 + 2 * i] = t & 0x7F, v
    return bytes(p)


def build_get(slot: int) -> bytes:
    p = bytearray(63)
    p[0:5] = bytes([0x01, 0x06, 0x50, 0x01, slot])
    return bytes(p)


def parse_reply(plain: bytes):
    count = plain[6]
    return [(plain[7 + 2 * i], plain[8 + 2 * i]) for i in range(min(count, MAX_PAIRS))]


class DeviceError(RuntimeError):
    pass


class AU05:
    def __init__(self):
        import hid  # imported lazily so the pure functions/tests work without hidapi
        path = next((d['path'] for d in hid.enumerate(VID, PID) if d['usage_page'] == USAGE_PAGE), None)
        if path is None:
            raise DeviceError('AU05 dongle not found (VID FFF1 PID 00DD, usage page FFFC)')
        self.dev = hid.device()
        self.dev.open_path(path)

    def close(self):
        self.dev.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def _tx(self, plain: bytes):
        if self.dev.write(encode_frame(plain)) < 0:
            raise DeviceError('HID write failed: %s' % self.dev.error())

    def _rx(self, ms):
        d = self.dev.read(64, ms)
        if not d:
            return None
        try:
            return decode_frame(bytes(d))
        except ValueError:
            return None

    def _transact(self, plain: bytes, slot: int, timeout=1.5, tries=3):
        """send a 0x50 command, return the matching reply (byte0 0x81, cmd 0x50, same slot)."""
        for _ in range(tries):
            while self._rx(10):          # drop stale frames (heartbeats, key events)
                pass
            self._tx(plain)
            end = time.time() + timeout
            while time.time() < end:
                r = self._rx(50)
                if r and r[0] == 0x81 and r[2] == 0x50 and r[4] == slot:
                    return r
        raise DeviceError('no reply for slot %d - is the AU05 awake (press a key) and Ulanzi Studio closed?' % slot)

    def get(self, slot: int):
        return parse_reply(self._transact(build_get(slot), slot))

    def set(self, slot: int, pairs, verify=True):
        self._transact(build_set(slot, pairs), slot)
        if verify and self.get(slot) != list(pairs):
            raise DeviceError('slot %d read back %r, expected %r' % (slot, self.get(slot), pairs))
