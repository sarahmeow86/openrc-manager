#!/usr/bin/env python3
"""GTK application wrapper."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

try:
    gi.require_version("Adw", "1")
    from gi.repository import Adw
except ValueError:
    Adw = None

from gi.repository import Gio, Gtk

from .backend.distro_detect import check_openrc_installed
from .window import MainWindow


APP_ID = "org.openrc.manager"


def _about_dialog(parent: Gtk.Window) -> None:
    about = Gtk.AboutDialog()
    about.set_transient_for(parent)
    about.set_modal(True)
    about.set_program_name("OpenRC Service Manager")
    about.set_version("1.0.3")
    about.set_website("https://github.com/sarahmeow86/openrc-manager")
    about.set_license_type(Gtk.License.GPL_3_0)
    about.set_comments("Universal GTK4 GUI for OpenRC service management")
    about.present()


class OpenRCManagerApplication((Adw.Application if Adw else Gtk.Application)):
    """Main application object."""

    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window: MainWindow | None = None
        self._auto_refresh_action: Gio.SimpleAction | None = None
        self.connect("activate", self.on_activate)

    def on_activate(self, _app: Gio.Application) -> None:
        if self.window is None:
            self.window = MainWindow(self)
            self._install_actions()
        self.window.present()

    def _install_actions(self) -> None:
        refresh_action = Gio.SimpleAction.new("refresh", None)
        refresh_action.connect("activate", lambda *_: self.window and self.window.load_services())
        self.add_action(refresh_action)

        auto_action = Gio.SimpleAction.new_stateful(
            "auto_refresh",
            None,
            GLib.Variant.new_boolean(False),
        )
        auto_action.connect("activate", self._toggle_auto_refresh)
        self.add_action(auto_action)
        self._auto_refresh_action = auto_action

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", lambda *_: self.window and _about_dialog(self.window))
        self.add_action(about_action)

    def _toggle_auto_refresh(self, action: Gio.SimpleAction, _param) -> None:
        current = action.get_state().get_boolean()
        new_value = not current
        action.set_state(GLib.Variant.new_boolean(new_value))
        if self.window is not None:
            self.window.auto_refresh = new_value


from gi.repository import GLib  # noqa: E402  # imported after gi.require_version


def run_app() -> int:
    """Run the GTK app and return process exit code."""
    if Adw is not None:
        Adw.init()

    if not check_openrc_installed():
        print("OpenRC tools are not available. Install openrc first.")

    app = OpenRCManagerApplication()
    return app.run(None)
