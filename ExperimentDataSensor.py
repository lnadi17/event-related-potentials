from ExperimentDataVEP import ExperimentDataVEP
import numpy as np
import mne


class ExperimentDataSensor(ExperimentDataVEP):
    def __init__(self, xdf_path, min_frequency=0.5, max_frequency=30, tmin=-0.2, tmax=0.5, bad_ch=None):
        super().__init__(xdf_path, min_frequency, max_frequency, tmin, tmax, bad_ch)

    def _filter_markers(self):
        events = []
        for i, marker in enumerate(self.marker_data):
            eeg_start_index = np.argmax(self.eeg_time >= self.marker_time[i]) - 1
            events.append([eeg_start_index, 0, marker])
        events = np.array(events)
        event_dict = dict(standard=1)
        self._epochs = mne.Epochs(self._raw, events, event_id=event_dict, tmin=self.tmin, tmax=self.tmax, preload=True,
                                  baseline=(None, 0 if self.tmin < 0 else None))

    def plot(self, confidence_interval=0.5, picks='eeg'):
        evokeds = dict(
            standard=list(self._epochs["standard"].iter_evoked()),
        )
        mne.viz.plot_compare_evokeds(evokeds, combine="mean", ci=confidence_interval, picks=picks)

    def plot_compare_conditions(self, confidence_interval=0.5, picks='eeg'):
        raise NotImplementedError("This method is not implemented for ExperimentDataSensor.")