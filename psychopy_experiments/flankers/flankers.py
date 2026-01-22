# -*- coding: utf-8 -*-
"""
Flanker Task (5-char arrows) — parameterized, block feedback, early stop
Respond to CENTER arrow: '<' = Left Shift, '>' = Right Shift
"""

from psychopy import visual, core, event, logging
from psychopy.hardware import keyboard
import numpy as np
import random, os, csv
from datetime import datetime
from pylsl import StreamInfo, StreamOutlet

# -------------------- Parameters you asked to expose --------------------
STIM_TIME      = 0.200            # seconds stimulus on-screen
ISI_INTERVAL   = (1.200, 1.400)   # seconds (min, max), randomized each trial
BLOCK_SIZE     = 50               # trials per block
N_TRIALS_MIN   = 600              # minimum total trials before we can stop early
N_TRIALS_MAX   = 800              # hard ceiling on total trials
ERR_RATE_MIN   = 0.10             # <10% -> "speed up"
ERR_RATE_MAX   = 0.20             # >20% -> "slow down"
MIN_ERR_COUNT  = 60               # stop early once (trials>=N_TRIALS_MIN) AND (cum_errors>=MIN_ERR_COUNT)

# -------------------- Window / style --------------------
fullscr  = False
win_size = [800, 600]
bg_color = [0.8, 0.8, 0.8]  # light gray

