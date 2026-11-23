# AU05 host protocol (as implemented in `au05.py`)

Reverse engineered from Ulanzi Studio for interoperability with the author's own device. Verified on firmware 4.6.3.

## Transport
- USB composite device `VID_FFF1 PID_00DD`. Config channel = HID interface 3, usage page `0xFFFC`, usage `1`.
- Input and output reports are 64 bytes, report id `0x55` (the id is byte 0 of the 64).
- Other interfaces: audio (mic), keyboard/mouse/consumer-control (what the device types when you press a key).

## Frame
```
byte 0        0x55                      report id
bytes 1..56   TEA-ECB(plain[0:56])      seven 8-byte blocks
bytes 57..63  plain[56:63]              not encrypted
```
`plain` is 63 bytes, zero padded. Zero blocks encrypt to `38 90 C4 99 A3 60 AA AD`, which is why captured frames
show a repeating 8-byte pattern.

Cipher: TEA, 32 rounds, delta `0x9E3779B9`, little-endian 32-bit words, fixed key (`KEY` in `au05.py`).
The key is a constant in the vendor's Windows software, not a per-device secret.

## Plaintext messages
| plain | meaning |
|---|---|
| `06 01 23 00 01` | heartbeat (dongle echoes it, even if the device is asleep) |
| `01 06 50 00 <slot> 01 <n> (<type> <value>)*n` | SET shortcut for a slot |
| `01 06 50 01 <slot>` | GET shortcut for a slot |
| `81 06 50 10 <slot> 01 <n> pairs` | ack for SET |
| `81 06 50 11 <slot> 01 <n> pairs` | reply for GET |
| `8b 10 <id> <status> <slot>` | key/knob event (status 1 = down, 0 = up) |

Pairs: `type 2` = HID keyboard usage (`value` = usage id), `type 3` = modifier bitmask
(`01` L-Ctrl `02` L-Shift `04` L-Alt `08` L-Win, `10..80` right-hand). Modifiers are listed first. Max 4 pairs.
Slots: `0,1,2` keys; `3` knob press; `4` knob right; `5` knob left.

## How it was derived
1. Ulanzi Studio's decoded log (mars xlog, raw-deflate blocks) shows `onSetButtonFunction ... content: "E0|10"`
   (HID usages joined by `|`) and the device's JSON-ish acks.
2. `Ulanzi_Studio.dll` contains the same transport stack for older devices: TEA routines, the key in `.data`,
   and the packet builders (heartbeat `0x23`, shortcut `0x50`).
3. Raw frames read from the vendor interface decrypt cleanly with that key, confirming the cipher.
4. A SET/GET sent with that layout is acked by the device; read-back matches.

Gotcha: the first attempt got no replies because the AU05 was asleep. The dongle answered heartbeats anyway.
