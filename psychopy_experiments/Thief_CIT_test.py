# P300 Concealed Information Test (3-stimulus CIT) — PsychoPy + LSL
# Project layout:
#   visual-evoke-potentials/
#     psychopy-experiments/   <- put this script here
#     media/                  <- put the 6 item images here
#
# Dependencies:
#   pip install psychopy pylsl
#
# Task:
# - 6 items (same category): 1 PROBE, 1 TARGET, 4 IRRELEVANTS
# - TARGET => RIGHT mouse click; others => LEFT mouse click
# - Stimulus visible up to 1.0 s (response window); total trial length 2.0 s
# - LSL marker (1..6) at stimulus onset
# - Trial data saved to CSV

from psychopy import visual, core, event, logging
from psychopy.visual import Window
from psychopy.hardware import keyboard
from pylsl import StreamInfo, StreamOutlet

import os
import csv
import random
from datetime import datetime

# ----------------------
# Config (style-aligned)
# ----------------------
TITLE = "P300 CIT (Probe/Target/Irrelevants)"
REPS_PER_ITEM = 40                 # 6 * 40 = 240 trials
PRETRIAL_TIME = 0.5                # fixation before each trial
STIM_DISPLAY_TIME = 1.0            # max on-screen & response window (s)
TRIAL_TOTAL_LEN = 2.0              # total trial length (s)

# Window settings (aligned to your oddball script)
fullscr = False
win_size = [1280, 800]
bg_color = [0.5, 0.5, 0.5]         # grey
units = 'pix'

