
import math
import struct

from aqt import mw
from aqt.qt import QTimer
from aqt.utils import showInfo
from PyQt6.QtMultimedia import QAudio, QAudioSink, QMediaDevices

device = QMediaDevices.defaultAudioOutput()
fmt = device.preferredFormat()

sink = QAudioSink(device, fmt, mw)
output = sink.start()  # Push mode: Qt supplies the writable device.

if output is None:
    showInfo(f"Audio start failed: {sink.error()}")
else:
    sample_rate = fmt.sampleRate()
    channels = fmt.channelCount()
    sample_format = fmt.sampleFormat()

    # Generate 20 ms of quiet stereo/mono audio per write.
    frame_count = max(1, sample_rate // 50)
    frame_index = 0

    def make_chunk():
        global frame_index

        samples = []
        for i in range(frame_count):
            value = 0.001 * math.sin(
                2 * math.pi * 997 * (frame_index + i) / sample_rate
            )
            samples.extend([value] * channels)

        frame_index += frame_count

        if sample_format == fmt.SampleFormat.Float:
            return struct.pack(
                "<" + "f" * len(samples), *samples
            )

        raise RuntimeError(
            f"Unsupported sample format: {sample_format}"
        )

    def feed_audio():
        if sink.state() == QAudio.State.StoppedState:
            return

        chunk = make_chunk()
        if sink.bytesFree() >= len(chunk):
            output.write(chunk)

    timer = QTimer(mw)
    timer.timeout.connect(feed_audio)
    timer.start(10)

    mw._audio_test_sink = sink
    mw._audio_test_output = output
    mw._audio_test_timer = timer

    def finish_test():
        timer.stop()
        state = sink.state()
        error = sink.error()
        sink.stop()
        showInfo(
            f"10-second audio test finished.\n"
            f"State before stopping: {state}\n"
            f"Error: {error}"
        )

    QTimer.singleShot(10000, finish_test)
