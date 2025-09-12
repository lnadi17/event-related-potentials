# MMN Oddball (single deviant) with PsychoPy + LSL
# Style-matched to your visual oddball template.
from psychopy import visual, core, event, logging, sound
from psychopy.visual import Window
from psychopy.hardware import keyboard
from pylsl import StreamInfo, StreamOutlet
import numpy as np
import random
import os
import csv
from datetime import datetime
import cv2 

# -------------------- Config --------------------
TITLE = "MMN Oddball (single deviant)"
SOA = 0.500                 # 500 ms onset-to-onset
TONE_DUR = 0.075            # 75 ms tone
RAMP_MS = 5                 # 5 ms linear ramps
DEV_PROB = 0.10             # deviant probability after initial standards
INIT_STANDARDS = 15         # first tones of each block forced to standards
N_BLOCKS = 3                # three 5-minute sequences
BLOCK_LEN_S = 5 * 60        # 5 minutes per block

# PsychoPy window settings (same style)
fullscr = False
win_size = [1280, 800]
bg_color = [0.5, 0.5, 0.5]  # grey

# Media (under psychopy-experiments/media)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR, 'media')
VIDEO_FILE = os.path.join(MEDIA_DIR, 'draw.mp4')  # optional; muted
VIDEO_SCALE = 0.5
# Output
OUT_CSV = os.path.join(BASE_DIR, f"mmn_oddball_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

# Tones: 3-partial harmonic standard; deviant is +10% on each partial
F_STD_PARTIALS = (500.0, 1000.0, 1500.0)
F_DEV_PARTIALS = tuple(f * 1.10 for f in F_STD_PARTIALS)

# LSL markers
MARK_STANDARD = 1
MARK_DEVIANT = 2

# -------------------- LSL --------------------
info = StreamInfo(name='PsychopyMarkerStream', type='Markers',
                  channel_count=1, channel_format='int32',
                  source_id='mmn_oddball_unique')
outlet = StreamOutlet(info)

def get_native_video_size(path):
    # Try OpenCV first (most reliable)
    try:
        import cv2
        cap = cv2.VideoCapture(path)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    # Fallback: let PsychoPy open it temporarily and read size, then close
    try:
        tmp = visual.MovieStim3(win, filename=path, noAudio=True, size=None)
    except Exception:
        tmp = visual.MovieStim(win, filename=path, noAudio=True, size=None)
    # These attributes work across versions; if not, last resort is win.size
    nat = getattr(tmp, 'movie', None)
    if hasattr(nat, 'size'):
        w, h = nat.size
    else:
        w, h = tmp.size  # current draw size; close to native if size=None
    try:
        tmp.pause(); tmp._unload()  # be nice to resources
    except Exception:
        pass
    return int(w), int(h)
    
def send_marker(win, value):
    """Send a marker value exactly on next flip."""
    win.callOnFlip(outlet.push_sample, [int(value)])

# -------------------- Logging --------------------
logging.console.setLevel(logging.INFO)

# -------------------- UI helpers (style-aligned) --------------------
def write_text(win, text, pos=(0, 0), height=0.04, wrapWidth=1.5, bold=False):
    return visual.TextStim(
        win, text=text, pos=pos, height=height, wrapWidth=wrapWidth,
        bold=bold, color='black', alignText='center', anchorVert='center', units='height'
    )

def show_text_and_wait(win, text, wait_keys=('space',), pos=(0, 0.0), height=0.04):
    stim = write_text(win, text, pos=pos, height=height)
    stim.draw()
    win.flip()
    kb = keyboard.Keyboard()
    kb.clearEvents()
    event.clearEvents()
    kb.waitKeys(keyList=list(wait_keys))

def draw_crosshair(win, size=0.05, color='black'):
    return visual.TextStim(win, text='+', height=size, color=color, bold=True, units='height')

# -------------------- Tone synth --------------------
def synth_harmonic_tone(partials_hz, dur_s, ramp_ms=5, sr=44100, rel_amps_db=(0, -3, -6)):
    """3-partial harmonic tone with linear ramps; relative amps in dB (0, -3, -6)."""
    n = int(dur_s * sr)
    t = np.arange(n) / sr
    amps = [10 ** (a/20.0) for a in rel_amps_db]
    wave = np.zeros(n, dtype=np.float32)
    for i, f in enumerate(partials_hz):
        wave += amps[i] * np.sin(2*np.pi*f*t, dtype=np.float32)
    wave /= (np.max(np.abs(wave)) + 1e-9)
    ramp_n = int((ramp_ms/1000.0) * sr)
    if ramp_n > 0:
        ramp = np.linspace(0, 1, ramp_n, dtype=np.float32)
        wave[:ramp_n] *= ramp
        wave[-ramp_n:] *= ramp[::-1]
    return wave

# -------------------- Main flow --------------------
def main():

    # Window
    win = visual.Window(size=win_size, units='pix', color=bg_color, fullscr=fullscr)    
    kb = keyboard.Keyboard()
    cross = draw_crosshair(win, color='black')
    
    # compute scaled size that preserves aspect ratio
    vid_w, vid_h = get_native_video_size(VIDEO_FILE)
    win_w, win_h = win.size
    target_h = int(round(win_h * VIDEO_SCALE))
    aspect = vid_w / float(vid_h) if vid_h else 1.0
    target_w = int(round(target_h * aspect))
    
    # Video (muted) — keep native size; support MovieStim3 fallback to MovieStim
    movie = None
    if os.path.exists(VIDEO_FILE):
       # create the real movie at the scaled size and center it
        try:
            movie = visual.MovieStim3(win, filename=VIDEO_FILE, noAudio=True, size=(target_w, target_h))
        except Exception:
            movie = visual.MovieStim(win, filename=VIDEO_FILE, noAudio=True, size=(target_w, target_h))

        movie.pos = (0, 0)

    # Prepare tones
    std_wave = synth_harmonic_tone(F_STD_PARTIALS, TONE_DUR, RAMP_MS)
    dev_wave = synth_harmonic_tone(F_DEV_PARTIALS, TONE_DUR, RAMP_MS)
    std_tone = sound.Sound(value=std_wave, sampleRate=44100, stereo=True, hamming=False)
    dev_tone = sound.Sound(value=dev_wave, sampleRate=44100, stereo=True, hamming=False)
    std_tone.setVolume(1.0)
    dev_tone.setVolume(1.0)

    # Instructions
    show_text_and_wait(
        win,
        "Press SPACE to begin.\n\nWatch the (muted) video and ignore the sounds.\nThere is no response task.",
        wait_keys=('space',), pos=(0, 0), height=0.045
    )

    # CSV
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["timestamp_iso","block","trial","marker","is_deviant",
                         "soa_s","tone_dur_s","std_partials_hz","dev_partials_hz"])

    # Blocks
    for block in range(1, N_BLOCKS + 1):
        block_clock = core.Clock()
        trial = 0

        if movie:
            try:
                movie.play()
            except Exception:
                pass

        while block_clock.getTime() < BLOCK_LEN_S:
            trial += 1

            # Decide deviant vs standard
            if trial <= INIT_STANDARDS:
                is_dev = False
            else:
                is_dev = (random.random() < DEV_PROB)

            # Draw current video frame (behind) and flip with marker at onset
            if movie:
                movie.draw()
            send_marker(win, MARK_DEVIANT if is_dev else MARK_STANDARD)
            win.flip()

            # Play tone (75 ms)
            if is_dev:
                dev_tone.play()
                marker = MARK_DEVIANT
            else:
                std_tone.play()
                marker = MARK_STANDARD

            core.wait(TONE_DUR)

            # Keep video updating to complete SOA
            remaining = max(0.0, SOA - TONE_DUR)
            t0 = core.getTime()
            while (core.getTime() - t0) < remaining:
                if movie:
                    movie.draw()
                win.flip()

            # Log trial
            with open(OUT_CSV, "a", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow([
                    datetime.now().isoformat(timespec='milliseconds'),
                    block, trial, marker, int(is_dev),
                    SOA, TONE_DUR,
                    ";".join(map(lambda x: str(int(x)), F_STD_PARTIALS)),
                    ";".join(map(lambda x: str(int(x)), F_DEV_PARTIALS))
                ])

            # Quit check
            for k in kb.getKeys(waitRelease=False):
                if k.name == 'escape':
                    if movie:
                        try: movie.pause()
                        except Exception: pass
                    win.close(); core.quit()

        # Pause between 5-min blocks; require explicit continue
        if movie:
            try: movie.pause()
            except Exception: pass

        msg = write_text(
            win,
            f"Block {block}/{N_BLOCKS} complete (5 minutes).\n\n"
            "Press SPACE or click to continue.",
            pos=(0, 0), height=0.05
        )
        msg.draw(); win.flip()

        mouse = event.Mouse(visible=True, win=win)
        while True:
            if any(mouse.getPressed()):
                break
            keys = kb.getKeys(waitRelease=False)
            if any(k.name == 'space' for k in keys):
                break
            core.wait(0.02)

    # Cleanup
    end_text = write_text(win, f"Task complete!\n\nData saved to:\n{os.path.basename(OUT_CSV)}\n\nPress Enter to exit.", pos=(0, 0), height=0.06)
    end_text.draw()
    win.flip()

    kb.clearEvents()
    while True:
        keys = kb.getKeys(waitRelease=False)
        if any(k.name in ('return', 'enter') for k in keys):
            break
        if any(k.name == 'escape' for k in keys):
            break
        core.wait(0.01)

    core.wait(0.3)
    if movie:
        try: movie.stop()
        except Exception: pass
    win.close()
    core.quit()

if __name__ == "__main__":
    main()
