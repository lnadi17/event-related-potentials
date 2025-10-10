# -*- coding: utf-8 -*-
"""
Semantic Relatedness Judgment Task — PsychoPy
Prime (red) → ISI → Target (green). Respond RELATED (→) vs UNRELATED (←).
Output CSV per-trial with timing, accuracy, condition, and words.
"""

from psychopy import visual, core, event, logging
from psychopy.hardware import keyboard
import numpy as np
import random, os, csv
from pylsl import StreamInfo, StreamOutlet
from datetime import datetime
from wordlist import wordlist as WORDLIST

# -------------------- Parameters (edit as needed) --------------------
PRIME_TIME = 0.200  # seconds prime on-screen
TARGET_TIME = 0.200  # seconds target on-screen (visual persistence; responses continue)
ISI_INTERVAL = (0.900, 1.100)  # seconds (min, max) between PRIME off and TARGET on
RESP_WINDOW = (1.400, 1.600)  # seconds (min, max) from TARGET onset (responses close after this)
N_TRIALS = 120  # total trials (must be even). Each target contributes 2 trials.

FULLSCR = False
WIN_SIZE = [1000, 700]
BG_COLOR = [1, 1, 1]  # white background
FONT_NAME = 'DejaVu Sans'
TITLE = "Semantic Relatedness Judgment"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(BASE_DIR, f"semrel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

COLOR_PRIME = 'red'
COLOR_TARGET = 'green'
KEY_RELATED = 'right'  # right arrow key
KEY_UNRELATED = 'left'  # left arrow key

# Markers
TARGET_STIM_ONSET_MARKER = 1
RESP_KEY_MARKER = 2

# Optional: small ITI after response/timeout (set to 0 to disable)
ITI_SECONDS = 0.0

# -------------------- LSL --------------------
info = StreamInfo(name='PsychopyMarkerStream', type='Markers',
                 channel_count=1, channel_format='int32',
                 source_id='word_pair_judgement_n400_unique')
outlet = StreamOutlet(info)

# -------------------- Utilities --------------------
logging.console.setLevel(logging.INFO)


def send_marker(win, value):
    """Send a marker value exactly on next flip."""
   win.callOnFlip(outlet.push_sample, [int(value)])


def write_text(win, text, pos=(0, 0), height=0.045, wrap=1.6, bold=False):
    return visual.TextStim(
        win, text=text, pos=pos, height=height, wrapWidth=wrap,
        bold=bold, color='black', alignText='center', units='height', font=FONT_NAME
    )


def build_trial_dicts(items):
    """
    Given a list of (rel_prime, target, unrel_prime), return a dict keyed by target
    and two trial dicts per target: one RELATED, one UNRELATED.
    """
    by_target = {}
    trials_per_target = {}
    for (rel, tgt, unrel) in items:
        by_target[tgt] = (rel, unrel)
    for tgt, (rel, unrel) in by_target.items():
        trials_per_target[tgt] = [
            dict(prime=rel, target=tgt, condition='related', correct_key=KEY_RELATED),
            dict(prime=unrel, target=tgt, condition='unrelated', correct_key=KEY_UNRELATED),
        ]
    return trials_per_target


def allocate_two_halves(trials_per_target, n_targets_needed):
    """
    Enforce the constraint: each target appears once per half.
    Returns a single list of trials (first_half + second_half), each half shuffled.
    """
    all_targets = list(trials_per_target.keys())
    random.shuffle(all_targets)
    chosen = all_targets[:n_targets_needed]

    first_half, second_half = [], []
    # For each chosen target, randomly assign which of its two conditions goes to which half
    for tgt in chosen:
        pair = trials_per_target[tgt]
        random.shuffle(pair)
        first_half.append(pair[0])
        second_half.append(pair[1])

    random.shuffle(first_half)
    random.shuffle(second_half)
    return first_half + second_half


# -------------------- Main Experiment --------------------

def main():
    # ---- Window ----
    win = visual.Window(size=WIN_SIZE, units='pix', color=BG_COLOR, fullscr=FULLSCR)
    kb = keyboard.Keyboard()

    # ---- Text objects ----
    instr = write_text(
        win,
        f"{TITLE}\n\n"
        f"Red word (prime) → green word (target).\n"
        f"RIGHT arrow if RELATED, LEFT arrow if UNRELATED.\n\n"
        f"Prime {int(PRIME_TIME * 1000)} ms, ISI {int(ISI_INTERVAL[0] * 1000)}–{int(ISI_INTERVAL[1] * 1000)} ms,\n"
        f"Target {int(TARGET_TIME * 1000)} ms, Response window {int(RESP_WINDOW[0] * 1000)}–{int(RESP_WINDOW[1] * 1000)} ms.\n\n"
        f"Press SPACE to begin."
    )

    prime_stim = visual.TextStim(win, text='', height=60, color=COLOR_PRIME, font=FONT_NAME)
    target_stim = visual.TextStim(win, text='', height=60, color=COLOR_TARGET, font=FONT_NAME)
    fixation = visual.TextStim(win, text='+', height=40, color='black')

    # Determine how many targets we can/should use
    max_targets = len(WORDLIST)
    needed_targets = N_TRIALS // 2
    
    wordlist = WORDLIST[:needed_targets]  # Limit wordlist to needed targets
    
    # Build trial dicts per target
    trials_per_target = build_trial_dicts(wordlist)

    # Allocate trials respecting half constraint
    trial_list = allocate_two_halves(trials_per_target, needed_targets)

    # Safety: enforce even count
    assert len(trial_list) % 2 == 0

    # ---- Instructions ----
    instr.draw();
    win.flip()
    kb.clearEvents();
    event.clearEvents()
    kb.waitKeys(keyList=['space', 'escape'])
    if any(k.name == 'escape' for k in kb.getKeys(waitRelease=False)):
        win.close();
        core.quit()

    # ---- CSV header ----
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "timestamp_iso", "trial_index", "prime", "target", "condition",
            "prime_time_s", "isi_s", "target_time_s", "resp_window_s",
            "resp_key", "correct", "rt_ms"
        ])

    # ---- Trial loop ----
    for t_idx, t in enumerate(trial_list):
        # PRIME
        prime_stim.text = t['prime']
        prime_stim.color = COLOR_PRIME
        prime_on = core.getTime()
        kb.clearEvents();
        event.clearEvents()

        # Show prime for PRIME_TIME
        while (core.getTime() - prime_on) < PRIME_TIME:
            prime_stim.draw();
            win.flip()

        # ISI (blank + fixation). No responses during ISI.
        isi = random.uniform(*ISI_INTERVAL)
        isi_start = core.getTime()
        while (core.getTime() - isi_start) < isi:
            fixation.draw();
            win.flip()

        # TARGET
        target_stim.text = t['target']
        target_stim.color = COLOR_TARGET
        target_on = core.getTime()
        resp_deadline = target_on + random.uniform(*RESP_WINDOW)
        resp_key = None
        rt_ms = None
        correct = 0

        marker_sent = False
        # Show target for TARGET_TIME; responses accepted immediately and continue until resp_deadline
        while core.getTime() < resp_deadline:
            elapsed = core.getTime() - target_on
            if elapsed < TARGET_TIME:
                target_stim.draw()
                if not marker_sent:
                    send_marker(win, TARGET_STIM_ONSET_MARKER)
                    marker_sent = True
            else:
                # after target offset, keep fixation
                fixation.draw()
            win.flip()

            keys = kb.getKeys(keyList=[KEY_RELATED, KEY_UNRELATED, 'escape'], waitRelease=False)
            if keys:
                k = keys[0].name
                if k == 'escape':
                    win.close();
                    core.quit()
                if resp_key is None and k in (KEY_RELATED, KEY_UNRELATED):
                    send_marker(win, RESP_KEY_MARKER)
                    resp_key = k
                    rt_ms = (core.getTime() - target_on) * 1000.0
                    correct = int(resp_key == t['correct_key'])
                    # break  # end trial immediately on response

        # Timeout case (no response)
        if resp_key is None:
            correct = 0

        # Optional ITI
        if ITI_SECONDS > 0:
            iti_start = core.getTime()
            while (core.getTime() - iti_start) < ITI_SECONDS:
                fixation.draw();
                win.flip()

        # Log
        with open(OUT_CSV, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow([
                datetime.now().isoformat(timespec='milliseconds'), t_idx,
                t['prime'], t['target'], t['condition'],
                PRIME_TIME, round(isi, 3), TARGET_TIME,
                round(resp_deadline - target_on, 3),
                resp_key if resp_key else '', correct, round(rt_ms, 2) if rt_ms else ''
            ])

    # ---- End screen ----
    end = write_text(
        win,
        f"Session complete.\n\nTrials: {len(trial_list)}\nData saved to:\n{os.path.basename(OUT_CSV)}\n\nPress ENTER to exit.",
        height=0.05
    )
    end.draw();
    win.flip()

    kb.clearEvents()
    while True:
        keys = kb.getKeys(waitRelease=False)
        if any(k.name in ('return', 'enter', 'escape') for k in keys):
            break
        core.wait(0.01)

    win.close();
    core.quit()


if __name__ == "__main__":
    main()
