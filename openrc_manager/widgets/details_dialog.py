#!/usr/bin/env python3
"""Service details dialog."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

from ..backend.service_manager import Service, ServiceManager


class ServiceDetailsDialog(Gtk.Window):
    """Window that displays service metadata and dependencies."""

    def __init__(self, parent: Gtk.Window, service: Service, manager: ServiceManager):
        super().__init__(
            title=f"Service Details - {service.name}",
            transient_for=parent,
            modal=True,
        )
        self.service = service
        self.manager = manager

        self.set_default_size(620, 480)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_margin_start(12)
        root.set_margin_end(12)
        root.set_margin_top(12)
        root.set_margin_bottom(12)

        head = Gtk.Label(label=f"<b>{GLib.markup_escape_text(service.name)}</b>")
        head.set_use_markup(True)
        head.set_xalign(0)
        root.append(head)

        summary = Gtk.Label(
            label=f"Status: {service.status}  |  Enabled: {'yes' if service.enabled else 'no'}"
        )
        summary.set_xalign(0)
        summary.add_css_class("dim-label")
        root.append(summary)

        stack_switcher = Gtk.StackSwitcher()
        stack = Gtk.Stack()
        stack.set_vexpand(True)
        stack_switcher.set_stack(stack)
        root.append(stack_switcher)

        details_view = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        details_buf = details_view.get_buffer()
        details_buf.set_text(self._format_details())
        details_scroll = Gtk.ScrolledWindow()
        details_scroll.set_child(details_view)
        stack.add_titled(details_scroll, "details", "Details")

        config_view = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.NONE)
        config_buf = config_view.get_buffer()
        config = manager.get_service_config(service.name)
        config_buf.set_text(config if config else "No /etc/conf.d override found for this service.")
        config_scroll = Gtk.ScrolledWindow()
        config_scroll.set_child(config_view)
        stack.add_titled(config_scroll, "config", "Config")

        root.append(stack)

        close_btn = Gtk.Button(label="Close")
        close_btn.connect("clicked", lambda *_: self.close())
        root.append(close_btn)

        self.set_child(root)

    def _format_details(self) -> str:
        dep_lines: list[str] = []
        for key in ["need", "use", "want", "before", "after", "provide", "keyword"]:
            vals = self.service.dependencies.get(key, [])
            if vals:
                dep_lines.append(f"{key}: {' '.join(vals)}")

        return "\n".join(
            [
                f"Name: {self.service.name}",
                f"Description: {self.service.description or self.service.name}",
                f"Status: {self.service.status}",
                f"PID: {self.service.pid if self.service.pid else 'n/a'}",
                f"Script: {self.service.script_path}",
                f"Runlevels: {', '.join(self.service.runlevels) if self.service.runlevels else '-'}",
                "",
                "Dependencies:",
                *(dep_lines if dep_lines else ["(none detected)"]),
            ]
        )
