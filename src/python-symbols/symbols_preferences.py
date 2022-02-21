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
#
import gi  # noqa
from gi.repository import GObject, Gtk, Ide

_ = Ide.gettext


class PythonSymbolsPreferencesAddin(GObject.Object, Ide.PreferencesAddin):
    """PythonSymbolsPreferencesAddin."""

    def do_load(self, prefs):
        """This interface method is called when a preferences
        addin is initialized.
        """
        self._ids = []

        prefs.add_page(
            "python-plugins",
            _("Python Plugins Preferences"),
            10000,
        )

        prefs.add_list_group(
            "python-plugins",
            "python-symbols",
            _("Python symbols:"),
            Gtk.SelectionMode.NONE,
            11000,
        )
        self._ids.append(
            prefs.add_switch(
                "python-plugins",
                "python-symbols",
                "org.gnome.builder.plugins.python-symbols",
                "export-imports",
                None,
                "true",
                _("Export imports as symbols"),
                _("Make imported module visible in the symbol tree view."),
                _("symbols python"),
                10
            )
        )
        self._ids.append(
            prefs.add_switch(
                "python-plugins",
                "python-symbols",
                "org.gnome.builder.plugins.python-symbols",
                "export-modules-variables",
                None,
                "true",
                _("Export module's variables as symbol"),
                _("Make variables declared at module level visible "
                  "in the symbol tree view."),
                _("symbols python"),
                20
            )
        )
        self._ids.append(
            prefs.add_switch(
                "python-plugins",
                "python-symbols",
                "org.gnome.builder.plugins.python-symbols",
                "export-class-variables",
                None,
                "true",
                _("Export class's variables as symbol"),
                _("Make variables declared at class level visible "
                  "in the symbol tree view."),
                _("symbols python"),
                30
            )
        )

    def do_unload(self, preferences):
        """This interface method is called when the preferences addin
        should remove all controls added to preferences. This could
        happen during desctruction of preferences, or when the plugin
        is unloaded.preferences.remove_id(self.python_linter_id)
        """
        for _id in self._ids:
            preferences.remove_id(_id)

