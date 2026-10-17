
import math
import struct

from aqt import mw
from aqt.qt import (
    QAction,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTimer,
    QVBoxLayout,
)
from aqt.utils import showInfo
from PyQt6.QtMultimedia import QAudio, QAudioSink, QMediaDevices


# Read configuration
config = mw.addonManager.getConfig(__name__) or {}

config.setdefault("method", "tone")
config.setdefault("tone_mode", "inaudible")
config.setdefault("custom_amplitude", 0.001)


AMPLITUDE_OPTIONS = {
    "tone": 0.01,
    "inaudible": 0.00001,
    "silent": 0.0,
}


def get_amplitude(settings):
    mode = settings.get("tone_mode", "inaudible")

    if mode == "custom":
        try:
            value = float(settings.get("custom_amplitude", 0.001))
        except (TypeError, ValueError):
            value = 0.001

        return max(0.0, min(value, 1.0))

    return AMPLITUDE_OPTIONS.get(mode, 0.00001)


class AudioManager:
    """Manages the persistent tone audio stream."""

    def __init__(self, settings):
        self.config = dict(settings)

        self.sink = None
        self.output = None
        self.timer = None
        self.fmt = None

        self.sample_rate = 0
        self.channels = 0
        self.frame_count = 0
        self.frame_index = 0

        self.amplitude = get_amplitude(self.config)
        self.running = False

    def start(self):
        if self.running:
            return True

        device = QMediaDevices.defaultAudioOutput()

        if device.isNull():
            showInfo("No audio output device is available.")
            return False

        fmt = device.preferredFormat()

        # The original working implementation uses float samples.
        if fmt.sampleFormat() != fmt.SampleFormat.Float:
            showInfo(
                "Unsupported audio sample format: "
                f"{fmt.sampleFormat()}"
            )
            return False

        sink = QAudioSink(device, fmt, mw)
        output = sink.start()

        if output is None:
            error = sink.error()
            sink.stop()
            sink.deleteLater()
            showInfo(f"Audio start failed: {error}")
            return False

        self.sink = sink
        self.output = output
        self.fmt = fmt

        self.sample_rate = fmt.sampleRate()
        self.channels = fmt.channelCount()
        self.frame_count = max(1, self.sample_rate // 50)
        self.frame_index = 0

        timer = QTimer(mw)
        timer.timeout.connect(self.feed_audio)
        timer.start(10)

        self.timer = timer
        self.running = True

        return True

    def stop(self):
        if self.timer is not None:
            self.timer.stop()
            self.timer.deleteLater()
            self.timer = None

        if self.sink is not None:
            self.sink.stop()
            self.sink.deleteLater()

        self.sink = None
        self.output = None
        self.fmt = None
        self.running = False

    def set_config(self, settings):
        self.config = dict(settings)
        self.amplitude = get_amplitude(self.config)

        # The existing stream uses self.amplitude for every new chunk,
        # so changes take effect without creating another stream.

    def make_chunk(self):
        samples = []

        for i in range(self.frame_count):
            value = self.amplitude * math.sin(
                2 * math.pi * 997
                * (self.frame_index + i)
                / self.sample_rate
            )
            samples.extend([value] * self.channels)

        self.frame_index += self.frame_count

        return struct.pack(
            "<" + "f" * len(samples),
            *samples,
        )

    def feed_audio(self):
        if not self.running or self.sink is None:
            return

        if self.sink.state() == QAudio.State.StoppedState:
            return

        chunk = self.make_chunk()

        if self.sink.bytesFree() >= len(chunk):
            self.output.write(chunk)


class SettingsDialog(QDialog):
    def __init__(self, manager):
        super().__init__(mw)

        self.manager = manager
        self.setWindowTitle("Keep Audio Stream Active")
        self.setMinimumWidth(390)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Playback method
        self.method_combo = QComboBox()
        self.method_combo.addItem("Tone", "tone")
        self.method_combo.addItem(
            "White noise (not implemented yet)", "noise"
        )
        self.method_combo.addItem(
            "MP3 file (not implemented yet)", "mp3"
        )

        method = self.manager.config.get("method", "tone")
        index = self.method_combo.findData(method)

        if index >= 0:
            self.method_combo.setCurrentIndex(index)

        form.addRow("Playback method:", self.method_combo)

        # Tone mode
        self.tone_combo = QComboBox()
        self.tone_combo.addItem("Loud tone", "tone")
        self.tone_combo.addItem("Very quiet tone (try this if silence doesn't work!)", "inaudible")
        self.tone_combo.addItem("Silence", "silent")
        self.tone_combo.addItem("Custom amplitude", "custom")

        tone_mode = self.manager.config.get(
            "tone_mode", "inaudible"
        )
        index = self.tone_combo.findData(tone_mode)

        if index >= 0:
            self.tone_combo.setCurrentIndex(index)

        form.addRow("Tone mode:", self.tone_combo)

        # Custom amplitude
        self.amplitude_spin = QDoubleSpinBox()
        self.amplitude_spin.setDecimals(8)
        self.amplitude_spin.setRange(0.0, 1.0)
        self.amplitude_spin.setSingleStep(0.00001)
        self.amplitude_spin.setValue(
            get_amplitude({
                "tone_mode": "custom",
                "custom_amplitude": self.manager.config.get(
                    "custom_amplitude", 0.001
                ),
            })
        )

        form.addRow("Custom amplitude:", self.amplitude_spin)
        layout.addLayout(form)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # Controls
        buttons = QHBoxLayout()

        self.apply_button = QPushButton("Apply")
        self.start_button = QPushButton("Start audio")
        self.stop_button = QPushButton("Stop audio")
        self.close_button = QPushButton("Close")

        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.close_button)

        layout.addLayout(buttons)

        self.tone_combo.currentIndexChanged.connect(
            self.update_controls
        )
        self.method_combo.currentIndexChanged.connect(
            self.update_status
        )

        self.apply_button.clicked.connect(self.apply_settings)
        self.start_button.clicked.connect(self.start_audio)
        self.stop_button.clicked.connect(self.stop_audio)
        self.close_button.clicked.connect(self.close)

        self.update_controls()
        self.update_status()

    def update_controls(self, *_):
        is_custom = self.tone_combo.currentData() == "custom"
        self.amplitude_spin.setEnabled(is_custom)

    def update_status(self, *_):
        method = self.method_combo.currentData()

        if not self.manager.running:
            status = "Audio stream is stopped."
        elif method != "tone":
            status = (
                "The selected backend is not implemented yet. "
                "The existing tone stream is still running."
            )
        else:
            status = "Tone audio stream is running."

        self.status_label.setText(status)

    def apply_settings(self):
        settings = dict(self.manager.config)

        settings["method"] = self.method_combo.currentData()
        settings["tone_mode"] = self.tone_combo.currentData()
        settings["custom_amplitude"] = (
            self.amplitude_spin.value()
        )

        try:
            mw.addonManager.writeConfig(__name__, settings)
        except Exception as exc:
            showInfo(f"Could not save settings:\n{exc}")
            return

        self.manager.set_config(settings)
        self.update_status()

    def start_audio(self):
        self.manager.start()
        self.update_status()

    def stop_audio(self):
        self.manager.stop()
        self.update_status()


# Keep one manager alive for the lifetime of Anki.
manager = AudioManager(config)
mw._keep_audio_manager = manager

# Preserve the existing behavior: start audio automatically.
manager.start()


def open_settings():
    dialog = getattr(mw, "_keep_audio_dialog", None)

    if dialog is not None and dialog.isVisible():
        dialog.raise_()
        dialog.activateWindow()
        return

    dialog = SettingsDialog(manager)
    mw._keep_audio_dialog = dialog
    dialog.show()


# Add the settings window to Anki's Tools menu.
action = QAction("Keep Audio Stream Active", mw)
action.triggered.connect(open_settings)
mw.form.menuTools.addAction(action)

# Keep a reference to the action.
mw._keep_audio_action = action
