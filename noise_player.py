
import random
import struct


class NoisePlayer:
    """Generates white-noise audio chunks."""

    def __init__(self, amplitude=0.01):
        self.amplitude = amplitude

    def set_amplitude(self, amplitude):
        self.amplitude = max(0.0, min(float(amplitude), 1.0))

    def make_chunk(self, frame_count, sample_rate, channels):
        """Generate interleaved float32 white-noise samples."""
        sample_count = frame_count * channels

        samples = (
            random.uniform(-self.amplitude, self.amplitude)
            for _ in range(sample_count)
        )

        return struct.pack(
            "<" + "f" * sample_count,
            *samples,
        )
