import os

import mne
import numpy as np
import pyxdf


class UnicornData:
    def _read_metadata(self, original_filename):
        # Read info of the first stream
        info = self._eeg_stream['info']
        self.metadata = {
            "effective_sample_rate": info['effective_srate'],
            "markers": list(set(self.marker_data)),
            "original_filename": original_filename
        }

    def _read_eeg_data(self):
        # Read data of the first stream
        self.eeg_time = self._eeg_stream['time_stamps']
        self._time_offset = min(self.eeg_time)
        self.eeg_time = self.eeg_time - self._time_offset - self._delay
        self.eeg_data = self._eeg_stream['time_series'][:, :8]
        # self.accelerometer_data = self._xdf_data[0]['time_series'][:, 8:11]
        # self.gyroscope_data = self._xdf_data[0]['time_series'][:, 11:14]
        # self.battery_level_data = self._xdf_data[0]['time_series'][:, 14]
        # self.counter_data = self._xdf_data[0]['time_series'][:, 15]
        # self.validation_indicator_data = self._xdf_data[0]['time_series'][:, 16]

    def _read_marker_data(self):
        # Read data of the second stream
        self.marker_time = self._marker_stream['time_stamps']
        self.marker_time = self.marker_time - self._time_offset
        self.marker_data = [x[0] for x in self._marker_stream['time_series']]

    def _create_raw_data(self):
        # Create raw data
        info = mne.create_info(ch_names=['Fz', 'C3', 'Cz', 'C4', 'Pz', 'PO7', 'Oz', 'PO8'], ch_types=['eeg'] * 8,
                               sfreq=250)
        raw = mne.io.RawArray([1e-6 * self.eeg_data[:, i] for i in range(8)], info)
        self.raw = raw

    def filter(self, l_freq=0.5, h_freq=30, notch_freqs=[50]):
        self.raw.notch_filter(freqs=notch_freqs)
        self.raw.filter(l_freq, h_freq)
        return self

    def _create_montage(self):
        montage = mne.channels.make_standard_montage("standard_1020")
        self.raw.set_montage(montage)

    def _parse_events(self):
        events = []
        for i, marker in enumerate(self.marker_data):
            eeg_start_index = np.argmax(self.eeg_time >= self.marker_time[i]) - 1
            events.append([eeg_start_index, 0, marker])
        events = np.array(events)
        # NOTE: We remove the last event because it is an artifact (end of recording)
        if self._remove_last_event:
            events = events[:-1, :]
        self.events = events

    def create_epochs(self, picks=None, event_dict=None, tmin=-0.2, tmax=1, reject_criteria=None):
        epochs = mne.Epochs(self.raw.copy(), self.events, event_id=event_dict, tmin=tmin, tmax=tmax, preload=True,
                            baseline=(None, 0 if tmin < 0 else None), picks=picks, reject=reject_criteria)
        self.epochs = epochs
        return epochs

    def __init__(self, xdf_path, delay=0, remove_last_event=True):
        self._remove_last_event = remove_last_event
        self._xdf_data = pyxdf.load_xdf(xdf_path)[0]
        self._delay = delay
        # Ensure we read correct streams
        for stream in self._xdf_data:
            stream_type = stream['info']['type'][0]
            stream_size = int(stream['footer']['info']['sample_count'][0])
            print(stream_type, stream_size)
            if stream_type == 'Data' and stream_size > 0:
                self._eeg_stream = stream
            if stream_type == 'Markers' and stream_size > 0:
                self._marker_stream = stream
        assert self._eeg_stream is not None, "No EEG stream found in the XDF file."
        assert self._marker_stream is not None, "No marker stream found in the XDF file."
        self._read_eeg_data()
        self._read_marker_data()
        self._read_metadata(os.path.basename(xdf_path))
        self._create_raw_data()
        self._create_montage()
        self._parse_events()
