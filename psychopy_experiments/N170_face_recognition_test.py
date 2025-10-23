# -*- coding: utf-8 -*-
"""
N170 (Faces vs Cars; Intact vs Scrambled) — PsychoPy + LSL
- Shows all images at the same height, width scaled by each file's native aspect ratio (no squashing).
- 4 classes randomly intermixed; each image shown once.
"""

from psychopy import visual, core, event, logging
from psychopy.hardware import keyboard
from pylsl import StreamInfo, StreamOutlet
from PIL import Image
import os, glob, csv, random
from datetime import datetime

# -------------------- PARAMETERS --------------------
TITLE = "N170 (Faces vs Cars; Intact vs Scrambled)"
FULLSCR = False
WIN_SIZE = [1280, 800]
BG_COLOR = [0.8, 0.8, 0.8]   # light grey
UNITS = 'height'             # make size independent of pixel resolution

STIM_HEIGHT = 0.6            # on-screen height of every stimulus (in 'height' units)
STIM_TIME = 0.300            # 300 ms
ISI_RANGE = (1.100, 1.300)   # seconds
KEY_INTACT = 'right'         # RIGHT arrow = intact (faces, cars)
KEY_SCRAMBLED = 'left'       # LEFT arrow  = scrambled (scrambled faces/cars)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR, 'media', 'N170')
OUT_CSV = os.path.join(BASE_DIR, f"n170_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

# Event codes (ERP CORE)
CODES_FACE_START = 1          # 1–40
CODES_CAR_START  = 41         # 41–80
CODES_SF_START   = 101        # 101–140
CODES_SC_START   = 141        # 141–180
RESP_CORRECT = 201
RESP_INCORRECT = 202

# -------------------- LSL --------------------
info = StreamInfo(name='PsychopyMarkerStream', type='Markers',
                  channel_count=1, channel_format='int32',
                  source_id='n170_faces_cars_unique')
outlet = StreamOutlet(info)

# -------------------- HELPERS --------------------
logging.console.setLevel(logging.INFO)

def write_text(win, text, pos=(0, 0), height=0.045, wrapWidth=1.6, bold=False):
    return visual.TextStim(
        win, text=text, pos=pos, height=height, wrapWidth=wrapWidth,
        bold=bold, color='black', alignText='center', anchorVert='center', units=UNITS
    )

def show_text_and_wait(win, text, wait_keys=('space',), pos=(0, 0.0), height=0.045):
    stim = write_text(win, text, pos=pos, height=height)
    stim.draw(); win.flip()
    kb = keyboard.Keyboard()
    kb.clearEvents(); event.clearEvents()
    kb.waitKeys(keyList=list(wait_keys))

def send_marker_on_flip(win, value):
    win.callOnFlip(outlet.push_sample, [int(value)])

def image_native_size(path):
    """Return (width_px, height_px) using Pillow, for aspect ratio."""
    with Image.open(path) as im:
        return im.size  # (w, h) in pixels

def list_images():
    def sorted_glob(pattern):
        paths = glob.glob(os.path.join(MEDIA_DIR, pattern))
        # sort numerically by trailing number if present
        def key(p):
            name = os.path.splitext(os.path.basename(p))[0]
            tail = ''.join(ch for ch in name if ch.isdigit())
            return (int(tail) if tail.isdigit() else 10**9, name)
        return sorted(paths, key=key)

    faces  = sorted_glob('face_*.jpg')
    cars   = sorted_glob('car_*.jpg')
    sfaces = sorted_glob('scrambled_face_*.jpg') + sorted_glob('face_scrambled_*.jpg')
    scars  = sorted_glob('scrambled_car_*.jpg')  + sorted_glob('car_scrambled_*.jpg')
    return faces, cars, sfaces, scars

def build_trials(faces, cars, sfaces, scars):
    """
    Build trials with per-image event codes and precomputed size (w,h in 'height' units),
    using fixed display height and width scaled by native aspect ratio.
    """
    n = min(40, len(faces), len(cars), len(sfaces), len(scars))
    if n == 0:
        raise RuntimeError(
            f"Need balanced sets in {MEDIA_DIR}: face_*, car_*, scrambled_face_*, scrambled_car_*"
        )
    faces, cars, sfaces, scars = faces[:n], cars[:n], sfaces[:n], scars[:n]

    def make_entries(paths, cls, scrambled, code_start):
        entries = []
        for i, p in enumerate(paths):
            wpx, hpx = image_native_size(p)
            aspect = (wpx / float(hpx)) if hpx > 0 else 1.0
            size_units = (STIM_HEIGHT * aspect, STIM_HEIGHT)  # width, height in 'height' units
            entries.append(dict(
                path=p, cls=cls, scrambled=scrambled, code=code_start + i,
                size=size_units
            ))
        return entries

    trials = []
    trials += make_entries(faces,  'face', False, CODES_FACE_START)
    trials += make_entries(cars,   'car',  False, CODES_CAR_START)
    trials += make_entries(sfaces, 'face', True,  CODES_SF_START)
    trials += make_entries(scars,  'car',  True,  CODES_SC_START)

    random.shuffle(trials)
    return trials

# -------------------- MAIN --------------------
def main():
    win = visual.Window(size=WIN_SIZE, units=UNITS, color=BG_COLOR, fullscr=FULLSCR)
    kb = keyboard.Keyboard()
    mouse = event.Mouse(visible=False, win=win)

    faces, cars, sfaces, scars = list_images()
    trials = build_trials(faces, cars, sfaces, scars)

    # Reusable ImageStim; size will be set per-trial from precomputed aspect
    img = visual.ImageStim(win, image=None, units=UNITS, interpolate=True, autoLog=False)

    instr = (
        f"{TITLE}\n\n"
        "You will see faces, cars, and their scrambled versions.\n"
        f"Press {KEY_INTACT.upper()} for INTACT (faces/cars).\n"
        f"Press {KEY_SCRAMBLED.upper()} for SCRAMBLED (scrambled faces/cars).\n\n"
        f"Stimulus: {int(STIM_TIME*1000)} ms   ISI: {int(ISI_RANGE[0]*1000)}–{int(ISI_RANGE[1]*1000)} ms\n\n"
        "Press SPACE to begin."
    )
    show_text_and_wait(win, instr, wait_keys=('space',))

    # CSV header
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "timestamp_iso", "trial_index", "image_file", "class", "scrambled",
            "marker_code", "resp_key", "correct", "rt_ms", "stim_time_s", "isi_s",
            "shown_width_units", "shown_height_units"
        ])

    # Trial loop
    for t_idx, t in enumerate(trials, start=1):
        kb.clearEvents(); event.clearEvents()
        resp_key = None; rt_ms = None; correct = 0

        # Set image and size (no squashing)
        img.image = t['path']
        img.size = t['size']  # (w,h) with fixed h and width scaled by native aspect

        # Stimulus onset (marker on flip)
        send_marker_on_flip(win, t['code'])
        img.draw()
        stim_on = core.getTime()
        win.flip()

        # Show for STIM_TIME; collect responses but don't shorten timing
        while (core.getTime() - stim_on) < STIM_TIME:
            keys = kb.getKeys(keyList=[KEY_INTACT, KEY_SCRAMBLED, 'escape'], waitRelease=False)
            if keys and resp_key is None:
                k = keys[0].name
                if k == 'escape':
                    win.close(); core.quit()
                if k in (KEY_INTACT, KEY_SCRAMBLED):
                    resp_key = k
                    rt_ms = (core.getTime() - stim_on) * 1000.0

        # Blank ISI (randomized)
        isi = random.uniform(*ISI_RANGE)
        isi_start = core.getTime()
        while (core.getTime() - isi_start) < isi:
            win.flip()
            keys = kb.getKeys(keyList=[KEY_INTACT, KEY_SCRAMBLED, 'escape'], waitRelease=False)
            if keys and resp_key is None:
                k = keys[0].name
                if k == 'escape':
                    win.close(); core.quit()
                if k in (KEY_INTACT, KEY_SCRAMBLED):
                    resp_key = k
                    rt_ms = (core.getTime() - stim_on) * 1000.0

        # Score and push accuracy marker
        if resp_key is not None:
            expect = KEY_SCRAMBLED if t['scrambled'] else KEY_INTACT
            correct = int(resp_key == expect)
            outlet.push_sample([RESP_CORRECT if correct else RESP_INCORRECT])

        # Log
        with open(OUT_CSV, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow([
                datetime.now().isoformat(timespec='milliseconds'),
                t_idx,
                os.path.basename(t['path']),
                t['cls'],
                int(t['scrambled']),
                t['code'],
                resp_key if resp_key else '',
                correct,
                round(rt_ms, 2) if rt_ms else '',
                STIM_TIME,
                round(isi, 3),
                round(t['size'][0], 4),  # width shown (units='height')
                round(t['size'][1], 4)   # height shown (should be STIM_HEIGHT)
            ])

        for k in kb.getKeys(waitRelease=False):
            if k.name == 'escape':
                win.close(); core.quit()

    # End
    end = write_text(
        win,
        f"Session complete.\nTrials: {len(trials)}\nSaved: {os.path.basename(OUT_CSV)}\n\nPress ENTER to exit.",
        height=0.05
    )
    end.draw(); win.flip()
    kb.clearEvents()
    while True:
        keys = kb.getKeys(waitRelease=False)
        if any(k.name in ('return', 'enter', 'escape') for k in keys):
            break
        core.wait(0.01)

    win.close(); core.quit()

if __name__ == "__main__":
    main()
