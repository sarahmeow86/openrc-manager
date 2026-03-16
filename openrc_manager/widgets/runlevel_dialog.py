#!/usr/bin/env python3
"""Runlevel selection dialog."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk


class RunlevelDialog(Gtk.Window):
    """Simple dialog-like transient window to pick a runlevel."""

    def __init__(
        self,
        parent: Gtk.Window,
        title: str,
        runlevels: list[str],
        highlighted: list[str],
        on_selected,
    ):
        super().__init__(title=title, transient_for=parent, modal=True)
        self._on_selected = on_selected
        self.set_default_size(380, 280)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_margin_start(12)
        root.set_margin_end(12)
        root.set_margin_top(12)
        root.set_margin_bottom(12)

        hint = Gtk.Label(label="Choose target runlevel")
        hint.set_xalign(0)
        hint.add_css_class("dim-label")
        root.append(hint)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)

        for item in runlevels:
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row_box.set_margin_start(8)
            row_box.set_margin_end(8)
            row_box.set_margin_top(6)
            row_box.set_margin_bottom(6)

            label = Gtk.Label(label=item)
            label.set_xalign(0)
            label.set_hexpand(True)
            row_box.append(label)

            if item in highlighted:
                badge = Gtk.Label(label="enabled")
                badge.add_css_class("dim-label")
                row_box.append(badge)

            row = Gtk.ListBoxRow()
            row.set_child(row_box)
            row.set_activatable(True)
            list_box.append(row)

        scrolled.set_child(list_box)
        root.append(scrolled)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cancel = Gtk.Button(label="Cancel")
        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("suggested-action")
        buttons.append(cancel)
        buttons.append(apply_btn)
        root.append(buttons)

        self._selected = None

        def on_row_selected(_box, row):
            if row is None:
                self._selected = None
                return
            idx = row.get_index()
            if 0 <= idx < len(runlevels):
                self._selected = runlevels[idx]

        list_box.connect("row-selected", on_row_selected)
        list_box.connect("row-activated", lambda _b, _r: self._accept())

        cancel.connect("clicked", lambda *_: self.close())
        apply_btn.connect("clicked", lambda *_: self._accept())

        self.set_child(root)

    def _accept(self) -> None:
        if self._selected:
            self._on_selected(self._selected)
            self.close()
