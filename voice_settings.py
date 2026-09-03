import json
import os

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_settings.json")

DEFAULTS = {"amplitude": 80, "pitch": 80, "speed": 125}


def load():
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH) as f:
            data = json.load(f)
        merged = dict(DEFAULTS)
        merged.update(data)
        return merged
    return dict(DEFAULTS)


def save(settings):
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)


def set_amplitude(value):
    settings = load()
    settings["amplitude"] = value
    save(settings)


def get_amplitude():
    return load()["amplitude"]
