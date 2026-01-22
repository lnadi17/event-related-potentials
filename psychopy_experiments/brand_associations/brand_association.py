# -*- coding: utf-8 -*-
"""
Logo→Word Semantic Relatedness (N400) — PsychoPy
Prime (logo) → ISI → Target (word, green). Respond RELATED (→) vs UNRELATED (←).
Response keys are accepted only AFTER a cooldown following TARGET onset.
Per-trial CSV with timing, keys, and RTs.
"""
USE_LSL = False  # Set to False to disable LSL markers

if USE_LSL:
    from pylsl import StreamInfo, StreamOutlet
from psychopy import visual, core, event, logging
from psychopy.hardware import keyboard
import random, os, csv, math
from datetime import datetime
from PIL import Image
from brands_wordlist import WORDLIST

## Parameters
# Timing (in seconds)
PRIME_TIME = 0.160  # seconds prime (logo) on-screen
TARGET_TIME = 0.160  # seconds target word on-screen (visual persistence)
ISI_INTERVAL = (0.540, 0.540)  # seconds (min, max) between PRIME off and TARGET on
RESP_WINDOW = 1.500  # seconds accepted AFTER cooldown
ITI_SECONDS = 0.500  # seconds after response/timeout to the next trial (set to 0 to disable)

## Trials & block structure
# Number of trials, by default use ALL combinations (len(WORDLIST) * len(BRAND_PATHS))
# Set N_TRIALS = None to use all; or an int to sample that many from the full factorial
N_TRIALS = None
# If TRIALS_PER_BLOCK is None or 0 → single block (no rest screens)
TRIALS_PER_BLOCK = 80

## Display settings
FULLSCR = False
WIN_SIZE = [1000, 700]
BG_COLOR = [1, 1, 1]  # White background
FONT_NAME = 'DejaVu Sans'
TITLE = "Brand Associations Test (N400)"
COLOR_TARGET = 'green'
PRIME_IMAGE_MAX = (500, 300)  # Max bounding box for primes to preserve aspect within (max_width, max_height)

## Response keys
KEY_RELATED = 'right'  # →
KEY_UNRELATED = 'left'  # ←

## Markers
TARGET_MARKER = 1
RESP_MARKER = 2

## Media input/output paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(BASE_DIR, f"logo_word_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
MEDIA_DIR = os.path.join(BASE_DIR, "media")  # Prefix for all logo paths
# Provide relative paths from MEDIA_DIR or absolute/BASE_DIR-relative paths.
BRAND_PATHS = [
    "logos/instagram.png",
    "logos/linkedin.png",
]

## Prepare wordlist
REPEATS_PER_WORD = 4  # How many times to repeat each word during the experiment

## LSL streaming
if USE_LSL:
    info = StreamInfo(name='PsychopyMarkerStream', type='Markers',
                      channel_count=1, channel_format='int32',
                      source_id='logo_word_n400')
    outlet = StreamOutlet(info)

## Utilities
logging.console.setLevel(logging.INFO)


def send_marker(win, value):
    """Send a marker value exactly on next flip."""
    if USE_LSL:
        win.callOnFlip(outlet.push_sample, [int(value)])


def resolve_brand_paths(paths):
    """
    Resolve BRAND_PATHS against MEDIA_DIR and BASE_DIR.
    Assume provided paths exist; for relative paths prefer MEDIA_DIR.
    """
    resolved = []
    for p in paths:
        if os.path.isabs(p):
            resolved.append(p)
        else:
            resolved.append(os.path.join(MEDIA_DIR, p))
    return resolved


def fitted_size_for_image(img_path, max_size):
    """
    Compute (w,h) that fits 'img_path' inside 'max_size' while preserving aspect ratio.
    max_size is (max_w, max_h) in the same units as the window ('pix' here).
    """
    with Image.open(img_path) as im:
        w, h = im.size
    max_w, max_h = max_size
    scale = min(max_w / float(w), max_h / float(h))
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return new_w, new_h


