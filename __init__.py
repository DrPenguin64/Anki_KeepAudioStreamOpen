
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
config.setdefault("noise_volume", 0.1)





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
