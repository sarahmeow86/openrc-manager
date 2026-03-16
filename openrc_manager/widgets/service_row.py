#!/usr/bin/env python3
"""Service row widget."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, Pango

from ..backend.service_manager import Service


class ServiceRow(Gtk.ListBoxRow):
    """Render one service row in the list box."""

    def __init__(self, service: Service):
        super().__init__()
        self.service = service

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        if service.status == "running":
            icon_name = "emblem-ok-symbolic"
            css_class = "service-running"
        elif service.status == "crashed":
            icon_name = "dialog-error-symbolic"
            css_class = "service-crashed"
        else:
            icon_name = "media-playback-stop-symbolic"
            css_class = "service-stopped"

        status_icon = Gtk.Image.new_from_icon_name(icon_name)
        status_icon.set_size_request(30, -1)
        status_icon.add_css_class(css_class)
        box.append(status_icon)

        name_label = Gtk.Label(label=service.name)
        name_label.set_xalign(0)
        name_label.set_size_request(220, -1)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        box.append(name_label)

        status_label = Gtk.Label(label=service.status.capitalize())
        status_label.set_xalign(0)
        status_label.set_size_request(120, -1)
        status_label.add_css_class(css_class)
        box.append(status_label)

        runlevels_text = ", ".join(service.runlevels) if service.runlevels else "-"
        runlevels_label = Gtk.Label(label=runlevels_text)
        runlevels_label.set_xalign(0)
        runlevels_label.set_size_request(180, -1)
        runlevels_label.set_ellipsize(Pango.EllipsizeMode.END)
        box.append(runlevels_label)

        deps = service.dependencies.get("need", []) + service.dependencies.get("use", [])
        dep_text = ", ".join(deps[:3]) if deps else "-"
        if len(deps) > 3:
            dep_text += "..."
        deps_label = Gtk.Label(label=dep_text)
        deps_label.set_xalign(0)
        deps_label.set_hexpand(True)
        deps_label.set_ellipsize(Pango.EllipsizeMode.END)
        deps_label.add_css_class("dim-label")
        box.append(deps_label)

        self.set_child(box)
