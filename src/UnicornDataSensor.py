from . import UnicornData
import numpy as np
import mne


class UnicornDataSensor(UnicornData):
    def __init__(self, xdf_path, channels=['Fz']):
        super().__init__(xdf_path, delay=0, remove_last_event=False)
        self.filter(l_freq=0.1, h_freq=30, notch_freqs=[50])
        self.create_epochs(picks=channels, event_dict=dict(standard=1), tmin=-0.2, tmax=1)

    def plot(self, confidence_interval=0.5, picks='eeg'):
        evokeds = dict(
            standard=list(self.epochs["standard"].iter_evoked()),
        )
        mne.viz.plot_compare_evokeds(evokeds, combine="mean", ci=confidence_interval, picks=picks)

    def get_fixed_delay(self) -> (int, int):
        # Calculate the time delay for first peak
        delays = []
        for i, marker in enumerate(self.marker_data):
            if marker == 1:
                eeg_start_index = np.argmax(self.eeg_time >= self.marker_time[i]) - 1
                eeg_end_index = int(eeg_start_index + self.raw.info['sfreq'])  # 1 second after the marker
                # Find the index of the maximum value in the epoch data for channel 'Fz' (index 0)
                epoch_data = self.eeg_data[eeg_start_index:eeg_end_index, 0]
                peak_value = np.max(epoch_data)
                threshold = 0.5 * peak_value
                peak_index = np.argmax(epoch_data >= threshold)
                # Convert index to time in milliseconds
                peak_time = (peak_index / self.raw.info['sfreq']) * 1000
                delays.append(peak_time)
        print(delays)
        # Return mean and standard deviation of delays
        return int(np.mean(delays)), int(np.std(delays))