def main():
    # Set up window
    win = visual.Window(size=WIN_SIZE, units='pix', color=BG_COLOR, fullscr=FULLSCR)
    kb = keyboard.Keyboard()
    logging.info(f"Experiment window initialized: {win.size} px, fullscr={FULLSCR}")

    # Create instructions
    instr = visual.TextStim(
        win,
        text=(
            f"{TITLE}\n\n"
            f"Logo (prime) → green word (target).\n"
            f"RIGHT (→) if RELATED, LEFT (←) if UNRELATED.\n\n"
            f"Prime {int(PRIME_TIME * 1000)} ms, ISI {int(ISI_INTERVAL[0] * 1000)}–{int(ISI_INTERVAL[1] * 1000)} ms,\n"
            f"Target {int(TARGET_TIME * 1000)} ms,\n"
            # f"Cooldown {int(RESPONSE_COOLDOWN * 1000)} ms (no responses accepted, '+' shown), then\n"
            f"Response window {int(RESP_WINDOW * 1000)} ms ('?' shown).\n\n"
            f"Press SPACE to begin."
        ),
        height=24, color='black', wrapWidth=900, font=FONT_NAME, alignText='center'
    )
    logging.info("Experiment instructions prepared.")

    # Prepare prime/target stimuli placeholders
    prime_img = visual.ImageStim(win, image=None, size=None, interpolate=True)
    target_stim = visual.TextStim(win, text='', height=60, color=COLOR_TARGET, font=FONT_NAME)

    # Fixation and response-window prompt
    fixation = visual.TextStim(win, text='+', height=60, color='black')
    question = visual.TextStim(win, text='?', height=60, color='black')

    # Rest screen between blocks (placeholder)
    rest_text = visual.TextStim(
        win,
        text='',
        height=28,
        color='black',
        wrapWidth=900,
        font=FONT_NAME,
        alignText='center'
    )

    # Build trials (full factorial: each target x each brand)
    logging.info("Building trial list...")
    full, n_blocks, total_trials, trials_per_block = build_trials()

    # Display instructions and wait for SPACE (or ESCAPE to quit)
    instr.draw()
    win.flip()
    kb.clearEvents()
    event.clearEvents()
    kb.waitKeys(keyList=['space', 'escape'])
    if any(k.name == 'escape' for k in kb.getKeys(waitRelease=False)):
        win.close()
        core.quit()

    # Create output CSV and write header
    csv_create_header()

    # Trial loop
    for t_idx, t in enumerate(full):
        prime_img.image = t["brand_path"]
        prime_img.size = t["brand_size"]
        prime_on = core.getTime()
        kb.clearEvents()
        event.clearEvents()

        # Show PRIME (logo)
        while (core.getTime() - prime_on) < PRIME_TIME:
            prime_img.draw()
            win.flip()

        # Wait during ISI (fixation)
        isi = random.uniform(*ISI_INTERVAL)
        isi_start = core.getTime()
        while (core.getTime() - isi_start) < isi:
            fixation.draw()
            win.flip()

        # Show TARGET (word) → response window ("?")
        target_stim.text = t['target']
        target_on = core.getTime()
        resp_deadline = target_on + TARGET_TIME + RESP_WINDOW

        # For clean gating, drop any pre-target key noise
        kb.clearEvents()
        event.clearEvents()
        resp_key = None
        rt_ms_from_target = None
        marker_sent = False

        while core.getTime() < resp_deadline:
            now = core.getTime()
            elapsed = now - target_on

            # Determine what to draw (target vs '?')
            if elapsed < TARGET_TIME:
                # During target: show target
                target_stim.draw()
                if not marker_sent:
                    send_marker(win, TARGET_MARKER)  # on first target frame
                    marker_sent = True
            elif elapsed < TARGET_TIME + RESP_WINDOW:
                # After target offset, response window: show '?'
                question.draw()

            win.flip()

            # Accept keys only during response window
            keys = kb.getKeys(keyList=[KEY_RELATED, KEY_UNRELATED, 'escape'], waitRelease=False)
            if keys:
                k = keys[0].name
                if k == 'escape':
                    win.close()
                    core.quit()
                if resp_key is None and (elapsed > TARGET_TIME) and (k in (KEY_RELATED, KEY_UNRELATED)):
                    send_marker(win, RESP_MARKER)
                    resp_key = k
                    rt_ms_from_target = elapsed * 1000
                    # NOTE: Keep drawing until resp_deadline for consistent timing; change to 'break' to end early
                    # break

        # Optional ITI
        if ITI_SECONDS > 0:
            iti_start = core.getTime()
            while (core.getTime() - iti_start) < ITI_SECONDS:
                fixation.draw()
                win.flip()

        # Log trial result to CSV
        with open(OUT_CSV, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow([
                datetime.now().isoformat(timespec='milliseconds'),  # timestamp_iso
                t_idx,  # trial_index
                t['brand'], t['target'],  # brand, target
                PRIME_TIME, TARGET_TIME, RESP_WINDOW,  # prime_time_s, target_time_s, resp_window_s
                (resp_key or ''),  # resp_key
                round(rt_ms_from_target, 2) if rt_ms_from_target is not None else '',  # rt_ms_from_target
            ])

        # Block rest screen
        trials_done = t_idx + 1
        if trials_per_block and (trials_done % trials_per_block == 0) and (trials_done < total_trials):
            current_block = trials_done // trials_per_block
            rest_text.text = (
                f"You can rest here.\n\n"
                f"You can move around and blink now.\n\n"
                f"{trials_done} trials done out of {total_trials}.\n"
                f"Block {current_block} of {n_blocks} completed.\n\n"
                f"Press SPACE to continue."
            )
            kb.clearEvents()
            event.clearEvents()
            while True:
                rest_text.draw()
                win.flip()
                keys = kb.getKeys(keyList=['space', 'escape'], waitRelease=False)
                if keys:
                    if any(k.name == 'escape' for k in keys):
                        win.close()
                        core.quit()
                    if any(k.name == 'space' for k in keys):
                        kb.clearEvents()
                        event.clearEvents()
                        break
                core.wait(0.01)

    # End of experiment screen
    end = visual.TextStim(
        win,
        text=(f"Session complete.\n\nTrials: {len(full)}\nData saved to:\n"
              f"{os.path.basename(OUT_CSV)}\n\nPress ENTER to exit."),
        height=28, color='black', wrapWidth=900, font=FONT_NAME, alignText='center'
    )
    end.draw()
    win.flip()
    kb.clearEvents()
    while True:
        keys = kb.getKeys(waitRelease=False)
        if any(k.name in ('return', 'enter', 'escape') for k in keys):
            break
        core.wait(0.01)

    win.close()
    core.quit()


def build_trials() -> tuple[list[dict], int, int, int]:
    brand_paths = resolve_brand_paths(BRAND_PATHS)
    targets = [word for category in WORDLIST.values() for word in category]
    targets = targets * REPEATS_PER_WORD  # Repeat each word as specified
    full = []
    for tgt in targets:
        for bpath in brand_paths:
            full.append({
                "brand": os.path.splitext(os.path.basename(bpath))[0],
                "brand_path": bpath,
                "brand_size": fitted_size_for_image(bpath, PRIME_IMAGE_MAX),
                "target": tgt,
                # 'condition' and 'correct_key' intentionally omitted (unknown without labels)
            })

    if len(full) == 0:
        raise RuntimeError("No trials to run (no targets or no valid logos).")

    # Shuffle trials and limit to N_TRIALS if set
    random.shuffle(full)
    if isinstance(N_TRIALS, int) and N_TRIALS > 0:
        full = random.sample(full, k=min(N_TRIALS, len(full)))
    total_trials = len(full)
    logging.info(f"Trial list built. Total trials: {total_trials}")

    if TRIALS_PER_BLOCK and TRIALS_PER_BLOCK > 0:
        trials_per_block = min(TRIALS_PER_BLOCK, total_trials)
        n_blocks = int(math.ceil(total_trials / float(trials_per_block)))
    else:
        trials_per_block = None
        n_blocks = 1
    return full, n_blocks, total_trials, trials_per_block


def csv_create_header():
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "timestamp_iso", "trial_index", "brand", "target", "prime_time_s", "target_time_s", "resp_window_s",
            "resp_key", "rt_ms_from_target"
        ])


if __name__ == "__main__":
    main()
