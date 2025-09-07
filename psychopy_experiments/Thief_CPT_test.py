# CTP P300 CIT — PsychoPy + LSL (Mouse + JPG images)
# Place this file in: visual-evoke-potentials/psychopy-experiments/
# Place S1 images (JPG) in: visual-evoke-potentials/psychopy-experiments/media/

from psychopy import visual, core, event, logging
from psychopy.visual import Window
from psychopy.hardware import keyboard
from pylsl import StreamInfo, StreamOutlet

import os, random, csv
from datetime import datetime

# -----------------------
# CONFIG
# -----------------------
TITLE = "CTP P300 CIT (mouse, JPG)"
NUM_TRIALS = 200                 # total trials (each has S1 & S2)
PROB_PROBE = 0.20                # S1: probe probability
PROB_S2_TARGET = 0.20            # S2: target probability

# Timing
PRETRIAL_FIX = 0.5               # fixation before S1
S1_DISPLAY_TIME = 0.30           # S1 on-screen (s)
QUIET_MIN, QUIET_MAX = 1.2, 1.8  # silent interval before S2 (s)
S2_DISPLAY_TIME = 0.60           # S2 on-screen (s)
POST_TRIAL_ITI = 0.50            # ITI after S2 (s)

# Window
fullscr = False
win_size = [1280, 800]
bg_color = [0.5, 0.5, 0.5]
units = 'pix'

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR, 'media')
OUT_CSV = os.path.join(BASE_DIR, f"ctp_cit_mouse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

# S1 image set (JPG) — 6 files total, 1 is PROBE, 4 are IRRELEVANTS, 1 extra
ITEM_FILES = [
    "item_01.jpg",
    "item_02.jpg",
    "item_03.jpg",
    "item_04.jpg",
    "item_05.jpg",
    "item_06.jpg",
]
PROBE_FILE = "item_01.jpg"        # <- the actually stolen item
IMAGE_SIZE = (380, 380)

# Mouse mapping (PsychoPy order is [left, middle, right])
LEFT_IDX  = 0
RIGHT_IDX = 2

# Responses
# R1 = “I saw it” during S1: any mouse click (left OR right)
# R2 = differential during S2:
#       right-click = TARGET
#       left-click  = NON-TARGET
QUIT_KEYS = ['escape']

# S2 number strings (can be swapped to images later)
S2_TARGET_STRING = "7"                    # target symbol
S2_NONTARGET_POOL = list("12345689")      # non-target symbols (exclude 7)

# LSL markers
# S1 markers: 1..6 map to S1 item identity
MARK_S2_TARGET   = 101
MARK_S2_NONTARGET= 102

# -----------------------
# LSL stream (on-flip)
# -----------------------
info = StreamInfo(name='PsychopyMarkerStream', type='Markers',
                  channel_count=1, channel_format='int32',
                  source_id='uniqueid_ctp_cit_mouse')
outlet = StreamOutlet(info)

def send_marker_on_flip(win, value):
    win.callOnFlip(outlet.push_sample, [int(value)])

# -----------------------
# UI helpers
# -----------------------
def write_text(win, text, pos=(0, 0), height=0.04, wrapWidth=1.6, bold=False, color='black'):
    return visual.TextStim(
        win, text=text, pos=pos, height=height, wrapWidth=wrapWidth,
        bold=bold, color=color, alignText='center', anchorVert='center', units='height'
    )

def show_text_and_wait(win, text, wait_keys=('space',), pos=(0, 0), height=0.045):
    stim = write_text(win, text, pos=pos, height=height)
    stim.draw(); win.flip()
    kb = keyboard.Keyboard(); kb.clearEvents(); event.clearEvents()
    kb.waitKeys(keyList=list(wait_keys))

def draw_crosshair(win, size=0.05, color='black'):
    return visual.TextStim(win, text='+', height=size, color=color, bold=True, units='height')

# -----------------------
# Safety checks
# -----------------------
if len(ITEM_FILES) != 6:
    raise ValueError("ITEM_FILES must list exactly 6 files.")
missing = [f for f in ITEM_FILES if not os.path.isfile(os.path.join(MEDIA_DIR, f))]
if missing:
    raise FileNotFoundError("Missing media files:\n  " + "\n  ".join(missing))
if PROBE_FILE not in ITEM_FILES:
    raise ValueError("PROBE_FILE must be in ITEM_FILES.")

# Map S1 items to codes 1..6
item_to_marker = {fname: idx for idx, fname in enumerate(ITEM_FILES, start=1)}
IRRELEVANTS = [f for f in ITEM_FILES if f != PROBE_FILE]

# -----------------------
# Build S1 sequence
# -----------------------
n_probe = int(round(NUM_TRIALS * PROB_PROBE))
n_irrel = NUM_TRIALS - n_probe
s1_types = (['probe'] * n_probe) + (['irrelevant'] * n_irrel)
random.shuffle(s1_types)

# -----------------------
# Main
# -----------------------
def main():
    logging.console.setLevel(logging.INFO)
    win = visual.Window(size=win_size, units=units, color=bg_color, fullscr=fullscr)
    kb = keyboard.Keyboard(); kb.clearEvents()
    mouse = event.Mouse(visible=True, win=win)

    # Preload S1 images (.jpg)
    image_cache = {
        f: visual.ImageStim(win, image=os.path.join(MEDIA_DIR, f), size=IMAGE_SIZE)
        for f in ITEM_FILES
    }

    # S2 visual (number strings)
    s2_text = visual.TextStim(win, text="", height=0.18, color='black', units='height')

    # Instructions
    show_text_and_wait(
        win,
        ("Each trial has 2 parts:\n\n"
         "1) You will see a picture of an item\n"
         "Click LEFT mouse button as soon as you see it\n"
         "2) You will see the number: \n"
         "   RIGHT click for TARGET number (7).\n"
         "   LEFT click for NON-TARGET\n\n"
         "Try to respond quickly and correctly."
         "Press SPACE to begin.\n\n"),
        wait_keys=('space',), pos=(0, 0), height=0.045
    )

    # Show the TARGET explicitly once (participants must recognize it)
    tgt_msg = write_text(win,
        f"This is the TARGET number for S2: {S2_TARGET_STRING}\n"
        "RIGHT-click when you see it during the task.\n"
        "Press any key to continue.",
        pos=(0, 0.35), height=0.045
    )
    tgt_msg.draw()
    
    # Big preview of the target number
    target_preview = visual.TextStim(
        win, text=S2_TARGET_STRING, height=0.25, color='black',
        units='height', pos=(0, -0.05)
    )
    target_preview.draw()
    
    win.flip()
    kb.waitKeys()
    
    cross = draw_crosshair(win, color='black')
    global_clock = core.Clock()


    # CSV
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "timestamp_iso", "trial_index",
            "s1_type", "s1_file", "s1_marker", "s1_rt_ms", "s1_button",
            "s2_type", "s2_symbol", "s2_marker", "s2_rt_ms", "s2_button"
        ])

    # Trials
    for t_idx, s1_type in enumerate(s1_types, start=1):
        # ---------- Pre-trial fixation ----------
        cross.draw(); win.flip(); core.wait(PRETRIAL_FIX)

        # ---------- S1 (probe or irrelevant) ----------
        if s1_type == 'probe':
            s1_file = PROBE_FILE
        else:
            s1_file = random.choice(IRRELEVANTS)
        s1_marker = item_to_marker[s1_file]
        s1_stim = image_cache[s1_file]

        # Present S1 and send marker at flip
        s1_stim.draw()
        send_marker_on_flip(win, s1_marker)
        win.flip()
        s1_onset = global_clock.getTime()

        # Collect R1 during S1_DISPLAY_TIME (any mouse button)
        s1_rt_ms, s1_button = None, ""
        mouse.clickReset()
        t0 = core.getTime()
        while (core.getTime() - t0) < S1_DISPLAY_TIME:
            buttons, times = mouse.getPressed(getTime=True)  # (left, middle, right)
            if any(buttons):
                if buttons[LEFT_IDX]:
                    s1_button = 'left'
                elif buttons[RIGHT_IDX]:
                    s1_button = 'right'
                else:
                    s1_button = 'middle'
                s1_rt_ms = (global_clock.getTime() - s1_onset) * 1000.0
                break
            # keep S1 on screen
            s1_stim.draw(); win.flip()

        # Clear to fixation
        cross.draw(); win.flip()

        # ---------- Quiet interval before S2 ----------
        core.wait(random.uniform(QUIET_MIN, QUIET_MAX))

        # ---------- S2 (target or non-target) ----------
        s2_is_target = (random.random() < PROB_S2_TARGET)
        if s2_is_target:
            s2_type = 'target'
            s2_symbol = S2_TARGET_STRING
            s2_marker = MARK_S2_TARGET
        else:
            s2_type = 'non-target'
            s2_symbol = random.choice(S2_NONTARGET_POOL)
            s2_marker = MARK_S2_NONTARGET

        s2_text.text = s2_symbol
        s2_text.draw()
        send_marker_on_flip(win, s2_marker)
        win.flip()
        s2_onset = global_clock.getTime()

        # Collect R2 during S2_DISPLAY_TIME
        s2_rt_ms, s2_button = None, ""
        mouse.clickReset()
        t1 = core.getTime()
        while (core.getTime() - t1) < S2_DISPLAY_TIME:
            buttons, times = mouse.getPressed(getTime=True)
            if any(buttons):
                # RIGHT click = target; LEFT click = non-target
                if s2_is_target and buttons[RIGHT_IDX]:
                    s2_button = 'right'
                    s2_rt_ms = (global_clock.getTime() - s2_onset) * 1000.0
                    break
                if (not s2_is_target) and buttons[LEFT_IDX]:
                    s2_button = 'left'
                    s2_rt_ms = (global_clock.getTime() - s2_onset) * 1000.0
                    break
            s2_text.draw(); win.flip()

        # ---------- ITI ----------
        cross.draw(); win.flip(); core.wait(POST_TRIAL_ITI)

        # ---------- Log ----------
        with open(OUT_CSV, "a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([
                datetime.now().isoformat(timespec='milliseconds'), t_idx,
                s1_type, s1_file, s1_marker,
                f"{s1_rt_ms:.2f}" if s1_rt_ms is not None else "", s1_button,
                s2_type, s2_symbol, s2_marker,
                f"{s2_rt_ms:.2f}" if s2_rt_ms is not None else "", s2_button
            ])

        # Optional progress ping
        if t_idx % 40 == 0:
            msg = write_text(win, f"Progress: {t_idx}/{NUM_TRIALS}\nPress any key to continue.", height=0.05)
            msg.draw(); win.flip()
            keyboard.Keyboard().waitKeys()

    # End
    end = write_text(win, f"Task complete!\nData saved to:\n{os.path.basename(OUT_CSV)}\n\nPress Enter to exit.", height=0.05)
    end.draw(); win.flip()
    kb = keyboard.Keyboard()
    while True:
        keys = kb.getKeys(waitRelease=False)
        if any(k.name in ('return', 'enter') for k in keys): break
        if any(k.name in QUIT_KEYS for k in keys): break
        core.wait(0.01)

    win.close(); core.quit()

if __name__ == "__main__":
    main()
