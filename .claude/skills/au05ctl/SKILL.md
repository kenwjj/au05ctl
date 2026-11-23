---
name: au05ctl
description: Read or change the hotkeys of the user's Ulanzi AU05 Vibe Key (3 keys + knob) with the au05ctl CLI, without Ulanzi Studio. Use when the user wants to see, set, back up or bulk-edit AU05 key/knob bindings, or edit bindings.json.
---

# au05ctl - program the Ulanzi AU05 from the command line

The project uses **uv**. From the repo root (normally `C:\Users\Kenwjj\au05ctl`) run `uv sync` once, then use
`uv run au05 <command>`. From any other folder use the launcher `C:\Users\Kenwjj\au05ctl\au05.cmd <command>`.
If `au05` was installed globally (`uv tool install .`), plain `au05 <command>` works too.

## Commands (prefix with `uv run`, e.g. `uv run au05 show`)
| goal | command |
|---|---|
| read what is on the device | `au05 show` |
| back up current bindings | `au05 dump backup.json` |
| preview a config change | `au05 apply --dry-run` |
| write `bindings.json` to the device | `au05 apply` |
| change one slot | `au05 set key2 "Ctrl+Alt+L"` |

Slots: `key1 key2 key3 knob_press knob_right knob_left` (or `0..5`).
Hotkeys: `Ctrl+Shift+]`, `Alt+F4`, `NumPad Enter`, or raw HID usages `E0|E1|30`. Max 4 keys per slot.
Modifiers: Ctrl Shift Alt Win (+ `R` prefix for right-hand). Mouse-wheel bindings are NOT supported.

## Preconditions - check before running
1. **Ulanzi Studio must be closed.** It steals the device's replies; the CLI aborts if `UlanziDeck.exe` runs.
   Do not kill the user's app without asking. Note Studio re-pushes its own saved profile when it connects,
   overwriting what this tool wrote.
2. **The AU05 must be awake.** `error: no reply for slot N` almost always means it is asleep: ask the user to
   press a key or turn the knob, then retry. (The dongle alone still answers heartbeats.)

## Workflow for changes
1. `au05 show` (or `dump backup.json`) so the original is recoverable.
2. Edit `bindings.json` (omit slots to leave them unchanged) or use `set`.
3. `au05 apply --dry-run`, show the diff to the user, then `au05 apply`. Each write is read back and verified.
4. Report what changed. Offer to restore from the backup if the user dislikes it.

## Don't
- Don't write to the device without the user asking for a change; `show`/`dump`/`--dry-run` are read-only.
- Don't hand-roll HID writes; the frame format is TEA-encrypted (see `docs/PROTOCOL.md`). Use `au05.py`.
- Run `uv run pytest` after editing `au05.py`; tests need no hardware. Add dependencies with `uv add`, never pip.
