
import math
import struct

from aqt import mw
from aqt.qt import QTimer
from aqt.utils import showInfo
from PyQt6.QtMultimedia import QAudio, QAudioSink, QMediaDevices


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
