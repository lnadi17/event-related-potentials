# Oddball (Standard vs. Oddball) with PsychoPy + LSL (AUDIO VERSION)
# - Replaces visual circles with audio tones (standard vs oddball)
# - Same flow, markers, and block counting prompt as your original
# - Counts the HIGH (oddball) beeps between prompts

from psychopy import visual, core, event, logging, sound
from psychopy.visual import Window
from psychopy.hardware import keyboard
from pylsl import StreamInfo, StreamOutlet
import random

# =========================
# Config (tweak as needed)
# =========================
TITLE = "Auditory Oddball (P300)"
PROBABILITY_ODD = 0.2
NUM_TRIALS = 200            # set higher for ERP averaging
LEN_BLOCK = 25              # trials before numeric prompt
PRETRIAL_TIME = 0.5         # fixation before stimulus (s)
STIM_AUDIO_TIME = 0.2       # tone duration (s)
TRIAL_LEN_MIN = 1.0         # min total trial length (s) incl. fixation + tone + ITI
TRIAL_LEN_MAX = 2.0         # max total trial length (s)

# Audio settings
SAMPLE_RATE = 48000         # psychopy sound default is fine; 48k is common
VOLUME = 0.7
FREQ_STANDARD = 440         # Hz (A4) - standard
FREQ_ODDBALL  = 880         # Hz (A5) - oddball (higher pitch)

# Window settings (used for instructions, fixation, prompts)
fullscr = False
win_size = [1280, 800]
bg_color = [0.5, 0.5, 0.5]  # grey

# LSL markers
MARK_STANDARD = 1
MARK_ODDBALL = 2

# =========================
# LSL Stream
# =========================
info = StreamInfo(name='PsychopyMarkerStream', type='Markers',
                  channel_count=1, channel_format='int32',
                  source_id='auditory_oddball_001')
outlet = StreamOutlet(info)

# =========================
# Helpers
# =========================
def write_text(win, text, pos=(0, 0), height=0.045, wrapWidth=1.5, bold=False):
    return visual.TextStim(
        win, text=text, pos=pos, height=height, wrapWidth=wrapWidth,
        bold=bold, color='black', alignText='center', anchorVert='center', units='height'
    )

def show_text_and_wait(win, text, wait_keys=('space',), pos=(0, 0), height=0.045):
    stim = write_text(win, text, pos=pos, height=height)
    stim.draw()
    win.flip()
    kb = keyboard.Keyboard()
    kb.clearEvents(); event.clearEvents()
    keys = kb.waitKeys(keyList=list(wait_keys))
    return keys

def get_numeric_response(win, prompt_text):
    """
    Collect digits until Enter is pressed. Backspace supported.
    Returns the entered string (possibly "").
    """
    kb = keyboard.Keyboard()
    kb.clearEvents()
    response = ""
    prompt = write_text(win, prompt_text, pos=(0, 0.2), height=0.045)
    entry_label = write_text(win, "Your count:", pos=(0, -0.05), height=0.04)
    entry = write_text(win, response, pos=(0, -0.12), height=0.07, bold=True)

    while True:
        prompt.draw()
        entry_label.draw()
        entry.draw()
        win.flip()
        events = kb.getKeys(waitRelease=False)
        for k in events:
            name = k.name
            if name in [str(d) for d in range(10)]:
                response += name
                entry.text = response
            elif name in ('backspace',):
                response = response[:-1]
                entry.text = response
            elif name in ('return', 'enter'):
                return response
            elif name == 'escape':
                win.close(); core.quit()

def draw_fixation(win, size=0.05, color='black'):
    return visual.TextStim(win, text='+', height=size, color=color, bold=True, units='height')

def send_marker_on_flip(win, value):
    # Schedule LSL push_sample on the next screen flip
    win.callOnFlip(outlet.push_sample, [value])

