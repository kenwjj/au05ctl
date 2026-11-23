"""Verify what the AU05 actually types: open a window, click it, then press keys / push / turn the knob.

    uv run python tools/keytest.py [log_file]

Each key-down is shown and appended to the log, so you can check every slot (key1..3, knob push,
knob right/left) fires its binding. Reads keyboard input only; nothing is written to the device.
The window closes itself after 120 s.
"""
import sys
import time
import tkinter as tk

log_path = sys.argv[1] if len(sys.argv) > 1 else None
out = open(log_path, 'w', buffering=1) if log_path else None
t0 = time.time()
root = tk.Tk()
root.title('AU05 key test - click here, then use the device')
root.geometry('520x160')
label = tk.Label(root, text='click this window, then use keys/knob\ncloses in 120 s', font=('Segoe UI', 12))
label.pack(expand=True)
MOD_ONLY = {'Control_L', 'Control_R', 'Shift_L', 'Shift_R', 'Alt_L', 'Alt_R'}


def on_key(e):
    if e.keysym in MOD_ONLY:
        return
    mods = [n for bit, n in ((0x4, 'Ctrl'), (0x1, 'Shift')) if e.state & bit]
    line = '%5.1fs %s keysym=%s' % (time.time() - t0, '+'.join(mods + [e.keysym]), e.keysym)
    label.config(text=line)
    print(line, flush=True)
    if out:
        out.write(line + '\n')


root.bind('<KeyPress>', on_key)
root.after(120000, root.destroy)
root.focus_force()
root.mainloop()
