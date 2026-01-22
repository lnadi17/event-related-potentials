# Oddball (Standard vs. Oddball) with PsychoPy + LSL
from psychopy import visual, core, event, logging
from psychopy.visual import Window
from psychopy.hardware import keyboard
from pylsl import StreamInfo, StreamOutlet
import random
import os

# Config
TITLE = "Visual Evoked Potentials"
PROBABILITY_ODD = 0.2
NUM_TRIALS = 20
LEN_BLOCK = 5  # how many trials before prompt
PRETRIAL_TIME = 0.5  # seconds before stimulus
STIM_DISPLAY_TIME = 0.5  # seconds stimulus is shown
TRIAL_LEN_MIN = 1.0  # minimum total trial length (seconds)
TRIAL_LEN_MAX = 2.0  # maximum total trial length (seconds)

# PsychoPy window settings
fullscr = False
win_size = [800, 600]
bg_color = [-1, -1, -1]  # black
circle_radius_px = 100  # radius of circle (in pix when units="pix")

# LSL markers
MARK_STANDARD = 1
MARK_ODDBALL = 2

# Create LSL Stream
info = StreamInfo(name='PsychopyMarkerStream', type='Markers',
                  channel_count=1, channel_format='int32',
                  source_id='uniqueid12345')
outlet = StreamOutlet(info)


# Run
clock = core.Clock()
logging.console.setLevel(logging.INFO)

def write_text(win, text, pos=(0, 0), height=0.04, wrapWidth=1.5, bold=False):
    return visual.TextStim(
        win, text=text, pos=pos, height=height, wrapWidth=wrapWidth,
        bold=bold, color='black', alignText='center', anchorVert='center', units='height'
    )


def show_text_and_wait(win, text, wait_keys=('space',), pos=(0, 0.6), height=0.04):
    stim = write_text(win, text, pos=pos, height=height)
    stim.draw()
    win.flip()
    kb = keyboard.Keyboard()
    kb.clearEvents()
    event.clearEvents()
    # Wait
    keys = kb.waitKeys(keyList=list(wait_keys))
    return keys


def show_text_for_duration(win, text, seconds, pos=(0, 0), height=0.04):
    stim = write_text(win, text, pos=pos, height=height)
    stim.draw()
    win.flip()
    core.wait(seconds)


def draw_crosshair(win, size=0.05, color='black'):
    # Simple '+' as crosshair
    return visual.TextStim(win, text='+', height=size, color=color, bold=True, units='height')


def show_image_for_duration(win, img_path, seconds, size=0.3, pos=(0, 0)):
    if not os.path.exists(img_path):
        # Draw a placeholder rect if image missing
        rect = visual.Rect(win, width=size, height=size, fillColor='grey', lineColor='black', pos=pos)
        rect.draw()
        win.flip()
        core.wait(seconds)
        return
    stim = visual.ImageStim(win, image=img_path, size=size, pos=pos)
    stim.draw()
    win.flip()
    core.wait(seconds)


def wait_seconds(seconds):
    core.wait(seconds)


def get_numeric_response(win, prompt_text):
    """
    Collect digits until 'return' is pressed. Backspace supported.
    Returns the string (can be "").
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
            if name in [str(d) for d in range(10)]:  # digits 0-9
                response += name
                entry.text = response
            elif name in ('backspace',):
                response = response[:-1]
                entry.text = response
            elif name in ('return', 'enter'):
                return response
            elif name in ('escape',):
                win.close()
                core.quit()

def send_marker(win, value):
    """Send a marker value via LSL."""
    win.callOnFlip(outlet.push_sample, [value])

# Main flow
def main():
    # Window in height units for easy scaling; grey background
    win = visual.Window(size=[1280, 800], units='pix', color=[0.5, 0.5, 0.5], fullscr=False)

    show_text_and_wait(win, 'Press space bar to begin task.', wait_keys=('space',), pos=(0, 0), height=0.04)

    cross = draw_crosshair(win, color='black')

    # Prepare trial list
    standard_circle = visual.Circle(win, radius=circle_radius_px,
                                    fillColor=[-0.25, -0.25, 1.0],  # blue-ish
                                    lineColor=[-0.25, -0.25, 1.0])
    oddball_circle = visual.Circle(win, radius=circle_radius_px,
                                   fillColor=[1.0, -1.0, -1.0],  # red
                                   lineColor=[1.0, -1.0, -1.0])
    # Build an exact-length sequence with the desired oddball proportion
    n_oddballs = int(round(NUM_TRIALS * PROBABILITY_ODD))
    n_standards = NUM_TRIALS - n_oddballs
    circles = ([MARK_ODDBALL] * n_oddballs) + ([MARK_STANDARD] * n_standards)
    random.shuffle(circles)

    counter = 0
    quit_keys = ['escape']

    for i, circle in enumerate(circles, start=1):
        stim = oddball_circle if circle == MARK_ODDBALL else standard_circle

        # Pre-trial fixation
        cross.draw()
        win.flip()
        core.wait(PRETRIAL_TIME)

        # Stimulus
        send_marker(win, MARK_ODDBALL if circle == MARK_ODDBALL else MARK_STANDARD)
        cross.draw()
        stim.draw()
        win.flip()
        core.wait(STIM_DISPLAY_TIME)

        # Randomize total trial length, keep ITI so total = chosen target
        total_trial_len = random.uniform(TRIAL_LEN_MIN, TRIAL_LEN_MAX)
        remaining_time = max(0.0, total_trial_len - PRETRIAL_TIME - STIM_DISPLAY_TIME)
        cross.draw()
        win.flip()
        core.wait(remaining_time)

        counter += 1

        # Blocked numeric prompt
        if counter == LEN_BLOCK:
            # Temporarily hide crosshair during prompt
            instructions2 = 'Type the number of red circles\nyou saw since the last time you were prompted,\nand press the enter key.'
            # Draw static background
            bg = visual.Rect(win, fillColor=[0.5, 0.5, 0.5], lineColor=None)
            bg.draw()
            win.flip()
            _ = get_numeric_response(win, instructions2)
            counter = 0  # reset after prompt


    # Cleanup
    end_text = write_text(win, 'Task complete!\n\nPress Enter to exit.', pos=(0, 0), height=0.06)
    end_text.draw()
    win.flip()

    # Wait for Enter or Esc
    kb = keyboard.Keyboard()
    kb.clearEvents()
    while True:
        keys = kb.getKeys(waitRelease=False)
        if any(k.name in ('return', 'enter') for k in keys):
            break
        if any(k.name == 'escape' for k in keys):
            break
        core.wait(0.01)

    core.wait(0.5)
    win.close()
    core.quit()


if __name__ == "__main__":
    main()
