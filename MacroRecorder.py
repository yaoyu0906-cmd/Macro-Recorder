"""
Macro Recorder v2.2
Made By Alvin
"""

import tkinter as tk
import threading
import time
import json
import ctypes
from ctypes import wintypes
from tkinter import filedialog
import keyboard

user32 = ctypes.windll.user32

# =========================
# CONFIG
# =========================

START_KEY = 'ctrl+alt+r'
STOP_KEY = 'ctrl+alt+s'
PLAY_KEY = 'ctrl+alt+p'
EMERGENCY_KEY = 'f8'

# =========================
# LOW LEVEL
# =========================

class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

def get_mouse_pos():
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def set_mouse_pos(x, y):
    user32.SetCursorPos(x, y)

def press(vk):
    user32.keybd_event(vk, 0, 0, 0)

def release(vk):
    user32.keybd_event(vk, 0, 2, 0)

def mouse_event(flag):
    user32.mouse_event(flag, 0, 0, 0, 0)

def key_state(vk):
    return user32.GetAsyncKeyState(vk) & 0x8000 != 0

# =========================
# GLOBAL
# =========================

recording = False
replaying = False
stop_replay = False

events = []
loop_forever = False

# =========================
# RECORD
# =========================

def record():
    global recording, events
    recording = True
    events = []

    last_keys = {vk: False for vk in range(256)}
    last_mouse = (0, 0)
    last_buttons = {"left": False, "right": False}

    start = time.time()

    while recording:
        t = time.time() - start

        x, y = get_mouse_pos()
        if (x, y) != last_mouse:
            events.append({"time": t, "type": "mouse", "x": x, "y": y})
            last_mouse = (x, y)

        for vk in range(256):
            now = key_state(vk)

            if now and not last_keys[vk]:
                events.append({"time": t, "type": "down", "vk": vk})

            if not now and last_keys[vk]:
                events.append({"time": t, "type": "up", "vk": vk})

            last_keys[vk] = now

        left = key_state(0x01)
        right = key_state(0x02)

        if left and not last_buttons["left"]:
            events.append({"time": t, "type": "click_down", "button": "left"})
        if not left and last_buttons["left"]:
            events.append({"time": t, "type": "click_up", "button": "left"})
        last_buttons["left"] = left

        if right and not last_buttons["right"]:
            events.append({"time": t, "type": "click_down", "button": "right"})
        if not right and last_buttons["right"]:
            events.append({"time": t, "type": "click_up", "button": "right"})
        last_buttons["right"] = right

        time.sleep(0.008)  # ~120 FPS

# =========================
# TRIM
# =========================

def trim_events():
    global events
    if not events:
        return

    cutoff = 0.25
    end_time = events[-1]["time"]
    events = [e for e in events if e["time"] < end_time - cutoff]

# =========================
# REPLAY
# =========================

def replay():
    global replaying, stop_replay

    if replaying or not events:
        return

    replaying = True
    stop_replay = False

    try:
        while True:
            prev_event = None

            for e in events:
                if stop_replay:
                    return

                if prev_event:
                    delay = e["time"] - prev_event["time"]
                else:
                    delay = e["time"]

                start_t = time.time()
                end = start_t + delay

                if e["type"] == "mouse" and prev_event and prev_event["type"] == "mouse":
                    x1, y1 = prev_event["x"], prev_event["y"]
                    x2, y2 = e["x"], e["y"]

                    while time.time() < end:
                        if stop_replay:
                            return

                        t = (time.time() - start_t) / delay if delay > 0 else 1

                        x = int(x1 + (x2 - x1) * t)
                        y = int(y1 + (y2 - y1) * t)

                        set_mouse_pos(x, y)
                        time.sleep(0.001)

                else:
                    # wait timing
                    while time.time() < end:
                        if stop_replay:
                            return
                        time.sleep(0.0005)

                    if e["type"] == "down":
                        press(e["vk"])
                    elif e["type"] == "up":
                        release(e["vk"])
                    elif e["type"] == "click_down":
                        mouse_event(2 if e["button"] == "left" else 8)
                    elif e["type"] == "click_up":
                        mouse_event(4 if e["button"] == "left" else 16)

                prev_event = e

            if not loop_forever:
                break

    finally:
        # safety release
        for vk in range(256):
            release(vk)

        replaying = False

# =========================
# CONTROL
# =========================

def start_record():
    threading.Thread(target=record, daemon=True).start()
    status.config(text="Recording...")

def stop_record():
    global recording
    recording = False
    trim_events()
    status.config(text="Stopped (trimmed)")

def start_replay():
    threading.Thread(target=replay, daemon=True).start()
    status.config(text="Replaying...")

def emergency_stop():
    global stop_replay
    stop_replay = True

    for vk in range(256):
        release(vk)

    status.config(text="EMERGENCY STOP")

def toggle_loop():
    global loop_forever
    loop_forever = not loop_forever
    loop_label.config(text=f"Loop: {'∞' if loop_forever else 'Off'}")

# =========================
# UI
# =========================

root = tk.Tk()
root.title("Macro Recorder v2.2")

tk.Button(root, text="🔴 Record", command=start_record).pack(pady=5)
tk.Button(root, text="⏹ Stop", command=stop_record).pack(pady=5)
tk.Button(root, text="▶ Replay", command=start_replay).pack(pady=5)
tk.Button(root, text="🔁 Toggle Loop", command=toggle_loop).pack(pady=5)

tk.Button(root, text="💾 Save", command=lambda: json.dump(events, open(filedialog.asksaveasfilename(defaultextension=".json"), "w"))).pack(pady=5)
tk.Button(root, text="📂 Load", command=lambda: globals().update(events=json.load(open(filedialog.askopenfilename())))).pack(pady=5)

loop_label = tk.Label(root, text="Loop: Off")
loop_label.pack()

# =========================
# HOTKEYS
# =========================

keyboard.add_hotkey(START_KEY, start_record)
keyboard.add_hotkey(STOP_KEY, stop_record)
keyboard.add_hotkey(PLAY_KEY, start_replay)
keyboard.add_hotkey(EMERGENCY_KEY, emergency_stop)

root.mainloop()
