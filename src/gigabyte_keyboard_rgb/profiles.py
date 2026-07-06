import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import usb.core

from .paths import CONFIG_DIR

BUILTIN_DATA_DIR = Path(__file__).parent / "profile_data"
USER_PROFILES_DIR = CONFIG_DIR / "profiles"

GIGABYTE_VIDS = {0x0414, 0x1044, 0x04D9}

OFF_CMD = bytes([0x08, 0x00, 0x01, 0x06, 0x00, 0x01, 0x01, 0xF2])


@dataclass
class DeviceProfile:
    vid: int
    pid: int
    name: str
    interfaces: list[int] = field(default_factory=lambda: [1, 3])
    control_interface: int = 3
    colour_map: dict[str, dict[int, tuple[int, int]]] = field(default_factory=dict)

    @property
    def id(self) -> tuple[int, int]:
        return (self.vid, self.pid)

    @property
    def colour_names(self) -> list[str]:
        return list(self.colour_map.keys())

    def colour_byte(self, name: str, level: int) -> tuple[int, int]:
        return self.colour_map[name][level]

    @property
    def full_map(self) -> dict[str, int]:
        return {name: mapping[2][0] for name, mapping in self.colour_map.items()}

    @property
    def reverse_map(self) -> dict[int, str]:
        return {v: k for k, v in self.full_map.items()}

    def to_dict(self) -> dict:
        cmap = {}
        for colour, levels in self.colour_map.items():
            cmap[colour] = {str(k): list(v) for k, v in levels.items()}
        return {
            "name": self.name,
            "vid": f"0x{self.vid:04X}",
            "pid": f"0x{self.pid:04X}",
            "interfaces": list(self.interfaces),
            "control_interface": self.control_interface,
            "colour_map": cmap,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DeviceProfile":
        vid = d["vid"] if isinstance(d["vid"], int) else int(d["vid"], 16)
        pid = d["pid"] if isinstance(d["pid"], int) else int(d["pid"], 16)
        cmap = {}
        for colour, levels in d.get("colour_map", {}).items():
            cmap[colour] = {int(k): tuple(v) for k, v in levels.items()}
        return cls(
            vid=vid,
            pid=pid,
            name=d.get("name", f"{vid:04X}:{pid:04X}"),
            interfaces=list(d.get("interfaces", [1, 3])),
            control_interface=int(d.get("control_interface", 3)),
            colour_map=cmap,
        )


def load_builtin_profiles() -> dict[tuple[int, int], DeviceProfile]:
    profiles = {}
    if not BUILTIN_DATA_DIR.is_dir():
        return profiles
    for path in sorted(BUILTIN_DATA_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
            profile = DeviceProfile.from_dict(data)
            profiles[profile.id] = profile
        except (json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
            print(f"Warning: skipping built-in profile {path.name}: {exc}", file=sys.stderr)
    return profiles


def load_user_profiles() -> dict[tuple[int, int], DeviceProfile]:
    profiles = {}
    if not USER_PROFILES_DIR.is_dir():
        return profiles
    for path in sorted(USER_PROFILES_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
            profile = DeviceProfile.from_dict(data)
            profiles[profile.id] = profile
        except (json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
            print(f"Warning: skipping user profile {path.name}: {exc}", file=sys.stderr)
    return profiles


def all_profiles() -> dict[tuple[int, int], DeviceProfile]:
    profiles = load_builtin_profiles()
    for key, profile in load_user_profiles().items():
        profiles[key] = profile
    return profiles


def detect_device() -> tuple[int, int] | None:
    try:
        for dev in usb.core.find(find_all=True):
            if dev is None:
                continue
            try:
                vid = dev.idVendor
                pid = dev.idProduct
            except (AttributeError, usb.core.USBError):
                continue
            if vid in GIGABYTE_VIDS:
                return (vid, pid)
        for dev in usb.core.find(find_all=True):
            if dev is None:
                continue
            try:
                mfr = (dev.manufacturer or "").upper()
                if "GIGABYTE" in mfr:
                    return (dev.idVendor, dev.idProduct)
            except (AttributeError, usb.core.USBError):
                continue
    except usb.core.USBError:
        pass
    return None


def resolve_profile(vid: int | None = None, pid: int | None = None) -> DeviceProfile | None:
    if vid is None or pid is None:
        detected = detect_device()
        if detected is None:
            return None
        vid, pid = detected
    return all_profiles().get((vid, pid))


def save_user_profile(profile: DeviceProfile) -> Path:
    USER_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    path = USER_PROFILES_DIR / f"{profile.vid:04X}_{profile.pid:04X}.json"
    path.write_text(json.dumps(profile.to_dict(), indent=2) + "\n")
    return path


def _test_interface(dev, iface: int) -> bool:
    from .protocol import make_command
    try:
        cmd = make_command(0x01, 0x06, 0x00, 0x01)
        dev.ctrl_transfer(0x21, 0x09, 0x0300, iface, cmd)
        return True
    except usb.core.USBError:
        return False


def _send_raw(dev, byte5: int, byte4: int, iface: int):
    from .protocol import make_command
    cmd = make_command(0x01, 0x06, byte4, byte5)
    dev.ctrl_transfer(0x21, 0x09, 0x0300, iface, cmd)


def calibrate(dev, vid: int, pid: int) -> DeviceProfile | None:
    from .protocol import make_command

    print()
    print("=" * 60)
    print("  Gigabyte Keyboard RGB — Calibration")
    print("=" * 60)
    print()
    print(f"Detected: VID={vid:04X} PID={pid:04X}")
    print()

    interfaces_to_detach = [1]
    working_iface = None

    print("Step 0: Finding control interface")
    for iface in [3, 0, 1, 2]:
        if _test_interface(dev, iface):
            print(f"  Interface {iface}: responds ✓")
            working_iface = iface
            break
        print(f"  Interface {iface}: no response")
        time.sleep(0.05)

    if working_iface is None:
        print("\nNo USB interface responded. Calibration aborted.")
        return None

    if working_iface not in interfaces_to_detach:
        interfaces_to_detach.append(working_iface)
    if 3 not in interfaces_to_detach and 3 != working_iface:
        interfaces_to_detach.append(3)

    for iface in interfaces_to_detach:
        try:
            if dev.is_kernel_driver_active(iface):
                dev.detach_kernel_driver(iface)
                print(f"  Detached kernel driver from interface {iface}")
        except (usb.core.USBError, NotImplementedError):
            pass

    time.sleep(0.2)
    print()

    PHASE1_BRIGHTNESS = 0x32
    found = {}

    print("Step 1: Identifying visible colours at medium brightness")
    print("  For each sample, type the colour name (lowercase, underscore for")
    print("  multi-word, e.g. 'light_purple').")
    print("  Enter = skip this byte, 'q' = quit, 'done' = finish early")
    print()

    for byte5 in range(0x01, 0x09):
        try:
            _send_raw(dev, byte5, PHASE1_BRIGHTNESS, working_iface)
        except usb.core.USBError:
            print(f"  byte5=0x{byte5:02X}: send failed, skipping")
            continue

        time.sleep(0.3)
        prompt = f"  Colour at byte5=0x{byte5:02X} (medium)? "
        ans = input(prompt).strip().lower().replace(" ", "_")

        if ans in ("q", "quit"):
            _send_raw(dev, 0x01, 0x00, working_iface)
            return None
        if ans in ("done", "d"):
            break
        if not ans or ans in ("skip", "none", "n"):
            continue

        found[byte5] = ans

    if not found:
        print("\nNo colours were identified. Calibration aborted.")
        _send_raw(dev, 0x01, 0x00, working_iface)
        return None

    print()
    print(f"  Found {len(found)} colour(s): {', '.join(found.values())}")
    print()

    colour_map: dict[str, dict[int, tuple[int, int]]] = {}

    print("Step 2: Checking for hue variation at dim (0x19) and full (0x64)")
    print("  For each colour, we'll send dim then full and ask if it's the same.")
    print()

    for byte5, base_name in sorted(found.items()):
        dim_name = base_name
        full_name = base_name

        try:
            _send_raw(dev, byte5, 0x19, working_iface)
        except usb.core.USBError:
            continue
        time.sleep(0.3)
        ans = input(f"  '{base_name}' at dim (0x19) — same colour? [Y/n] ").strip().lower()
        if ans == "n":
            dim_name = input("    Name this dim colour: ").strip().lower().replace(" ", "_")
            if not dim_name:
                dim_name = base_name

        try:
            _send_raw(dev, byte5, 0x64, working_iface)
        except usb.core.USBError:
            continue
        time.sleep(0.3)
        ans = input(f"  '{base_name}' at full (0x64) — same colour? [Y/n] ").strip().lower()
        if ans == "n":
            full_name = input("    Name this full colour: ").strip().lower().replace(" ", "_")
            if not full_name:
                full_name = base_name

        colour_map.setdefault(base_name, {})[1] = (byte5, PHASE1_BRIGHTNESS)
        colour_map.setdefault(base_name, {})[0] = (byte5, 0x00)

        if dim_name != base_name:
            colour_map.setdefault(dim_name, {})[1] = (byte5, 0x19)
            colour_map.setdefault(dim_name, {})[0] = (byte5, 0x00)

        if full_name != base_name:
            colour_map.setdefault(full_name, {})[2] = (byte5, 0x64)
            colour_map.setdefault(full_name, {})[0] = (byte5, 0x00)

            probe_points = [0x4B, 0x5A]
            found_dim = False
            for bp in probe_points:
                try:
                    _send_raw(dev, byte5, bp, working_iface)
                except usb.core.USBError:
                    continue
                time.sleep(0.3)
                ans = input(f"    At 0x{bp:02X} — same as '{full_name}'? [Y/n] ").strip().lower()
                if ans != "n":
                    colour_map.setdefault(full_name, {})[1] = (byte5, bp)
                    found_dim = True
                    break
            if not found_dim:
                colour_map.setdefault(full_name, {})[1] = (byte5, 0x64)

        if dim_name == base_name and full_name == base_name:
            colour_map[base_name][2] = (byte5, 0x64)
            colour_map[base_name][1] = (byte5, 0x19)

    for name in list(colour_map):
        levels = colour_map[name]
        if 2 not in levels:
            any_byte5 = next(iter(levels.values()))[0]
            levels[2] = (any_byte5, 0x64)
        if 1 not in levels:
            any_byte5 = next(iter(levels.values()))[0]
            levels[1] = (any_byte5, 0x19)
        if 0 not in levels:
            any_byte5 = next(iter(levels.values()))[0]
            levels[0] = (any_byte5, 0x00)

    _send_raw(dev, 0x01, 0x00, working_iface)

    print()
    print("Step 3: Model name")
    default_name = f"Custom {vid:04X}:{pid:04X}"
    model_name = input(f"  Model name (e.g. 'Gigabyte Aorus 15BKF')\n  [{default_name}]: ").strip()
    if not model_name:
        model_name = default_name

    profile = DeviceProfile(
        vid=vid,
        pid=pid,
        name=model_name,
        interfaces=sorted(set(interfaces_to_detach)),
        control_interface=working_iface,
        colour_map=colour_map,
    )

    print()
    print("=" * 60)
    print("  Calibration complete!")
    print("=" * 60)
    print(f"\n  {len(colour_map)} colour(s) mapped: {', '.join(sorted(colour_map.keys()))}")
    print()
    print(f"  Saved to: ~/.config/gigabyte-keyboard-rgb/profiles/")
    print(f"  To share: submit the file at")
    print(f"    https://github.com/goodeesh/gigabyte-keyboard-rgb/issues/new")
    print()

    return profile
