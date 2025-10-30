# -*- coding: utf-8 -*-
"""
Logo→Word Semantic Relatedness (N400) — PsychoPy
Prime (logo) → ISI → Target (word, green). Respond RELATED (→) vs UNRELATED (←).
Response keys are accepted only AFTER a cooldown following TARGET onset.
Per-trial CSV with timing, keys, and RTs (from target onset and from window open).
"""

from psychopy import visual, core, event, logging
from psychopy.hardware import keyboard
import random, os, csv
from pylsl import StreamInfo, StreamOutlet
from datetime import datetime
from wordlist import wordlist as WORDLIST  # <- list of target words (see example below)

# -------------------- Parameters (edit as needed) --------------------
PRIME_TIME = 0.160            # seconds prime (logo) on-screen
TARGET_TIME = 0.160           # seconds target word on-screen (visual persistence)
ISI_INTERVAL = (0.700, 0.700) # seconds (min, max) between PRIME off and TARGET on

RESPONSE_COOLDOWN = 1.000     # seconds after TARGET onset during which responses are IGNORED
RESP_WINDOW = 0.500           # seconds accepted AFTER cooldown (float or tuple for jitter, e.g., (0.45, 0.55))

# Trials: by default use ALL combinations (len(WORDLIST) * len(BRAND_PATHS)).
# Set N_TRIALS = None to use all; or an int to sample that many from the full factorial.
N_TRIALS = None

