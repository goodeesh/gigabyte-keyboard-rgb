import sys
import time
import argparse

from .protocol import (
    COLOUR_MAP,
    PROGRAMS,
    SPEEDS,
    BRIGHTNESS_LABELS,
    get_keyboard,
    send_command,
    make_command,
    print_detect,
    VID,
    PID,
    INTERFACE,
    set_static,
    set_off,
)
from .profiles import (
    detect_device,
    resolve_profile,
    calibrate as run_calibrate,
    save_user_profile,
)
from .config import load as load_config, save as save_config

_LEVEL_NAMES = {"off": 0, "dim": 1, "full": 2}


def _parse_level(val):
    if isinstance(val, str) and val.lower() in _LEVEL_NAMES:
        return _LEVEL_NAMES[val.lower()]
    try:
        v = int(val)
        if v in (0, 1, 2):
            return v
        if v <= 12:
            return 0
        if v <= 62:
            return 1
        return 2
    except (ValueError, TypeError):
        pass
    return 2


def get_dev(args):
    profile = resolve_profile(args.vid, args.pid)
    dev = get_keyboard(args.vid, args.pid, profile)
    if dev is None:
        print(f"Keyboard not found (VID={args.vid:04X} PID={args.pid:04X})")
        print("Use 'gigabyte-rgb detect' to scan for compatible keyboards.")
        sys.exit(1)
    return dev, profile


def get_dev_for(vid, pid):
    profile = resolve_profile(vid, pid)
    dev = get_keyboard(vid, pid, profile)
    if dev is None:
        print(f"Keyboard not found (VID={vid:04X} PID={pid:04X})")
        print("Use 'gigabyte-rgb detect' to scan for compatible keyboards.")
        sys.exit(1)
    return dev, profile


def list_options(profile=None):
    cmap = profile.colour_map if profile is not None else COLOUR_MAP
    print("Available effects (static is the only working one for backlight;")
    print("others may break the keyboard and require a USB reset to recover):")
    for name, val in sorted(PROGRAMS.items(), key=lambda x: x[1]):
        print(f"  {name:15s} (0x{val:02X})")
    print()
    print("Available colours:")
    for name in sorted(cmap.keys()):
        print(f"  {name}")
    print()
    print("Brightness levels: off, dim, full")
    print("Available speeds:")
    for name, val in sorted(SPEEDS.items(), key=lambda x: x[1]):
        print(f"  {name:10s} (0x{val:02X})")


def cmd_cycle(args):
    dev, profile = get_dev(args)
    cmap = profile.colour_map if profile is not None else COLOUR_MAP
    print("Cycling through colours (Ctrl+C to stop)...")
    try:
        while True:
            for colour_name in cmap:
                print(f"  {colour_name}...", end=" ", flush=True)
                set_static(dev, colour_name, args.level, profile)
                time.sleep(2)
                print()
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)


def cmd_set(effect, colour, speed, level, interface, vid, pid):
    dev, profile = get_dev_for(vid, pid)
    if effect != "static":
        print("WARNING: Non-static effects may hang the keyboard firmware.")
        print("Press Ctrl+C within 3 seconds to cancel...")
        time.sleep(3)
    prog_id = PROGRAMS.get(effect)
    if prog_id is None:
        print(f"Unknown effect: {effect}")
        sys.exit(1)
    cmap = profile.colour_map if profile is not None else COLOUR_MAP
    if colour not in cmap:
        if profile is None:
            print(f"Colour '{colour}' unknown — no profile loaded for this model.")
            print("Run 'gigabyte-rgb --calibrate' to set up your model.")
        else:
            print(f"Unknown colour: {colour}")
            print(f"Available: {', '.join(sorted(cmap.keys()))}")
        sys.exit(1)
    speed_id = SPEEDS.get(speed)
    if speed_id is None:
        try:
            speed_id = int(speed)
            if speed_id < 1 or speed_id > 10:
                raise ValueError
        except ValueError:
            print(f"Invalid speed: {speed}")
            sys.exit(1)
    ok = set_static(dev, colour, level, profile, interface)
    label = BRIGHTNESS_LABELS.get(level, f"level-{level}")
    if ok:
        print(f"Set to {colour} {effect} ({label})")
    else:
        print("Failed to send command", file=sys.stderr)
        sys.exit(1)


