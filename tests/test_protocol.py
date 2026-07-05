import pytest
from gigabyte_keyboard_rgb.protocol import (
    make_checksum, make_command, COLOURS, COLOUR_MAP, BRIGHTNESS_LABELS,
    set_static,
)


def test_red_full():
    cmd = make_command(0x01, 0x06, 0x64, 0x01)
    expected = bytes([0x08, 0x00, 0x01, 0x06, 0x64, 0x01, 0x01, 0x8A])
    assert cmd == expected


def test_eleven_colours():
    assert len(COLOUR_MAP) == 11
    expected = {
        "red", "green", "yellow", "blue", "orange", "dark_yellow",
        "purple", "light_purple", "white", "light_blue", "blush_pink",
    }
    assert set(COLOUR_MAP.keys()) == expected


def test_all_colours_have_3_levels():
    for name, mapping in COLOUR_MAP.items():
        assert set(mapping.keys()) == {0, 1, 2}, f"{name} missing levels"


def test_colour_map_red():
    assert COLOUR_MAP["red"][0] == (0x01, 0x00)
    assert COLOUR_MAP["red"][1] == (0x01, 0x19)
    assert COLOUR_MAP["red"][2] == (0x01, 0x64)


def test_colour_map_orange():
    assert COLOUR_MAP["orange"][1] == (0x05, 0x19)
    assert COLOUR_MAP["orange"][2] == (0x05, 0x32)


def test_colour_map_dark_yellow():
    assert COLOUR_MAP["dark_yellow"][1] == (0x05, 0x4B)
    assert COLOUR_MAP["dark_yellow"][2] == (0x05, 0x64)


def test_colour_map_light_blue_dim():
    assert COLOUR_MAP["light_blue"][1] == (0x07, 0x5A)
    assert COLOUR_MAP["light_blue"][2] == (0x07, 0x64)


def test_colour_map_light_purple_dim():
    assert COLOUR_MAP["light_purple"][1] == (0x06, 0x5A)
    assert COLOUR_MAP["light_purple"][2] == (0x06, 0x64)


def test_colour_map_blush_pink():
    assert COLOUR_MAP["blush_pink"][0] == (0x07, 0x00)
    assert COLOUR_MAP["blush_pink"][1] == (0x06, 0x4B)
    assert COLOUR_MAP["blush_pink"][2] == (0x07, 0x4B)


def test_checksum_roundtrip():
    for b2 in range(0x01, 0x0E):
        for b3 in range(0x01, 0x0B):
            d = [0x08, 0x00, b2, b3, 0x64, 0x01, 0x01]
            cs = make_checksum(d)
            computed = (255 - sum(d[:7])) & 0xFF
            assert cs == computed


def test_brightness_labels():
    for k, v in BRIGHTNESS_LABELS.items():
        assert k in (0, 1, 2)
        assert v in ("off", "dim", "full")


class FakeDev:
    def __init__(self):
        self.last_cmd = None
    def ctrl_transfer(self, *args):
        self.last_cmd = args[-1]
        return 8


def test_set_static_blush_pink_dim():
    dev = FakeDev()
    set_static(dev, "blush_pink", 1)
    assert dev.last_cmd == bytes([0x08, 0x00, 0x01, 0x06, 0x4B, 0x06, 0x01, 0x9E])


def test_set_static_blush_pink_full():
    dev = FakeDev()
    set_static(dev, "blush_pink", 2)
    assert dev.last_cmd == bytes([0x08, 0x00, 0x01, 0x06, 0x4B, 0x07, 0x01, 0x9D])


def test_set_static_invalid_colour():
    dev = FakeDev()
    assert set_static(dev, "nonexistent", 2) is False
    assert dev.last_cmd is None