# =========================
# Main
# =========================
def main():
    logging.console.setLevel(logging.INFO)
    win = Window(size=win_size, units='height', color=bg_color, fullscr=fullscr)

    # Prepare audio tones
    # Use short-duration tones; we will stop them explicitly after STIM_AUDIO_TIME
    tone_standard = sound.Sound(value=FREQ_STANDARD, secs=STIM_AUDIO_TIME, stereo=True, sampleRate=SAMPLE_RATE)
    tone_oddball  = sound.Sound(value=FREQ_ODDBALL,  secs=STIM_AUDIO_TIME, stereo=True, sampleRate=SAMPLE_RATE)
    tone_standard.setVolume(VOLUME)
    tone_oddball.setVolume(VOLUME)

    # Instructions
    intro = (
        "Auditory Oddball Task\n\n"
        f"- You will hear tones. Most are {FREQ_STANDARD} Hz (standard).\n"
        f"- Occasionally, a HIGHER tone ({FREQ_ODDBALL} Hz) will play — that's the ODDBALL.\n\n"
        "Your task: SILENTLY COUNT the number of HIGH tones (oddballs).\n"
        f"Every {LEN_BLOCK} trials, you'll be asked to type your count and press Enter.\n\n"
        "Press SPACE to begin."
    )
    show_text_and_wait(win, intro, wait_keys=('space',), pos=(0, 0), height=0.045)

    fixation = draw_fixation(win)

    # Build trial sequence
    n_oddballs = int(round(NUM_TRIALS * PROBABILITY_ODD))
    n_standards = NUM_TRIALS - n_oddballs
    seq = ([MARK_ODDBALL] * n_oddballs) + ([MARK_STANDARD] * n_standards)
    random.shuffle(seq)

    # Run
    trials_since_prompt = 0
    odd_count_since_prompt = 0
    kb = keyboard.Keyboard()
    kb.clearEvents()

    for idx, code in enumerate(seq, start=1):
        # Fixation (pre-trial)
        fixation.draw()
        win.flip()
        core.wait(PRETRIAL_TIME)

        # Choose tone
        is_odd = (code == MARK_ODDBALL)
        tone = tone_oddball if is_odd else tone_standard

        # Send marker and start tone precisely on flip
        send_marker_on_flip(win, code)
        win.callOnFlip(tone.play)  # schedule audio onset with flip
        fixation.draw()            # keep fixation visible during tone
        win.flip()

        # Tone duration (audio plays for STIM_AUDIO_TIME)
        core.wait(STIM_AUDIO_TIME)
        tone.stop()  # ensure it stops even if backend ignores secs

        # Randomize total trial length (keep total within [min, max])
        chosen_total = random.uniform(TRIAL_LEN_MIN, TRIAL_LEN_MAX)
        remaining = max(0.0, chosen_total - PRETRIAL_TIME - STIM_AUDIO_TIME)
        fixation.draw()
        win.flip()
        core.wait(remaining)

        # Update counters
        trials_since_prompt += 1
        if is_odd:
            odd_count_since_prompt += 1

        # Blocked numeric prompt
        if trials_since_prompt == LEN_BLOCK:
            prompt_text = (
                "Type how many HIGH (oddball) tones you heard\n"
                "since the last prompt, then press Enter."
            )
            # Static background behind prompt
            bg_rect = visual.Rect(win, fillColor=bg_color, lineColor=None, width=2, height=2, units='height')
            bg_rect.draw()
            win.flip()
            _ = get_numeric_response(win, prompt_text)
            trials_since_prompt = 0
            odd_count_since_prompt = 0

        # Allow emergency quit
        events = kb.getKeys(waitRelease=False)
        if any(k.name == 'escape' for k in events):
            break

    # End screen
    end_text = write_text(win, 'Task complete!\n\nPress Enter or Esc to exit.', pos=(0, 0), height=0.06)
    end_text.draw()
    win.flip()
    # Wait for Enter/Esc
    while True:
        keys = kb.getKeys(waitRelease=False)
        if any(k.name in ('return', 'enter', 'escape') for k in keys):
            break
        core.wait(0.01)

    core.wait(0.2)
    win.close()
    core.quit()

if __name__ == "__main__":
    main()