# Mouse mapping (PsychoPy returns [left, middle, right])
LEFT_IDX = 0
RIGHT_IDX = 2

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR, 'media')
OUT_CSV = os.path.join(BASE_DIR, f"cit_p300_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

# -------------
# Item files
# -------------
# Put your 6 image files in ../media and list them here (filenames only).
ITEM_FILES = [
    "item_01.jpg",
    "item_02.jpg",
    "item_03.jpg",
    "item_04.jpg",
    "item_05.jpg",
    "item_06.jpg",
]

# Choose which is PROBE and which is TARGET (by filename)
PROBE_FILE = "item_02.jpg"
TARGET_FILE = "item_06.jpg"

# Image display size (pixels)
IMAGE_SIZE = (400, 400)

# ----------------
# LSL definitions
# ----------------
# We’ll use marker codes 1..6 mapped to the 6 items
info = StreamInfo(name='PsychopyMarkerStream', type='Markers',
                  channel_count=1, channel_format='int32',
                  source_id='uniqueid_cit_p300')
outlet = StreamOutlet(info)

# ---------
# Helpers
# ---------
def write_text(win, text, pos=(0, 0), height=0.04, wrapWidth=1.5, bold=False, color='black'):
    return visual.TextStim(
        win, text=text, pos=pos, height=height, wrapWidth=wrapWidth,
        bold=bold, color=color, alignText='center', anchorVert='center', units='height'
    )

def show_text_and_wait(win, text, wait_keys=('space',), pos=(0, 0), height=0.04):
    stim = write_text(win, text, pos=pos, height=height)
    stim.draw()
    win.flip()
    kb = keyboard.Keyboard()
    kb.clearEvents()
    event.clearEvents()
    keys = kb.waitKeys(keyList=list(wait_keys))
    return keys

def draw_crosshair(win, size=0.05, color='black'):
    return visual.TextStim(win, text='+', height=size, color=color, bold=True, units='height')

def send_marker_on_flip(win, value):
    """Schedule an LSL marker to be sent exactly on the next flip."""
    win.callOnFlip(outlet.push_sample, [int(value)])

# -----------------------
# Safety / sanity checks
# -----------------------
if len(ITEM_FILES) != 6:
    raise ValueError("ITEM_FILES must contain exactly 6 filenames.")

if PROBE_FILE not in ITEM_FILES:
    raise ValueError("PROBE_FILE must be one of ITEM_FILES.")
if TARGET_FILE not in ITEM_FILES:
    raise ValueError("TARGET_FILE must be one of ITEM_FILES.")
if PROBE_FILE == TARGET_FILE:
    raise ValueError("PROBE_FILE and TARGET_FILE must be different.")

missing = [f for f in ITEM_FILES if not os.path.isfile(os.path.join(MEDIA_DIR, f))]
if missing:
    raise FileNotFoundError("Missing media files:\n  " + "\n  ".join(missing))

# ----------------------
# Build item structures
# ----------------------
# Map item to marker code 1..6
item_to_marker = {fname: idx for idx, fname in enumerate(ITEM_FILES, start=1)}
IRRELEVANTS = [f for f in ITEM_FILES if f not in (PROBE_FILE, TARGET_FILE)]

# -----------------
# Main experiment
# -----------------
def main():
    # Logging & window
    logging.console.setLevel(logging.INFO)
    win = visual.Window(size=win_size, units=units, color=bg_color, fullscr=fullscr)
    mouse = event.Mouse(visible=True, win=win)
    kb = keyboard.Keyboard()

    # Preload images
    image_cache = {
        f: visual.ImageStim(win, image=os.path.join(MEDIA_DIR, f), size=IMAGE_SIZE)
        for f in ITEM_FILES
    }

    # Instructions (style-consistent)
    show_text_and_wait(
        win,
        ('Press SPACE to begin.\n\n'
         'You will see items from the same category.\n\n'
         'RESPONSES (mouse):\n'
         '  - RIGHT click for the TARGET item. We will show you the target on the next screen.\n'
         '  - LEFT click for ALL OTHER items\n\n'
         f'The image will stay up to {STIM_DISPLAY_TIME:.1f}s; try to respond as quickly and accurately as possible.\n'),
        wait_keys=('space',), pos=(0, 0), height=0.045
    )

    # Show the TARGET explicitly once (participants must recognize it)
    tgt_msg = write_text(win, "This is the TARGET. RIGHT-click when you see it during the task.\nPress any key to continue.", pos=(0, 0.35), height=0.045)
    tgt_msg.draw()
    image_cache[TARGET_FILE].pos = (0, -50)  # nudge down a bit in pix
    image_cache[TARGET_FILE].draw()
    win.flip()
    kb.waitKeys()

    # Prepare trials (6 items × 40 reps = 240; randomized)
    trials = []
    for fname in ITEM_FILES:
        trials.extend([fname] * REPS_PER_ITEM)
    random.shuffle(trials)

    def classify(fname):
        if fname == PROBE_FILE:
            return 'probe'
        elif fname == TARGET_FILE:
            return 'target'
        else:
            return 'irrelevant'

    # Crosshair for baseline/fixation
    cross = draw_crosshair(win, color='black')

    # CSV setup
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "timestamp_iso", "trial_index",
            "item_file", "item_type", "marker_code",
            "rt_ms", "button", "correct"
        ])

    # Run trials
    global_clock = core.Clock()
    trial_clock = core.Clock()

    for t_idx, fname in enumerate(trials, start=1):
        item_type = classify(fname)
        marker_code = item_to_marker[fname]
        stim = image_cache[fname]

        # Reset per-trial
        mouse.clickReset()
        kb.clearEvents()

        # Pre-trial fixation
        cross.draw()
        win.flip()
        core.wait(PRETRIAL_TIME)

        # Stimulus onset: draw + send marker on flip
        stim.draw()
        send_marker_on_flip(win, marker_code)
        win.flip()
        stim_onset = global_clock.getTime()

        # Collect mouse within STIM_DISPLAY_TIME
        responded = False
        resp_button = None  # 'left' or 'right'
        rt_ms = None

        # Keep the stimulus on screen while collecting
        trial_clock.reset()
        while trial_clock.getTime() < STIM_DISPLAY_TIME:
            # Check clicks
            buttons, times = mouse.getPressed(getTime=True)
            if any(buttons):
                if buttons[LEFT_IDX]:
                    resp_button = 'left'
                    responded = True
                    rt_ms = (global_clock.getTime() - stim_onset) * 1000.0
                    break
                elif buttons[RIGHT_IDX]:
                    resp_button = 'right'
                    responded = True
                    rt_ms = (global_clock.getTime() - stim_onset) * 1000.0
                    break

            # Keep showing the image during the response window
            stim.draw()
            win.flip()

        # After response window, clear screen to fixation to finish trial
        # (ensures total trial = TRIAL_TOTAL_LEN)
        elapsed = PRETRIAL_TIME + STIM_DISPLAY_TIME
        remain = max(0.0, TRIAL_TOTAL_LEN - elapsed)
        cross.draw()
        win.flip()
        core.wait(remain)

        # Correctness: TARGET => right; others => left; no response => incorrect
        if responded:
            if item_type == 'target':
                correct = (resp_button == 'right')
            else:
                correct = (resp_button == 'left')
        else:
            correct = False

        # Log to CSV
        with open(OUT_CSV, "a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([
                datetime.now().isoformat(timespec='milliseconds'),
                t_idx,
                fname,
                item_type,
                marker_code,
                f"{rt_ms:.2f}" if rt_ms is not None else "",
                resp_button if resp_button else "",
                int(correct)
            ])

        # Optional lightweight progress every 40 trials
        if t_idx % 40 == 0:
            p = write_text(win, f"Progress: {t_idx}/{len(trials)}\n\nPress any key to continue.", pos=(0, 0), height=0.05)
            p.draw()
            win.flip()
            kb.waitKeys()

    # End screen
    end_text = write_text(win, f'Task complete!\n\nData saved to:\n{os.path.basename(OUT_CSV)}\n\nPress Enter to exit.', pos=(0, 0), height=0.05)
    end_text.draw()
    win.flip()

    # Wait for Enter/Esc
    while True:
        keys = kb.getKeys(waitRelease=False)
        if any(k.name in ('return', 'enter') for k in keys):
            break
        if any(k.name == 'escape' for k in keys):
            break
        core.wait(0.01)

    core.wait(0.3)
    win.close()
    core.quit()

if __name__ == "__main__":
    main()
