#!/usr/bin/env python3
"""Main application window."""

from __future__ import annotations

import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
try:
    gi.require_version("Adw", "1")
    from gi.repository import Adw
except ValueError:
    Adw = None

from gi.repository import Gio, GLib, Gtk

from .backend.distro_detect import detect_distro
from .backend.service_manager import Service, ServiceManager
from .widgets.details_dialog import ServiceDetailsDialog
from .widgets.log_viewer import LogViewerWindow
from .widgets.runlevel_dialog import RunlevelDialog
from .widgets.service_row import ServiceRow


BaseWindow = Adw.ApplicationWindow if Adw else Gtk.ApplicationWindow
CRITICAL_SERVICES = {"dbus", "elogind", "udev", "syslog", "networking"}


class MainWindow(BaseWindow):
    """Primary window with service list and service actions."""

    def __init__(self, app: Gtk.Application):
        super().__init__(application=app)
        self.distro = detect_distro()
        self.manager = ServiceManager(self.distro)

        self.services: list[Service] = []
        self.filtered_services: list[Service] = []
        self.selected_service: Service | None = None
        self.auto_refresh = False
        self.refresh_interval_ms = 5000

        self.set_title(f"OpenRC Service Manager - {self.distro.pretty_name}")
        self.set_default_size(1024, 700)

        self.search_entry: Gtk.SearchEntry
        self.status_filter: Gtk.DropDown
        self.runlevel_filter: Gtk.DropDown
        self.list_box: Gtk.ListBox
        self.status_label: Gtk.Label

        self.start_button: Gtk.Button
        self.stop_button: Gtk.Button
        self.restart_button: Gtk.Button
        self.enable_button: Gtk.Button
        self.disable_button: Gtk.Button
        self.logs_button: Gtk.Button
        self.details_button: Gtk.Button

        self._build_ui()
        GLib.idle_add(self.load_services)
        self._start_auto_refresh()

    def _build_ui(self) -> None:
        if Adw:
            header = Adw.HeaderBar()
        else:
            header = Gtk.HeaderBar()

        refresh_button = Gtk.Button()
        refresh_button.set_icon_name("view-refresh-symbolic")
        refresh_button.set_tooltip_text("Refresh service list")
        refresh_button.connect("clicked", lambda *_: self.load_services())
        header.pack_start(refresh_button)

        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(self._create_menu())
        header.pack_end(menu_button)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_margin_start(8)
        root.set_margin_end(8)
        root.set_margin_top(8)
        root.set_margin_bottom(8)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search services")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        toolbar.append(self.search_entry)

        status_model = Gtk.StringList.new(["All", "Running", "Stopped", "Enabled", "Disabled"])
        self.status_filter = Gtk.DropDown(model=status_model)
        self.status_filter.connect("notify::selected", self.on_filter_changed)
        toolbar.append(self.status_filter)

        runlevels = ["All Runlevels"] + self.manager.get_available_runlevels()
        self.runlevel_filter = Gtk.DropDown(model=Gtk.StringList.new(runlevels))
        self.runlevel_filter.connect("notify::selected", self.on_filter_changed)
        toolbar.append(self.runlevel_filter)

        root.append(toolbar)

        columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        columns.add_css_class("header-row")
        for title, width in [
            ("", 30),
            ("Service", 220),
            ("Status", 120),
            ("Runlevels", 180),
            ("Dependencies", 240),
        ]:
            label = Gtk.Label(label=title)
            label.set_xalign(0)
            label.set_size_request(width, -1)
            label.add_css_class("dim-label")
            columns.append(label)
        root.append(columns)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.list_box = Gtk.ListBox()
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.set_activate_on_single_click(False)
        self.list_box.connect("row-selected", self.on_service_selected)
        self.list_box.connect("row-activated", self.on_service_activated)
        scrolled.set_child(self.list_box)
        root.append(scrolled)

        action_bar = Gtk.ActionBar()
        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_xalign(0)
        action_bar.pack_start(self.status_label)

        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.start_button = Gtk.Button(label="Start")
        self.start_button.set_icon_name("media-playback-start-symbolic")
        self.stop_button = Gtk.Button(label="Stop")
        self.stop_button.set_icon_name("media-playback-stop-symbolic")
        self.restart_button = Gtk.Button(label="Restart")
        self.restart_button.set_icon_name("view-refresh-symbolic")
        self.enable_button = Gtk.Button(label="Enable")
        self.disable_button = Gtk.Button(label="Disable")
        self.logs_button = Gtk.Button(label="Logs")
        self.logs_button.set_icon_name("utilities-terminal-symbolic")
        self.details_button = Gtk.Button(label="Details")
        self.details_button.set_icon_name("dialog-information-symbolic")

        self.start_button.connect("clicked", self.on_start_clicked)
        self.stop_button.connect("clicked", self.on_stop_clicked)
        self.restart_button.connect("clicked", self.on_restart_clicked)
        self.enable_button.connect("clicked", self.on_enable_clicked)
        self.disable_button.connect("clicked", self.on_disable_clicked)
        self.logs_button.connect("clicked", self.on_logs_clicked)
        self.details_button.connect("clicked", self.on_details_clicked)

        for button in [
            self.start_button,
            self.stop_button,
            self.restart_button,
            self.enable_button,
            self.disable_button,
            self.logs_button,
            self.details_button,
        ]:
            actions_box.append(button)

        action_bar.pack_end(actions_box)
        root.append(action_bar)

        self._set_buttons_sensitive(False)

        if Adw:
            toolbar_view = Adw.ToolbarView()
            toolbar_view.add_top_bar(header)
            toolbar_view.set_content(root)
            self.set_content(toolbar_view)
        else:
            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            outer.append(header)
            outer.append(root)
            self.set_child(outer)

        self._load_css()

    def _create_menu(self) -> Gio.Menu:
        menu = Gio.Menu()
        menu.append("Refresh", "app.refresh")
        menu.append("Auto-refresh", "app.auto_refresh")
        about_section = Gio.Menu()
        about_section.append("About", "app.about")
        menu.append_section(None, about_section)
        return menu

    def _load_css(self) -> None:
        css_path = Path(__file__).resolve().parent / "data" / "style.css"
        css = """
        .header-row {
            padding: 6px;
            border-radius: 8px;
            background-color: alpha(@theme_fg_color, 0.06);
        }
        .service-running { color: @success_color; }
        .service-stopped { color: @warning_color; }
        .service-crashed { color: @error_color; }
        """
        if css_path.exists():
            try:
                css = css_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def load_services(self) -> None:
        self.status_label.set_text("Loading services...")

        def task() -> None:
            services = self.manager.get_all_services()
            GLib.idle_add(self.on_services_loaded, services)

        threading.Thread(target=task, daemon=True).start()

    def on_services_loaded(self, services: list[Service]) -> bool:
        self.services = services
        self.apply_filters()
        running = sum(1 for item in services if item.status == "running")
        self.status_label.set_text(
            f"{len(services)} services ({running} running) - {self.distro.name}"
        )
        return False

    def apply_filters(self) -> None:
        search_text = self.search_entry.get_text().lower().strip()
        status_index = self.status_filter.get_selected()
        runlevel_index = self.runlevel_filter.get_selected()
        all_runlevels = self.manager.get_available_runlevels()

        self.filtered_services = []
        for service in self.services:
            if search_text and search_text not in service.name.lower() and search_text not in service.description.lower():
                continue

            if status_index == 1 and service.status != "running":
                continue
            if status_index == 2 and service.status != "stopped":
                continue
            if status_index == 3 and not service.enabled:
                continue
            if status_index == 4 and service.enabled:
                continue

            if runlevel_index > 0:
                target = all_runlevels[runlevel_index - 1]
                if target not in service.runlevels:
                    continue

            self.filtered_services.append(service)

        self._populate_list()

    def _populate_list(self) -> None:
        while True:
            row = self.list_box.get_row_at_index(0)
            if row is None:
                break
            self.list_box.remove(row)

        for service in self.filtered_services:
            self.list_box.append(ServiceRow(service))

    def on_search_changed(self, _entry: Gtk.SearchEntry) -> None:
        self.apply_filters()

    def on_filter_changed(self, _widget, _param) -> None:
        self.apply_filters()

    def on_service_selected(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if row is None:
            self.selected_service = None
            self._set_buttons_sensitive(False)
            return

        idx = row.get_index()
        if idx < 0 or idx >= len(self.filtered_services):
            self.selected_service = None
            self._set_buttons_sensitive(False)
            return

        self.selected_service = self.filtered_services[idx]
        self._set_buttons_sensitive(True)
        self._update_button_states()

    def on_service_activated(self, _listbox: Gtk.ListBox, _row: Gtk.ListBoxRow) -> None:
        self.on_details_clicked(None)

    def _set_buttons_sensitive(self, enabled: bool) -> None:
        for button in [
            self.start_button,
            self.stop_button,
            self.restart_button,
            self.enable_button,
            self.disable_button,
            self.logs_button,
            self.details_button,
        ]:
            button.set_sensitive(enabled)

    def _update_button_states(self) -> None:
        if self.selected_service is None:
            return

        running = self.selected_service.status == "running"
        enabled = self.selected_service.enabled

        self.start_button.set_sensitive(not running)
        self.stop_button.set_sensitive(running)
        self.restart_button.set_sensitive(True)
        self.enable_button.set_sensitive(not enabled)
        self.disable_button.set_sensitive(enabled and bool(self.selected_service.runlevels))

    def _run_service_operation(self, operation: str, callback) -> None:
        if self.selected_service is None:
            return
        service_name = self.selected_service.name

        self._set_buttons_sensitive(False)
        self.status_label.set_text(f"{operation.capitalize()}ing {service_name}...")

        def task() -> None:
            success, message = callback(service_name)
            GLib.idle_add(self._on_operation_complete, operation, success, message)

        threading.Thread(target=task, daemon=True).start()

    def _on_operation_complete(self, operation: str, success: bool, message: str) -> bool:
        if success:
            self.status_label.set_text(f"{operation.capitalize()} successful")
        else:
            self._show_message(f"{operation.capitalize()} Failed", message, error=True)
            self.status_label.set_text(f"{operation.capitalize()} failed")
        self.load_services()
        return False

    def _show_message(self, title: str, body: str, error: bool = False, callback=None) -> None:
        if Adw:
            dialog = Adw.MessageDialog.new(self)
            dialog.set_heading(title)
            dialog.set_body(body)
            dialog.add_response("ok", "OK")
            if callback:
                dialog.add_response("continue", "Continue")
                dialog.set_default_response("ok")
                if error:
                    dialog.set_response_appearance("continue", Adw.ResponseAppearance.DESTRUCTIVE)
                dialog.connect("response", lambda _d, r: callback() if r == "continue" else None)
            dialog.present()
            return

        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            text=title,
            secondary_text=body,
            buttons=Gtk.ButtonsType.OK,
            message_type=Gtk.MessageType.ERROR if error else Gtk.MessageType.INFO,
        )
        dialog.connect("response", lambda d, _r: d.destroy())
        dialog.present()

    def on_start_clicked(self, _button: Gtk.Button | None) -> None:
        self._run_service_operation("start", self.manager.start_service)

    def on_stop_clicked(self, _button: Gtk.Button | None) -> None:
        if self.selected_service is None:
            return
        if self.selected_service.name in CRITICAL_SERVICES:
            self._show_message(
                f"Stop {self.selected_service.name}?",
                f"Stopping {self.selected_service.name} may cause system instability.",
                error=True,
                callback=lambda: self._run_service_operation("stop", self.manager.stop_service),
            )
            return
        self._run_service_operation("stop", self.manager.stop_service)

    def on_restart_clicked(self, _button: Gtk.Button | None) -> None:
        self._run_service_operation("restart", self.manager.restart_service)

    def on_enable_clicked(self, _button: Gtk.Button | None) -> None:
        if self.selected_service is None:
            return
        dialog = RunlevelDialog(
            self,
            "Enable Service",
            self.manager.get_available_runlevels(),
            self.selected_service.runlevels,
            self._on_enable_runlevel_selected,
        )
        dialog.present()

    def _on_enable_runlevel_selected(self, runlevel: str) -> None:
        self._run_service_operation(
            "enable",
            lambda name: self.manager.enable_service(name, runlevel),
        )

    def on_disable_clicked(self, _button: Gtk.Button | None) -> None:
        if self.selected_service is None:
            return
        if not self.selected_service.runlevels:
            self._show_message("Disable Service", "Service is not enabled in any runlevel.")
            return
        dialog = RunlevelDialog(
            self,
            "Disable Service",
            self.selected_service.runlevels,
            [],
            self._on_disable_runlevel_selected,
        )
        dialog.present()

    def _on_disable_runlevel_selected(self, runlevel: str) -> None:
        self._run_service_operation(
            "disable",
            lambda name: self.manager.disable_service(name, runlevel),
        )

    def on_logs_clicked(self, _button: Gtk.Button | None) -> None:
        if self.selected_service is None:
            return
        win = LogViewerWindow(self, self.selected_service, self.manager)
        win.present()

    def on_details_clicked(self, _button: Gtk.Button | None) -> None:
        if self.selected_service is None:
            return
        dialog = ServiceDetailsDialog(self, self.selected_service, self.manager)
        dialog.present()

    def _start_auto_refresh(self) -> None:
        def tick() -> bool:
            if self.auto_refresh:
                self.load_services()
            return True

        GLib.timeout_add(self.refresh_interval_ms, tick)
