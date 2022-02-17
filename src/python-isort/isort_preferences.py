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


class PythonIsortPreferencesAddin(GObject.Object, Ide.PreferencesAddin):
    """PythonIsortPreferencesAddin."""

    def do_load(self, prefs):
        """This interface method is called when a preferences
        addin is initialized.
        """
        self._ids = []

        prefs.add_list_group(
            "code-insight",
            "python-isort",
            _("Python Isort:"),
            Gtk.SelectionMode.NONE,
            11000,
        )
        self._ids.append(
            prefs.add_switch(
                "code-insight",
                "python-isort",
                "org.gnome.builder.plugins.python-isort",
                "black-support",
                None,
                "true",
                "Enable Black compatibility",
                ("Enable isort profile compatibility with python Black "
                 "when formatting your code."),
                _("Black isort python"),
                10
            )
        )
        self._ids.append(
            prefs.add_switch(
                "code-insight",
                "python-isort",
                "org.gnome.builder.plugins.python-isort",
                "pyversion-auto",
                None,
                "true",
                "Enable auto python version discovery",
                ("Format your code accordingly to the version of the "
                 "interpreter used to run isort."),
                _("isort python"),
                20
            )
        )
        self._ids.append(
            prefs.add_switch(
                "code-insight",
                "python-isort",
                "org.gnome.builder.plugins.python-isort",
                "virtual-env",
                None,
                "false",
                "Enable isort to use VIRTUAL_ENV project variable",
                ("If you have set a VIRTUAL_ENV environment variable in your "
                 "project configuration, ask isort to use it for determining "
                 "whether a package is third-party."),
                _("isort python virtual_env"),
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

