import json
import os
from pathlib import Path


CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "gigabyte-keyboard-rgb"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "colour": "light_purple",
    "brightness": 2,
    "startup_apply": True,
    "vid": 0x0414,
    "pid": 0x8105,
    "interface": 3,
}

_BRIGHTNESS_LEGACY_MAP = {
    (0, 12): 0,
    (13, 62): 1,
    (63, 100): 2,
}


def _migrate_brightness(val):
    if isinstance(val, str):
        if val in ("off", "0"):
            return 0
        if val in ("dim", "1"):
            return 1
        if val in ("full", "2"):
            return 2
        try:
            val = int(val)
        except (ValueError, TypeError):
            return 2
    if isinstance(val, int):
        if val in (0, 1, 2):
            return val
        for (lo, hi), mapped in _BRIGHTNESS_LEGACY_MAP.items():
            if lo <= val <= hi:
                return mapped
    return 2


_LEGACY_COLOUR_MAP = {
    "blush_pink_dim": "blush_pink",
}


def _migrate_colour(col):
    if not col:
        return DEFAULT_CONFIG["colour"]
    col = col.lower().replace(" ", "_")
    if col in _LEGACY_COLOUR_MAP:
        return _LEGACY_COLOUR_MAP[col]
    from .protocol import COLOURS
    if col in COLOURS:
        return col
    old_to_new = {
        "rainbow": DEFAULT_CONFIG["colour"],
    }
    return old_to_new.get(col, col)


def load():
    config = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            if "brightness" in data:
                data["brightness"] = _migrate_brightness(data["brightness"])
            if "colour" in data:
                data["colour"] = _migrate_colour(data["colour"])
            config.update(data)
        except (json.JSONDecodeError, OSError):
            pass
    return config


def save(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    safe = dict(config)
    safe["brightness"] = int(safe.get("brightness", 2))
    CONFIG_FILE.write_text(json.dumps(safe, indent=2) + "\n")


def apply_from_config(dev):
    cfg = load()
    if not cfg.get("startup_apply", False):
        return False
    from .protocol import set_static, set_off
    brightness = cfg.get("brightness", 2)
    if brightness == 0:
        return set_off(dev)
    colour = cfg.get("colour", DEFAULT_CONFIG["colour"])
    return set_static(dev, colour, brightness)
