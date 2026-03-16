#!/usr/bin/env python3
"""Service log viewer window."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

from ..backend.service_manager import Service, ServiceManager


class LogViewerWindow(Gtk.Window):
    """Display recent log lines for a selected service."""

    def __init__(self, parent: Gtk.Window, service: Service, manager: ServiceManager):
        super().__init__(
            title=f"Logs - {service.name}",
            transient_for=parent,
            modal=False,
        )
        self.service = service
        self.manager = manager
        self.lines = 200

        self.set_default_size(900, 560)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_margin_start(10)
        root.set_margin_end(10)
        root.set_margin_top(10)
        root.set_margin_bottom(10)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toolbar.append(Gtk.Label(label=f"Service: {service.name}"))

        self.spin = Gtk.SpinButton.new_with_range(20, 5000, 10)
        self.spin.set_value(self.lines)
        toolbar.append(Gtk.Label(label="Lines"))
        toolbar.append(self.spin)

        refresh = Gtk.Button(label="Refresh", icon_name="view-refresh-symbolic")
        refresh.connect("clicked", lambda *_: self.load_logs())
        toolbar.append(refresh)

        root.append(toolbar)

        self.text_view = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.NONE)
        self.text_buffer = self.text_view.get_buffer()

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_child(self.text_view)
        root.append(scrolled)

        self.status = Gtk.Label(label="Loading logs...")
        self.status.set_xalign(0)
        self.status.add_css_class("dim-label")
        root.append(self.status)

        self.set_child(root)
        self.load_logs()

    def load_logs(self) -> None:
        self.lines = int(self.spin.get_value())
        self.status.set_text("Loading logs...")

        def task() -> None:
            text = self.manager.get_logs(self.service.name, lines=self.lines)
            GLib.idle_add(self._on_logs_loaded, text)

        threading.Thread(target=task, daemon=True).start()

    def _on_logs_loaded(self, text: str) -> bool:
        self.text_buffer.set_text(text)
        self.status.set_text(f"Showing last {self.lines} lines")
        return False
