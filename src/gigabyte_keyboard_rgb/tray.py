import sys
import signal

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
from gi.repository import Gtk, GLib, AppIndicator3

from .protocol import (
    COLOURS, get_keyboard, set_static, set_off, VID, PID, INTERFACE,
)
from .config import load as load_config, save as save_config

APP_ID = "gigabyte-keyboard-rgb"
COLOUR_LIST = list(COLOURS.keys())
BRIGHTNESS_NAMES = ["Off", "Dim", "Full"]


class TrayApp:
    def __init__(self):
        self._config = load_config()
        self._indicator = None
        self._menu = None
        self._colour_items = {}
        self._brightness_items = {}
        self._startup_item = None
        self._no_keyboard = False
        self._building = True

        self._current_colour = self._config.get("colour", "light_purple")
        self._current_brightness = self._config.get("brightness", 2)
        self._startup_apply = self._config.get("startup_apply", True)

        self._build_menu()
        self._building = False
        self._apply_on_startup()

    def _get_keyboard(self):
        dev = get_keyboard()
        if dev is None:
            self._show_no_keyboard()
            return None
        return dev

    def _show_no_keyboard(self):
        if not self._no_keyboard:
            self._no_keyboard = True
            self._indicator.set_label("No keyboard", APP_ID)
        GLib.timeout_add(10000, self._retry_keyboard)

    def _retry_keyboard(self):
        dev = get_keyboard()
        if dev is not None:
            self._no_keyboard = False
            self._indicator.set_label("", APP_ID)
            self._apply_colour()
        return False

    def _build_menu(self):
        self._menu = Gtk.Menu()

        colour_header = Gtk.MenuItem(label="Colour")
        colour_header.set_sensitive(False)
        self._menu.append(colour_header)

        colour_group = None
        for cname in COLOUR_LIST:
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

        reset_item = Gtk.MenuItem(label="Reset keyboard drivers")
        reset_item.connect("activate", self._on_reset)
        self._menu.append(reset_item)

        about_item = Gtk.MenuItem(label="About")
        about_item.connect("activate", self._on_about)
        self._menu.append(about_item)

        self._menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self._on_quit)
        self._menu.append(quit_item)

        self._menu.show_all()

        self._indicator = AppIndicator3.Indicator.new(
            APP_ID,
            "gigabyte-keyboard-rgb",
            AppIndicator3.IndicatorCategory.HARDWARE,
        )
        self._indicator.set_menu(self._menu)
        self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

    def _apply_colour(self):
        dev = self._get_keyboard()
        if dev is None:
            return
        if self._current_brightness == 0:
            set_off(dev)
        else:
            set_static(dev, self._current_colour, self._current_brightness)
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

    def _on_startup_toggled(self, item):
        self._startup_apply = item.get_active()
        self._save_config()

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
        dlg = Gtk.MessageDialog(
            transient_for=None,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Gigabyte Keyboard RGB Control",
        )
        dlg.format_secondary_text(
            f"Version {__import__('gigabyte_keyboard_rgb', fromlist=['']).__version__}\n\n"
            "Controls the keyboard backlight on selected\n"
            "Gigabyte Aero/AORUS laptops.\n\n"
            "MIT License - use at your own risk."
        )
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
        dev = get_keyboard()
        if dev is None:
            return
        if self._current_brightness == 0:
            set_off(dev)
        else:
            set_static(dev, self._current_colour, self._current_brightness)


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    TrayApp()
    try:
        Gtk.main()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
