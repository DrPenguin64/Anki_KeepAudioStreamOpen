
from aqt import mw
from aqt.qt import (
    QAction
)
from aqt.utils import showInfo
from PyQt6.QtMultimedia import QAudio, QAudioSink, QMediaDevices

from .settings_dialog import SettingsDialog
from .audio_manager import AudioManager

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
