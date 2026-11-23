# au05ctl

Program an **Ulanzi AU05 (Vibe Key)** hotkeys from a script and a JSON file, without Ulanzi Studio.

The AU05 keeps its key/knob bindings in firmware. This tool talks to the dongle's vendor HID interface and
reads/writes those bindings directly.

## Setup (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install hidapi
```

## Use

```powershell
.\.venv\Scripts\python.exe au05ctl.py show                  # read all slots from the device
.\.venv\Scripts\python.exe au05ctl.py apply --dry-run       # diff bindings.json against the device
.\.venv\Scripts\python.exe au05ctl.py apply                 # write changed slots, verify by read-back
.\.venv\Scripts\python.exe au05ctl.py set key2 "Ctrl+Alt+L" # change one slot
.\.venv\Scripts\python.exe au05ctl.py dump mine.json        # save current device bindings
```

Slots: `key1 key2 key3 knob_press knob_right knob_left` (or `0..5`). Up to 4 keys per slot, written like
`Ctrl+Shift+]`, or in the raw Ulanzi form `E0|E1|30`. Edit `bindings.json` and run `apply`.

## Requirements and limits

- **Close Ulanzi Studio first.** Its read thread steals the device's replies (the tool refuses to run if it is open).
  Studio also re-pushes its own saved profile whenever it connects, overwriting what this tool wrote.
- **The AU05 must be awake.** The dongle alone answers heartbeats; slot commands need the device itself.
  Symptom of a sleeping device: `no reply for slot N`.
- Mouse-wheel bindings are not supported (format not captured).
- Whether bindings survive a device power cycle has not been verified.

See [docs/PROTOCOL.md](docs/PROTOCOL.md) for the wire format and how it was derived.

Tested on one AU05, firmware 4.6.3, Windows 10, Ulanzi Studio 3.x. Unofficial; not affiliated with Ulanzi.
Use at your own risk.
