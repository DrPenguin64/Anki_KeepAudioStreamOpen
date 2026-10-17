from aqt import mw
from aqt.qt import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from aqt.utils import showInfo
from .audio_manager import get_amplitude

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
            "Noise (not implemented yet)", "noise"
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

        #form.addRow("Tone mode:", self.tone_combo)
        self.mode_label = QLabel("Tone mode:")
        form.addRow(self.mode_label, self.tone_combo)

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
            self.update_method_options
        )
        self.method_combo.currentIndexChanged.connect(
            self.update_status
        )

        self.apply_button.clicked.connect(self.apply_settings)
        self.start_button.clicked.connect(self.start_audio)
        self.stop_button.clicked.connect(self.stop_audio)
        self.close_button.clicked.connect(self.close)

        self.update_method_options()
        self.update_controls()
        self.update_status()

    def update_controls(self, *_):
        is_custom = self.tone_combo.currentData() == "custom"
        self.amplitude_spin.setEnabled(is_custom)
    def update_method_options(self, *_):
        method = self.method_combo.currentData()
        previous_value = self.tone_combo.currentData()

        self.tone_combo.blockSignals(True)
        self.tone_combo.clear()

        if method == "noise":
            self.mode_label.setText("Noise type:")
            self.tone_combo.addItem("White noise", "white")
            self.tone_combo.addItem("Pink noise", "pink")
            self.tone_combo.addItem("Brown noise", "brown")

            # Restore the previous noise type if possible.
            index = self.tone_combo.findData(previous_value)
            if index < 0:
                index = 0
            self.tone_combo.setCurrentIndex(index)

        else:
            self.mode_label.setText("Tone mode:")
            self.tone_combo.addItem("Loud tone", "tone")
            self.tone_combo.addItem(
                "Very quiet tone (try this if silence doesn't work!)",
                "inaudible",
            )
            self.tone_combo.addItem("Silence", "silent")
            self.tone_combo.addItem("Custom amplitude", "custom")

            index = self.tone_combo.findData(previous_value)
            if index < 0:
                index = self.tone_combo.findData(
                    self.manager.config.get("tone_mode", "inaudible")
                )
            if index < 0:
                index = 1
            self.tone_combo.setCurrentIndex(index)

        self.tone_combo.blockSignals(False)
        self.update_controls()


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
        method = self.method_combo.currentData()

        settings["method"] = method

        if method == "noise":
            settings["noise_type"] = self.tone_combo.currentData()
        else:
            settings["tone_mode"] = self.tone_combo.currentData()

        settings["custom_amplitude"] = self.amplitude_spin.value()

        try:
            # __name__ here is the submodule name, so use the add-on root.
            mw.addonManager.writeConfig(
                __name__.split(".")[0], settings
            )
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
