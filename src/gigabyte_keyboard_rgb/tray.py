import sys
import os
import signal

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
from gi.repository import Gtk, GLib, AppIndicator3

from .protocol import set_static, set_off, get_keyboard
from .profiles import (
    detect_device, resolve_profile, save_user_profile,
)
from .config import load as load_config, save as save_config

APP_ID = "gigabyte-keyboard-rgb"
BRIGHTNESS_NAMES = ["Off", "Dim", "Full"]


class TrayApp:
    def __init__(self):
        self._config = load_config()
        self._indicator = None
        self._menu = None
        self._colour_items = {}
        self._brightness_items = {}
        self._startup_item = None
        self._reload_item = None
        self._no_keyboard = False
        self._building = True

        self._profile = None
        self._unsupported = False
        self._detected_vid = None
        self._detected_pid = None

        self._current_colour = self._config.get("colour", "light_purple")
        self._current_brightness = self._config.get("brightness", 2)
        self._startup_apply = self._config.get("startup_apply", True)

        self._detect_on_startup()
        self._build_menu()
        self._building = False
        self._apply_on_startup()

    def _detect_on_startup(self):
        detected = detect_device()
        if detected is None:
            self._no_keyboard = True
            return
        self._detected_vid, self._detected_pid = detected
        profile = resolve_profile(self._detected_vid, self._detected_pid)
        if profile is not None:
            self._profile = profile
            self._unsupported = False
            self._current_colour = self._config.get("colour", self._profile.colour_names[0])
        else:
            self._profile = None
            self._unsupported = True

    def _get_keyboard(self):
        if self._profile is not None:
            dev = get_keyboard(vid=self._profile.vid, pid=self._profile.pid, profile=self._profile)
        elif self._detected_vid and self._detected_pid:
            dev = get_keyboard(vid=self._detected_vid, pid=self._detected_pid)
        else:
            dev = get_keyboard()
        if dev is None:
            self._show_no_keyboard()
            return None
        if self._no_keyboard:
            self._no_keyboard = False
            try:
                self._indicator.set_label("", APP_ID)
            except Exception:
                pass
        return dev

    def _show_no_keyboard(self):
        if not self._no_keyboard:
            self._no_keyboard = True
            try:
                self._indicator.set_label("No keyboard", APP_ID)
            except Exception:
                pass
        GLib.timeout_add(10000, self._retry_keyboard)

    def _retry_keyboard(self):
        detected = detect_device()
        if detected is not None:
            self._no_keyboard = False
            try:
                self._indicator.set_label("", APP_ID)
            except Exception:
                pass
            self._detected_vid, self._detected_pid = detected
            profile = resolve_profile(self._detected_vid, self._detected_pid)
            if profile is not None:
                self._profile = profile
                self._unsupported = False
                self._rebuild_menu()
                self._apply_on_startup()
        return False

    def _clear_menu(self):
        if self._menu is not None:
            self._menu.destroy()
            self._menu = None
        self._colour_items = {}
        self._brightness_items = {}

    def _rebuild_menu(self):
        self._clear_menu()
        self._building = True
        self._build_menu()
        self._building = False
        self._menu.show_all()

    def _build_menu(self):
        self._menu = Gtk.Menu()

        if self._no_keyboard:
            self._build_no_keyboard_menu()
        elif self._unsupported:
            self._build_unsupported_menu()
        else:
            self._build_supported_menu()

        if self._menu is not None:
            self._menu.show_all()

        if self._indicator is None:
            self._indicator = AppIndicator3.Indicator.new(
                APP_ID,
                "gigabyte-keyboard-rgb",
                AppIndicator3.IndicatorCategory.HARDWARE,
            )
            self._indicator.set_menu(self._menu)
            self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

    def _build_no_keyboard_menu(self):
        item = Gtk.MenuItem(label="No keyboard detected")
        item.set_sensitive(False)
        self._menu.append(item)
        self._menu.append(Gtk.SeparatorMenuItem())
        self._append_quit()

    def _build_unsupported_menu(self):
        vid = self._detected_vid or 0
        pid = self._detected_pid or 0

        header = Gtk.MenuItem(label=f"Unknown model ({vid:04X}:{pid:04X})")
        header.set_sensitive(False)
        self._menu.append(header)

        hint = Gtk.MenuItem(label="Run calibration to add support")
        hint.set_sensitive(False)
        self._menu.append(hint)

        self._menu.append(Gtk.SeparatorMenuItem())

        off_item = Gtk.RadioMenuItem(label="Off")
        off_item.set_active(True)
        off_item.connect("toggled", self._on_unsupported_off)
        self._menu.append(off_item)

        self._menu.append(Gtk.SeparatorMenuItem())

        cal_item = Gtk.MenuItem(label="Calibrate...")
        cal_item.connect("activate", self._on_calibrate)
        self._menu.append(cal_item)

        self._menu.append(Gtk.SeparatorMenuItem())

        reset_item = Gtk.MenuItem(label="Reset keyboard drivers")
        reset_item.connect("activate", self._on_reset)
        self._menu.append(reset_item)

        self._append_reload()
        self._append_about()
        self._append_quit()

    def _build_supported_menu(self):
        colour_header = Gtk.MenuItem(label="Colour")
        colour_header.set_sensitive(False)
        self._menu.append(colour_header)

        colour_group = None
        for cname in self._profile.colour_names:
            label = cname.replace("_", " ").title()
            item = Gtk.RadioMenuItem(group=colour_group, label=label)
            if colour_group is None:
                colour_group = item
            if cname == self._current_colour:
                item.set_active(True)
            item.connect("toggled", self._on_colour_changed, cname)
            self._menu.append(item)
            self._colour_items[cname] = item

        self._menu.append(Gtk.SeparatorMenuItem())

        brightness_header = Gtk.MenuItem(label="Brightness")
        brightness_header.set_sensitive(False)
        self._menu.append(brightness_header)

        bright_group = None
        for level, label in enumerate(BRIGHTNESS_NAMES):
            item = Gtk.RadioMenuItem(group=bright_group, label=label)
            if bright_group is None:
                bright_group = item
            if level == self._current_brightness:
                item.set_active(True)
            item.connect("toggled", self._on_brightness_changed, level)
            self._menu.append(item)
            self._brightness_items[level] = item

        self._menu.append(Gtk.SeparatorMenuItem())

        self._startup_item = Gtk.CheckMenuItem(label="Apply on startup")
        self._startup_item.set_active(self._startup_apply)
        self._startup_item.connect("toggled", self._on_startup_toggled)
        self._menu.append(self._startup_item)

        self._menu.append(Gtk.SeparatorMenuItem())

        reset_item = Gtk.MenuItem(label="Reset keyboard drivers")
        reset_item.connect("activate", self._on_reset)
        self._menu.append(reset_item)

        self._append_reload()
        self._append_about()
        self._append_quit()

    def _append_reload(self):
        self._reload_item = Gtk.MenuItem(label="Reload profiles")
        self._reload_item.connect("activate", self._on_reload)
        self._menu.append(self._reload_item)

    def _append_about(self):
        about_item = Gtk.MenuItem(label="About")
        about_item.connect("activate", self._on_about)
        self._menu.append(about_item)

    def _append_quit(self):
        self._menu.append(Gtk.SeparatorMenuItem())
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self._on_quit)
        self._menu.append(quit_item)

    def _apply_colour(self):
        dev = self._get_keyboard()
        if dev is None:
            return
        if self._current_brightness == 0:
            set_off(dev, self._profile)
        else:
            set_static(dev, self._current_colour, self._current_brightness, self._profile)
        self._save_config()

    def _on_colour_changed(self, item, cname):
        if not item.get_active() or self._building:
            return
        self._current_colour = cname
        self._apply_colour()

    def _on_brightness_changed(self, item, level):
        if not item.get_active() or self._building:
            return
        self._current_brightness = level
        self._apply_colour()

    def _on_unsupported_off(self, item):
        if not item.get_active() or self._building:
            return
        dev = self._get_keyboard()
        if dev is not None:
            set_off(dev)

    def _on_startup_toggled(self, item):
        self._startup_apply = item.get_active()
        self._save_config()

    def _on_calibrate(self, *args):
        terminal_cmds = [
            ("gnome-terminal", ["gnome-terminal", "--", "gigabyte-rgb", "--calibrate"]),
            ("konsole", ["konsole", "-e", "gigabyte-rgb", "--calibrate"]),
            ("xfce4-terminal", ["xfce4-terminal", "-e", "gigabyte-rgb", "--calibrate"]),
            ("lxterminal", ["lxterminal", "-e", "gigabyte-rgb", "--calibrate"]),
            ("x-terminal-emulator", ["x-terminal-emulator", "-e", "gigabyte-rgb", "--calibrate"]),
        ]
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        argv = None
        for term, cmd in terminal_cmds:
            if desktop and term in desktop:
                argv = cmd
                break
        if argv is None:
            argv = ["gigabyte-rgb", "--calibrate"]
        try:
            pid, *_ = GLib.spawn_async(
                argv,
                flags=GLib.SpawnFlags.SEARCH_PATH | GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            )
            GLib.child_watch_add(pid, self._on_calibrate_done)
        except GLib.GError:
            self._show_calibrate_fallback()

    def _on_calibrate_done(self, pid, status):
        if status == 0:
            self._on_reload()

    def _show_calibrate_fallback(self):
        dlg = Gtk.MessageDialog(
            transient_for=None,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Calibration launcher",
        )
        dlg.format_secondary_text(
            "Could not open a terminal automatically.\n\n"
            "Please open a terminal and run:\n"
            "  gigabyte-rgb --calibrate\n\n"
            "Then click 'Reload profiles' in the tray menu."
        )
        dlg.run()
        dlg.destroy()

    def _on_reload(self, *args):
        if self._no_keyboard:
            detected = detect_device()
            if detected is None:
                return
            self._no_keyboard = False
            self._detected_vid, self._detected_pid = detected
        if self._unsupported or self._no_keyboard:
            detected = detect_device()
            if detected is not None:
                self._detected_vid, self._detected_pid = detected
        profile = resolve_profile(self._detected_vid, self._detected_pid) \
            if self._detected_vid else resolve_profile()
        if profile is not None:
            self._profile = profile
            self._unsupported = False
            self._no_keyboard = False
            self._current_colour = self._config.get("colour", self._profile.colour_names[0])
            self._rebuild_menu()
            try:
                self._indicator.set_label("", APP_ID)
            except Exception:
                pass
        elif self._unsupported:
            pass
        else:
            self._profile = None
            self._unsupported = True
            self._rebuild_menu()
        self._apply_on_startup()

    def _on_reset(self, *args):
        dev = self._get_keyboard()
        if dev is None:
            return
        for i in [0, 2, 4]:
            try:
                dev.attach_kernel_driver(i)
            except Exception:
                pass

    def _on_about(self, *args):
        if self._profile is not None:
            secondary = (
                f"Version {__import__('gigabyte_keyboard_rgb', fromlist=['']).__version__}\n\n"
                f"Profile: {self._profile.name}\n\n"
                "Controls the keyboard backlight on selected\n"
                "Gigabyte Aero/AORUS laptops.\n\n"
                "MIT License - use at your own risk."
            )
        elif self._unsupported:
            vid = self._detected_vid or 0
            pid = self._detected_pid or 0
            secondary = (
                f"Version {__import__('gigabyte_keyboard_rgb', fromlist=['']).__version__}\n\n"
                f"Your keyboard (VID={vid:04X} PID={pid:04X})\n"
                "isn't in our profile database yet.\n\n"
                "Run Calibrate... to add support."
            )
        else:
            secondary = (
                f"Version {__import__('gigabyte_keyboard_rgb', fromlist=['']).__version__}\n\n"
                "No Gigabyte keyboard detected.\n\n"
                "MIT License - use at your own risk."
            )
        dlg = Gtk.MessageDialog(
            transient_for=None,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Gigabyte Keyboard RGB Control",
        )
        dlg.format_secondary_text(secondary)
        dlg.run()
        dlg.destroy()

    def _on_quit(self, *args):
        self._save_config()
        Gtk.main_quit()

    def _save_config(self):
        self._config["colour"] = self._current_colour
        self._config["brightness"] = self._current_brightness
        self._config["startup_apply"] = self._startup_apply
        save_config(self._config)

    def _apply_on_startup(self):
        if not self._startup_apply:
            return
        if self._unsupported or self._no_keyboard:
            return
        dev = self._get_keyboard()
        if dev is None:
            return
        if self._current_brightness == 0:
            set_off(dev, self._profile)
        else:
            set_static(dev, self._current_colour, self._current_brightness, self._profile)


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    TrayApp()
    try:
        Gtk.main()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
