# Import necessary PsychoPy modules
from psychopy import visual, core, event, logging
from psychopy.visual import Window
from pylsl import StreamInfo, StreamOutlet

import random

# Configurable parameters
total_trials = 400  # Total number of trials
total_trial_len = 1  # Length of each trial (in seconds)
stimulus_time = 0.2  # Duration to show the stimulus (in seconds)
prestimulus_time = 0.2  # Duration of prestimulus (in seconds)

info = StreamInfo(name='PsychopyMarkerStream', type='Markers', channel_count=1,
                  channel_format='int32', source_id='uniqueid12345')
# Initialize the stream.
outlet = StreamOutlet(info)



# Set up the Window
win = Window(
    size=[800, 600],
    units="pix",
    fullscr=False,
    color=[-1, -1, -1]  # Black background
)


# Wait for user input (key press) to start the experiment
start_message = visual.TextStim(win, text="Press any key to start the experiment...", color="white")
start_message.draw()
win.flip()  # Display message to the participant
event.waitKeys(keyList=["return"])  # Wait for any key press


# Create a white square stimulus
stimulus = visual.Rect(win, width=200, height=200, fillColor="white", lineColor="white")

# Start the experiment
for trial in range(total_trials):
    logging.info(f"Trial {trial + 1} of {total_trials}")

    # Display the prestimulus (blank black screen)
    win.flip()
    core.wait(prestimulus_time)


    # Show stimulus (white square)
    stimulus.draw()
    # Send marker for stimulus
    win.callOnFlip(outlet.push_sample, [1])
    win.flip()
    core.wait(stimulus_time)

    # End of trial, intertrial interval
    win.flip()  # Blank screen
    core.wait(total_trial_len - prestimulus_time - stimulus_time)  # Remaining time in trial

# End the experiment and close the window
win.close()
core.quit()