TITLE   = "Flanker Task (5 arrows)"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_CSV  = os.path.join(BASE_DIR, f"flanker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

# -------------------- LSL --------------------
info = StreamInfo(name='PsychopyMarkerStream', type='Markers',
                  channel_count=1, channel_format='int32',
                  source_id='flankers_ern_lrp_unique')
outlet = StreamOutlet(info)
MARKER_STIM_ONSET = 1
MARKER_RESP = 2
# -------------------- Utilities --------------------
logging.console.setLevel(logging.INFO)

def send_marker(win, value):
    """Send a marker value exactly on next flip."""
    win.callOnFlip(outlet.push_sample, [int(value)])

def write_text(win, text, pos=(0,0), height=0.045, wrap=1.6, bold=False):
    return visual.TextStim(
        win, text=text, pos=pos, height=height, wrapWidth=wrap,
        bold=bold, color='black', alignText='center', units='height'
    )

def draw_fixation(win, size=0.06, color='black'):
    return visual.TextStim(win, text='+', height=size, color=color, bold=True, units='height')

def gen_block_trials(block_size):
    """
    Generate block_size trials with:
      - 50% congruent (all flankers match center), 50% incongruent (flankers opposite center)
      - 50% center '<', 50% center '>'
    Return list of dicts: {'stim_str','center','congruent','correct_key'}
    """
    # counts
    n_cong = block_size // 2
    n_incong = block_size - n_cong
    # split directions evenly within each congruency
    n_cong_left = n_cong // 2
    n_cong_right = n_cong - n_cong_left
    n_incong_left = n_incong // 2
    n_incong_right = n_incong - n_incong_left

    trials = []

    # helper to build 5-char string given center and congruency
    def build(center, congruent):
        flank = center if congruent else ('<' if center == '>' else '>')
        return flank*2 + center + flank*2

    # congruent-left
    for _ in range(n_cong_left):
        c = '<'
        s = build(c, True)
        trials.append(dict(stim_str=s, center=c, congruent=True, correct_key='lshift'))
    # congruent-right
    for _ in range(n_cong_right):
        c = '>'
        s = build(c, True)
        trials.append(dict(stim_str=s, center=c, congruent=True, correct_key='slash'))
    # incongruent-left (center '<', flankers '>')
    for _ in range(n_incong_left):
        c = '<'
        s = build(c, False)
        trials.append(dict(stim_str=s, center=c, congruent=False, correct_key='lshift'))
    # incongruent-right (center '>', flankers '<')
    for _ in range(n_incong_right):
        c = '>'
        s = build(c, False)
        trials.append(dict(stim_str=s, center=c, congruent=False, correct_key='slash'))

    random.shuffle(trials)
    return trials

# -------------------- Main --------------------
def main():
    win = visual.Window(size=win_size, units='pix', color=bg_color, fullscr=fullscr)
    kb = keyboard.Keyboard()
    fixation = draw_fixation(win)

    # Stimulus object — monospaced feel, big and clean
    stim = visual.TextStim(win, text='', height=64, color='black', font='Courier New')

    # Instructions
    instr = write_text(
        win,
        f"{TITLE}\n\n"
        "Respond to the CENTER arrow only.\n\n"
        "Center '<'  → Left Shift\n"
        "Center '>'  → Right Shift\n\n"
        f"Stim {int(STIM_TIME*1000)} ms, ISI {int(ISI_INTERVAL[0]*1000)}–{int(ISI_INTERVAL[1]*1000)} ms.\n"
        "Press SPACE to begin."
    )
    instr.draw(); win.flip()
    kb.clearEvents(); event.clearEvents()
    kb.waitKeys(keyList=['space'])

    # CSV header
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "timestamp_iso","global_trial","block","trial_in_block",
            "stimulus","center_dir","congruent","correct_key",
            "resp_key","correct","rt_ms","stim_time_s","isi_s"
        ])

    total_trials = 0
    cum_errors  = 0
    block_idx   = 0

    # Loop blocks until stop conditions satisfied
    while True:
        block_idx += 1
        trials = gen_block_trials(BLOCK_SIZE)
        block_errors = 0

        # Block loop
        for t_idx, t in enumerate(trials, start=1):
            # --- Fixation during ISI, collect responses during ISI window (carryover) ---
            isi = random.uniform(ISI_INTERVAL[0], ISI_INTERVAL[1])
            t0 = core.getTime()
            kb.clearEvents(); event.clearEvents()

            # Draw fixation during ISI while we *allow* late responses from previous trial to be ignored (kb cleared above)
            while (core.getTime() - t0) < isi:
                fixation.draw()
                win.flip()

            # --- Stimulus onset ---
            stim.text = t['stim_str']
            stim.draw()
            send_marker(win, MARKER_STIM_ONSET)
            win.flip()
            stim_on = core.getTime()

            # Accept response from stim onset through the *next* ISI (i.e., a unified response window: STIM_TIME + ISI)
            rt = None
            resp_key = None
            correct = 0

            # Keep stim visible for STIM_TIME
            kb.clearEvents()
            while (core.getTime() - stim_on) < STIM_TIME:
                # check keys without blocking
                keys = kb.getKeys(keyList=['lshift','slash','leftshift','escape'], waitRelease=False)
                if keys:
                    k = keys[0].name
                    if k == 'escape':
                        win.close(); core.quit()
                    # normalize aliases
                    if k == 'leftshift':  k = 'lshift'
                    # if k == 'slash': k = 'slash'
                    if k in ('lshift','slash') and resp_key is None:
                        send_marker(win, MARKER_RESP)
                        resp_key = k
                        rt = (keys[0].rt) * 1000.0  # ms
                # keep showing stim
                stim.draw()
                win.flip()

            # Turn off stim, go to post-stim ISI (still accept response if none yet)
            post_isi = random.uniform(ISI_INTERVAL[0], ISI_INTERVAL[1])
            post_start = core.getTime()
            while (core.getTime() - post_start) < post_isi and resp_key is None:
                fixation.draw()
                win.flip()
                keys = kb.getKeys(keyList=['lshift','slash','leftshift','escape'], waitRelease=False)
                if keys:
                    k = keys[0].name
                    if k == 'escape':
                        win.close(); core.quit()
                    if k == 'leftshift':  k = 'lshift'
                    # if k == 'rightshift': k = 'rshift'
                    if k in ('lshift','slash'):
                        send_marker(win, MARKER_RESP)
                        resp_key = k
                        # RT from stim onset
                        rt = (core.getTime() - stim_on) * 1000.0

            # Score
            if resp_key is None:
                correct = 0
                block_errors += 1
                cum_errors  += 1
            else:
                correct = int(resp_key == t['correct_key'])
                if not correct:
                    block_errors += 1
                    cum_errors  += 1

            total_trials += 1

            # Log
            with open(OUT_CSV, "a", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow([
                    datetime.now().isoformat(timespec='milliseconds'),
                    total_trials, block_idx, t_idx,
                    t['stim_str'], t['center'], int(t['congruent']), t['correct_key'],
                    resp_key if resp_key else '', int(correct), round(rt,2) if rt else '',
                    STIM_TIME, round(post_isi,3)
                ])

            # Esc quick-quit
            for k in kb.getKeys(waitRelease=False):
                if k.name == 'escape':
                    win.close(); core.quit()

        # ----- Block end feedback -----
        block_err_rate = block_errors / float(BLOCK_SIZE)
        if block_err_rate > ERR_RATE_MAX:
            msg = "Too many errors (>20%). SLOW DOWN a bit next block."
        elif block_err_rate < ERR_RATE_MIN:
            msg = "Very low errors (<10%). You can SPEED UP a bit next block."
        else:
            msg = "Nice pacing. Keep it steady."

        fb = write_text(
            win,
            f"Block {block_idx} complete.\n\n"
            f"Errors this block: {block_errors}/{BLOCK_SIZE} ({block_err_rate*100:.1f}%)\n\n"
            f"{msg}\n\nPress SPACE to continue.",
            height=0.05
        )
        fb.draw(); win.flip()
        kb.clearEvents(); event.clearEvents()
        kb.waitKeys(keyList=['space','escape'])
        if any(k.name == 'escape' for k in kb.getKeys(waitRelease=False)):
            win.close(); core.quit()

        # ----- Early stop logic -----
        # If we've reached the minimum trials AND cumulative errors have reached the threshold, stop.
        if (total_trials >= N_TRIALS_MIN) and (cum_errors >= MIN_ERR_COUNT):
            end = write_text(
                win,
                f"Stopping early: criteria met.\n\n"
                f"Total trials: {total_trials}\nCumulative errors: {cum_errors}\n\n"
                f"Data saved to:\n{os.path.basename(OUT_CSV)}\n\nPress ENTER to exit.",
                height=0.05
            )
            end.draw(); win.flip()
            _wait_exit(kb, win)
            return

        # If we hit the max trial cap, stop regardless.
        if total_trials >= N_TRIALS_MAX:
            end = write_text(
                win,
                f"Reached maximum trials.\n\n"
                f"Total trials: {total_trials}\nCumulative errors: {cum_errors}\n\n"
                f"Data saved to:\n{os.path.basename(OUT_CSV)}\n\nPress ENTER to exit.",
                height=0.05
            )
            end.draw(); win.flip()
            _wait_exit(kb, win)
            return

def _wait_exit(kb, win):
    kb.clearEvents()
    while True:
        keys = kb.getKeys(waitRelease=False)
        if any(k.name in ('return','enter','escape') for k in keys):
            break
        core.wait(0.01)
    win.close(); core.quit()

if __name__ == "__main__":
    main()
