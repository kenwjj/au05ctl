"""au05ctl - program an Ulanzi AU05 without Ulanzi Studio.

  au05ctl.py show                       read all six slots from the device
  au05ctl.py apply [bindings.json]      write every slot listed in the JSON, verify by read-back
  au05ctl.py apply --dry-run            show what would change, write nothing
  au05ctl.py set key1 "Ctrl+Alt+L"      change one slot
  au05ctl.py dump [out.json]            save the device's current bindings as a JSON file
Slots: key1 key2 key3 knob_press knob_right knob_left   (or 0..5)
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import au05

HERE = Path(__file__).resolve().parent


def slot_id(name):
    name = str(name)
    if name in au05.SLOT_NAMES:
        return au05.SLOT_NAMES[name]
    if name.isdigit() and 0 <= int(name) <= 5:
        return int(name)
    raise SystemExit('unknown slot %r (use %s or 0..5)' % (name, ', '.join(au05.SLOT_NAMES)))


def slot_label(i):
    return next(k for k, v in au05.SLOT_NAMES.items() if v == i)


def app_running():
    if sys.platform != 'win32':  # tasklist is Windows-only, and Ulanzi Studio has no Linux build
        return False
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq UlanziDeck.exe', '/NH'], capture_output=True,
                         text=True).stdout
    return 'UlanziDeck.exe' in out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('show')
    a = sub.add_parser('apply'); a.add_argument('file', nargs='?', default=str(HERE / 'bindings.json'))
    a.add_argument('--dry-run', action='store_true')
    s = sub.add_parser('set'); s.add_argument('slot'); s.add_argument('hotkey')
    d = sub.add_parser('dump'); d.add_argument('file', nargs='?', default='-')
    args = ap.parse_args()

    if app_running():
        sys.exit('Ulanzi Studio is running and would steal replies - close it first.')

    with au05.AU05() as dev:
        if args.cmd == 'show':
            for i in range(6):
                print('%-11s %s' % (slot_label(i), au05.format_pairs(dev.get(i))))
        elif args.cmd == 'dump':
            out = {'bindings': {slot_label(i): au05.format_pairs(dev.get(i)) for i in range(6)}}
            text = json.dumps(out, indent=2) + '\n'
            if args.file == '-':
                print(text, end='')
            else:
                Path(args.file).write_text(text)
        elif args.cmd == 'set':
            i, pairs = slot_id(args.slot), au05.parse_hotkey(args.hotkey)
            dev.set(i, pairs)
            print('%-11s -> %s (verified)' % (slot_label(i), au05.format_pairs(dev.get(i))))
        elif args.cmd == 'apply':
            cfg = json.loads(Path(args.file).read_text(encoding='utf-8'))
            todo = [(slot_id(k), au05.parse_hotkey(v)) for k, v in cfg['bindings'].items()]
            for i, pairs in todo:
                cur = dev.get(i)
                if cur == pairs:
                    print('%-11s %-20s unchanged' % (slot_label(i), au05.format_pairs(pairs)))
                elif args.dry_run:
                    print('%-11s %-20s would change from %s' % (slot_label(i), au05.format_pairs(pairs),
                                                                au05.format_pairs(cur)))
                else:
                    dev.set(i, pairs)
                    print('%-11s %-20s written + verified (was %s)' % (slot_label(i), au05.format_pairs(pairs),
                                                                       au05.format_pairs(cur)))


def cli():
    """Console-script entry point (`au05`)."""
    try:
        main()
    except (au05.DeviceError, ValueError) as e:
        sys.exit('error: %s' % e)


if __name__ == '__main__':
    cli()
