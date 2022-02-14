# -*- coding: utf-8 -*-
#
#       Copyright (c) Gilles Coissac 2022 <info@gillescoissac.fr>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 3 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
#
# pylint: disable=unused-argument
# pylint: disable=too-many-arguments, attribute-defined-outside-init
# pylint: disable=too-many-locals, no-self-use
#
from pathlib import Path
import gi

from gi.repository import GLib, GObject, Gio
from gi.repository import Gtk, Dazzle
from gi.repository import Ide


UI = str(Path(__file__).parent / "preferences_entry.ui")

@Gtk.Template(filename=UI)
class PreferencesEntry(Dazzle.PreferencesBin):
    """A custom Dazzle Entry widget."""

    __gtype_name__ = "__preferences_entry__"

    title = GObject.Property(type=str, default="")
    subtitle = GObject.Property(type=str, default="")
    _key = ""
    @GObject.Property(type=str)
    def key(self):
        return self._key

    @key.setter
    def key(self, value):
        self._key = value

    title_label = Gtk.Template.Child()
    subtitle_label = Gtk.Template.Child()
    entry = Gtk.Template.Child()


    def __new__(
        cls, schema_id, key, path, title, subtitle, priority
    ):
        instance = super().__new__(cls)
        instance._key = key
        return instance

    def __init__(
        self, schema_id, key, path, title, subtitle, priority
    ):
        super().__init__(
            schema_id=schema_id,
            path=path,
            priority=priority,
            keywords="",
        )
        self.init_template()
        self.bind_property(
            "title", self.title_label, "label", GObject.BindingFlags.DEFAULT
        )
        self.bind_property(
            "subtitle", self.subtitle_label, "label", GObject.BindingFlags.DEFAULT
        )
        self.props.title = title
        self.props.subtitle = subtitle

    def do_connect(self, gsettings):
        value = gsettings.get_string(self.key)
        self.entry.set_text(value)

    def do_disconnect(self, gsettings):
        gsettings.set_string(self.key, self.entry.get_text())

    def do_matches(self, spec):
        print(f"do_matches: {spec}")
