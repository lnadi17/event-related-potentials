import mne
import numpy as np
from matplotlib import pyplot as plt

from ExperimentData import ExperimentData


class ExperimentDataVEP(ExperimentData):
    def __init__(self, xdf_path, min_frequency=0.5, max_frequency=30, tmin=-0.2, tmax=0.5, bad_ch=None, delay=0):
        super().__init__(xdf_path, delay)
        self.tmin = tmin
        self.tmax = tmax
        self._filter_data(min_frequency, max_frequency)
        self._create_montage()
        self._filter_markers()
        self._read_trials()
        if bad_ch is not None:
            self._raw.info["bads"].append(bad_ch)
            self._filter_markers()

    def _filter_markers(self):
        events = []
        for i, marker in enumerate(self.marker_data):
            eeg_start_index = np.argmax(self.eeg_time >= self.marker_time[i]) - 1
            events.append([eeg_start_index, 0, marker])
        events = np.array(events)
        event_dict = dict(standard=1, oddball=2)
        self._epochs = mne.Epochs(self._raw, events, event_id=event_dict, tmin=self.tmin, tmax=self.tmax, preload=True,
                                  baseline=(None, 0 if self.tmin < 0 else None))

    def _create_montage(self):
        montage = mne.channels.make_standard_montage("standard_1020")
        self._raw.set_montage(montage)

    def _filter_data(self, min_frequency, max_frequency):
        mne.set_log_level('WARNING')
        info = mne.create_info(ch_names=['Fz', 'C3', 'Cz', 'C4', 'Pz', 'PO7', 'Oz', 'PO8'], ch_types=['eeg'] * 8,
                               sfreq=250)
        raw = mne.io.RawArray([1e-6 * self.eeg_data[:, i] for i in range(8)], info)
        raw.notch_filter(freqs=[50])
        raw.filter(min_frequency, max_frequency)
        self._raw = raw
        self.eeg_data = np.transpose(raw.get_data())

    def _read_trials(self):
        self.trials = []
        # The 'trial-begin' and 'trial-end' are the usual markers to look for.
        # However, if 'trial-begin' is followed by 'response-received-enter' before getting to 'trial-end', it isn't a real trial and must be skipped.
        for i, marker in enumerate(self.marker_data):
            if marker == 'trial-begin':
                if self.marker_data[i + 1] in ['oddball', 'standard'] and self.marker_data[i + 2] == 'trial-end':
                    eeg_start_index = np.argmax(self.eeg_time >= self.marker_time[
                        i]) - 1  # Max timestamp that is less than current marker time (trial-begin)
                    eeg_end_index = np.argmax(self.eeg_time >= self.marker_time[i + 2])
                    marker_time = self.marker_time[i:i + 3]
                    marker_data = self.marker_data[i:i + 3]
                    self.trials.append(
                        (self.eeg_time[eeg_start_index:eeg_end_index], self.eeg_data[eeg_start_index:eeg_end_index, :],
                         marker_time, marker_data))
                else:
                    print(
                        f'Incorrect trial, two following events are {self.marker_data[i + 1]} and {self.marker_data[i + 2]}')
                    pass

    def _plot_markers(self, ax, x_values, y_coord, labels):
        for x, label in zip(x_values, labels):
            ax.vlines(x, ymin=-y_coord, ymax=y_coord, colors='r', linestyles='dashed')
            ax.text(x, y_coord, label, rotation=90, verticalalignment='bottom', horizontalalignment='right')

    def plot_all_channels(self, duration=30):
        self._raw.plot(duration=duration, scalings='auto')

    def plot_channel(self, channel_index=0, show_markers=False):
        fig, ax = plt.subplots()
        ax.plot(self.eeg_time, self.eeg_data[:, channel_index])
        if show_markers:
            # Create vertical lines
            label_y_coord = np.max(np.abs(self.eeg_data[:, channel_index]))
            self._plot_markers(ax, self.marker_time, label_y_coord, self.marker_data)

    def plot_fft(self, channel_index=0):
        fig, ax = plt.subplots()
        signal_fft = np.fft.rfft(self.eeg_data[:, channel_index])
        signal_spectrum = abs(signal_fft)
        freq = np.fft.rfftfreq(len(self.eeg_data[:, channel_index]), 1. / 250)  # 250 is the sampling rate
        ax.plot(freq, signal_spectrum)
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('Amplitude')

    def plot_trial(self, trial_index, show_markers=True):
        # Plots a trial from 'trial-begin' to 'trial-end' event
        eeg_time, eeg_data, marker_time, marker_data = self.trials[trial_index]
        fig, ax = plt.subplots()
        ax.plot(eeg_time - min(eeg_time), eeg_data)
        if show_markers:
            # Create vertical lines
            label_y_coord = np.max(np.abs(eeg_data))
            self._plot_markers(ax, marker_time - min(eeg_time), label_y_coord, marker_data)

    def plot_sensors(self):
        self._raw.plot_sensors(show_names=True)

    def plot_epochs(self):
        self._epochs.plot(scalings='auto', events=True, n_epochs=1)

    def plot_epoch(self, epoch_index):
        # Plots a single epoch, starting from tmin before stimulus, and ending after tmax time
        self._epochs[epoch_index].plot(events=True, scalings='auto')

    def plot_compare_conditions(self, confidence_interval=0.95, picks=None):
        evokeds = dict(
            standard=list(self._epochs["standard"].iter_evoked()),
            oddball=list(self._epochs["oddball"].iter_evoked()),
        )
        mne.viz.plot_compare_evokeds(evokeds, combine="mean", ci=confidence_interval, picks=picks)