def cmd_reset(args):
    dev, _ = get_dev(args)
    for i in [0, 2, 4]:
        try:
            dev.attach_kernel_driver(i)
        except Exception:
            pass
    print("Keyboard drivers re-attached for interfaces 0/2/4. Typing should work.")


def cmd_detect(args):
    print_detect()


def cmd_off(args):
    dev, profile = get_dev(args)
    set_off(dev, profile)
    print("Keyboard backlight turned off.")


def cmd_calibrate(args):
    if args.vid and args.pid:
        vid, pid = args.vid, args.pid
    else:
        detected = detect_device()
        if detected is None:
            print("No Gigabyte USB keyboard detected.")
            print("Try: lsusb | grep -i gigabyte")
            sys.exit(1)
        vid, pid = detected
    existing = resolve_profile(vid, pid)
    if existing is not None:
        print(f"Model already supported: {existing.name}")
        ans = input("Re-run calibration anyway? [y/N] ").strip().lower()
        if ans != "y":
            return
    dev = get_keyboard(vid, pid)
    if dev is None:
        print(f"Keyboard not found (VID={vid:04X} PID={pid:04X})")
        sys.exit(1)
    new_profile = run_calibrate(dev, vid, pid)
    if new_profile is None:
        print("Calibration cancelled.")
        return
    path = save_user_profile(new_profile)
    print(f"\nProfile saved: {path}")
    print()
    print("To use right now:")
    print(f"  gigabyte-rgb static <colour>")
    print()
    print("To enable in the tray app:")
    print("  Open the tray menu and click 'Reload profiles'")
    print("  (or restart: systemctl --user restart gigabyte-keyboard-rgb.service)")
    print()
    print("To share with the community:")
    print("  Submit this file as a GitHub issue:")
    print("  https://github.com/goodeesh/gigabyte-keyboard-rgb/issues/new")
    print(f"  Attach: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Gigabyte Keyboard RGB Control",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  gigabyte-rgb static purple          Set static purple (full)
  gigabyte-rgb static blue --level dim  Dim blue
  gigabyte-rgb --cycle                 Cycle all colours
  gigabyte-rgb off                     Turn backlight off
  gigabyte-rgb detect                  Scan for compatible keyboards
  gigabyte-rgb --calibrate             Interactive calibration for new models
  gigabyte-rgb --list                  List all options
  gigabyte-rgb --reset                 Re-attach keyboard drivers (fix typing)
        """,
    )

    parser.add_argument("effect", nargs="?", default=None,
                        help="Effect name (default: static)")
    parser.add_argument("colour", nargs="?", default="light_purple",
                        help="Colour name")
    parser.add_argument("--level", "-l", default="full",
                        help="Brightness: off/dim/full (or 0/1/2)")
    parser.add_argument("--bright", "-b", type=int, default=None,
                        help=argparse.SUPPRESS)
    parser.add_argument("--speed", "-s", default="medium",
                        help="Speed: fastest/fast/medium/slow/slowest or 1-10")
    parser.add_argument("--interface", "-i", type=int, default=INTERFACE,
                        help=f"USB interface (default: {INTERFACE})")
    parser.add_argument("--vid", type=lambda x: int(x, 16), default=None,
                        help=f"USB vendor ID hex (default: auto-detect)")
    parser.add_argument("--pid", type=lambda x: int(x, 16), default=None,
                        help=f"USB product ID hex (default: auto-detect)")
    parser.add_argument("--list", "-L", action="store_true",
                        help="List available options")
    parser.add_argument("--cycle", "-c", action="store_true",
                        help="Cycle through colours")
    parser.add_argument("--reset", "-r", action="store_true",
                        help="Re-attach keyboard drivers")
    parser.add_argument("--calibrate", action="store_true",
                        help="Interactive calibration for unsupported models")

    args = parser.parse_args()

    if args.bright is not None:
        args.level = _parse_level(args.bright)
    else:
        args.level = _parse_level(args.level)

    if args.calibrate:
        cmd_calibrate(args)
        return

    if args.list:
        profile = resolve_profile(args.vid, args.pid)
        list_options(profile)
        return

    if args.reset:
        cmd_reset(args)
        return

    if args.cycle:
        cmd_cycle(args)
        return

    if args.effect == "detect":
        cmd_detect(args)
        return

    if args.effect == "off":
        cmd_off(args)
        return

    if args.effect is None:
        parser.print_help()
        return

    cmd_set(args.effect, args.colour, args.speed, args.level,
            args.interface, args.vid, args.pid)


if __name__ == "__main__":
    main()