FULLSCR = False
WIN_SIZE = [1000, 700]
BG_COLOR = [1, 1, 1]  # white
FONT_NAME = 'DejaVu Sans'
TITLE = "Logo→Word Relatedness (N400)"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(BASE_DIR, f"logo_word_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

COLOR_TARGET = 'green'
KEY_RELATED = 'right'   # →
KEY_UNRELATED = 'left'  # ←

# Markers
TARGET_STIM_ONSET_MARKER = 1
RESP_KEY_MARKER = 2

# Optional: small ITI after response/timeout (set to 0 to disable)
ITI_SECONDS = 0.0

# --------------- MEDIA (logos as image primes) ----------------
MEDIA_DIR = os.path.join(BASE_DIR, "media")  # prefix for all logo paths

# Provide relative paths from MEDIA_DIR or absolute paths. Example stubs:
BRAND_PATHS = [
    "media/logos/instagram.png",
    "media/logos/linkedin.png",
]

PRIME_IMAGE_SIZE = (500, 300)  # (w, h) in pixels; tweak for your display

# -------------------- LSL --------------------
info = StreamInfo(name='PsychopyMarkerStream', type='Markers',
                  channel_count=1, channel_format='int32',
                  source_id='logo_word_n400')
outlet = StreamOutlet(info)

# -------------------- Utilities --------------------
logging.console.setLevel(logging.INFO)

def send_marker(win, value):
    """Send a marker value exactly on next flip."""
    win.callOnFlip(outlet.push_sample, [int(value)])

def jitter_or_float(x):
    """Return a float from either a float or a (min,max) tuple."""
    if isinstance(x, (tuple, list)) and len(x) == 2:
        return random.uniform(x[0], x[1])
    return float(x)

def resolve_brand_paths(paths):
    """Resolve BRAND_PATHS against MEDIA_DIR and sanity-check existence."""
    resolved = []
    for p in paths:
        p2 = p if os.path.isabs(p) else os.path.join(MEDIA_DIR, p)
        if not os.path.exists(p2):
            logging.warning(f"[WARN] Brand image not found: {p2}")
        resolved.append(p2)
    if not any(os.path.exists(p) for p in resolved):
        raise FileNotFoundError("None of the BRAND_PATHS exist. Check MEDIA_DIR/paths.")
    return resolved

# -------------------- Main Experiment --------------------
def main():
    # ---- Window ----
    win = visual.Window(size=WIN_SIZE, units='pix', color=BG_COLOR, fullscr=FULLSCR)
    kb = keyboard.Keyboard()

    # ---- Stimuli ----
    instr = visual.TextStim(
        win,
        text=(
            f"{TITLE}\n\n"
            f"Logo (prime) → green word (target).\n"
            f"RIGHT (→) if RELATED, LEFT (←) if UNRELATED.\n\n"
            f"Prime {int(PRIME_TIME*1000)} ms, ISI {int(ISI_INTERVAL[0]*1000)}–{int(ISI_INTERVAL[1]*1000)} ms,\n"
            f"Target {int(TARGET_TIME*1000)} ms,\n"
            f"Cooldown {int(RESPONSE_COOLDOWN*1000)} ms (no responses accepted), then\n"
            f"Response window {int(jitter_or_float(RESP_WINDOW)*1000)} ms.\n\n"
            f"Press SPACE to begin."
        ),
        height=24, color='black', wrapWidth=900, font=FONT_NAME, alignText='center'
    )

    # Image prime (logo)
    prime_img = visual.ImageStim(win, image=None, size=PRIME_IMAGE_SIZE, interpolate=True)

    # Target word
    target_stim = visual.TextStim(win, text='', height=60, color=COLOR_TARGET, font=FONT_NAME)

    # Fixation
    fixation = visual.TextStim(win, text='+', height=40, color='black')

    # ---- Build trials (full factorial: each target x each brand) ----
    brand_paths = resolve_brand_paths(BRAND_PATHS)
    targets = list(WORDLIST)  # <- your target words

    full = []
    for tgt in targets:
        for bpath in brand_paths:
            full.append({
                "brand_path": bpath,
                "brand": os.path.splitext(os.path.basename(bpath))[0],
                "target": tgt,
                # 'condition' and 'correct_key' intentionally omitted (unknown without labels)
            })

    if len(full) == 0:
        raise RuntimeError("No trials to run (no targets or no valid logos).")

    random.shuffle(full)

    if isinstance(N_TRIALS, int) and N_TRIALS > 0:
        full = random.sample(full, k=min(N_TRIALS, len(full)))

    # ---- Instructions ----
    instr.draw(); win.flip()
    kb.clearEvents(); event.clearEvents()
    kb.waitKeys(keyList=['space', 'escape'])
    if any(k.name == 'escape' for k in kb.getKeys(waitRelease=False)):
        win.close(); core.quit()

    # ---- CSV header ----
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "timestamp_iso", "trial_index",
            "brand", "brand_path", "target",
            "prime_time_s", "isi_s", "target_time_s",
            "cooldown_s", "resp_window_s",
            "resp_key", "rt_ms_from_target", "rt_ms_from_window_open"
        ])

    # ---- Trial loop ----
    for t_idx, t in enumerate(full):
        # PRIME (logo)
        prime_img.image = t["brand_path"]
        prime_on = core.getTime()
        kb.clearEvents(); event.clearEvents()

        while (core.getTime() - prime_on) < PRIME_TIME:
            prime_img.draw()
            win.flip()

        # ISI (fixation)
        isi = random.uniform(*ISI_INTERVAL)
        isi_start = core.getTime()
        while (core.getTime() - isi_start) < isi:
            fixation.draw()
            win.flip()

        # TARGET (word)
        target_stim.text = t['target']
        target_on = core.getTime()
        window_open = target_on + RESPONSE_COOLDOWN
        resp_win_len = jitter_or_float(RESP_WINDOW)
        resp_deadline = window_open + resp_win_len

        # For clean gating, drop any pre-target key noise
        kb.clearEvents(); event.clearEvents()
        resp_key = None
        rt_ms_from_target = None
        rt_ms_from_window = None
        marker_sent = False

        while core.getTime() < resp_deadline:
            now = core.getTime()
            elapsed = now - target_on

            if elapsed < TARGET_TIME:
                target_stim.draw()
                if not marker_sent:
                    send_marker(win, TARGET_STIM_ONSET_MARKER)  # on first target frame
                    marker_sent = True
            else:
                fixation.draw()

            win.flip()

            # Accept keys only after cooldown window opens
            keys = kb.getKeys(keyList=[KEY_RELATED, KEY_UNRELATED, 'escape'], waitRelease=False)
            if keys:
                k = keys[0].name
                if k == 'escape':
                    win.close(); core.quit()
                if resp_key is None and (now >= window_open) and (k in (KEY_RELATED, KEY_UNRELATED)):
                    send_marker(win, RESP_KEY_MARKER)
                    resp_key = k
                    rt_ms_from_target = (now - target_on) * 1000.0
                    rt_ms_from_window = (now - window_open) * 1000.0
                    # do NOT break; we keep showing fixation until deadline for consistency
                    # (flip the line above to 'break' if you want to end-trial immediately)

        # Optional ITI
        if ITI_SECONDS > 0:
            iti_start = core.getTime()
            while (core.getTime() - iti_start) < ITI_SECONDS:
                fixation.draw(); win.flip()

        # ---- Log row ----
        with open(OUT_CSV, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow([
                datetime.now().isoformat(timespec='milliseconds'), t_idx,
                t['brand'], t['brand_path'], t['target'],
                PRIME_TIME, round(isi, 3), TARGET_TIME,
                RESPONSE_COOLDOWN, round(resp_win_len, 3),
                (resp_key or ''),
                round(rt_ms_from_target, 2) if rt_ms_from_target is not None else '',
                round(rt_ms_from_window, 2) if rt_ms_from_window is not None else ''
            ])

    # ---- End screen ----
    end = visual.TextStim(
        win,
        text=(f"Session complete.\n\nTrials: {len(full)}\nData saved to:\n"
              f"{os.path.basename(OUT_CSV)}\n\nPress ENTER to exit."),
        height=28, color='black', wrapWidth=900, font=FONT_NAME, alignText='center'
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