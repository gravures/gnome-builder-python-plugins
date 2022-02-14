#!/usr/bin/env python3
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
import os
import json
import threading

import gi

from gi.repository import GLib, GObject, Gio
from gi.repository import Ide

from linters import PyLintAdapter, LinterError, AbstractLinterAdapter
from preferences import PythonLinterPreferencesAddin


_ = Ide.gettext


class PythonLinterDiagnosticProvider(Ide.Object, Ide.DiagnosticProvider):
    linter_enabled = GObject.Property(type=bool, default=True)
    _linter_adapter = None

    @GObject.property
    def linter_adapter(self):
        return self._linter_adapter

    @linter_adapter.setter
    def linter_adapter(self, value):
        if not isinstance(value, AbstractLinterAdapter):
            raise TypeError(
                "property should be a subclass of AbstractLinterAdapter"
            )
        self._linter_adapter = value

    def __init__(self):
        super().__init__()
        _gsettings = Gio.Settings(
            schema="org.gnome.builder.plugins.python-linter"
        )
        _gsettings.bind(
            "enable-python-linter",
            self,
            "linter_enabled",
            Gio.SettingsBindFlags.DEFAULT,
        )
        self.connect("notify::linter-enabled", self.on_enable_cb)
        self._linter_adapter = PyLintAdapter()

    def on_enable_cb(self, _gparamstring, _):
        """Callback when linter_enable property is changed,
        ui should be update to reflect user change in preferences.
        """
        context = self.get_context()
        if not context is None:
            manager = Ide.DiagnosticsManager.from_context(context)
            # FIXME: ui is not updated
            manager.emit("changed")

    def create_launcher(self):
        """create the subprocess launcher."""
        context = self.get_context()
        srcdir = context.ref_workdir().get_path()
        launcher = None

        if context.has_project():
            build_manager = Ide.BuildManager.from_context(context)
            pipeline = build_manager.get_pipeline()
            if pipeline is not None:
                srcdir = pipeline.get_srcdir()
            runtime = pipeline.get_config().get_runtime()
            launcher = runtime.create_launcher()

        if launcher is None:
            launcher = Ide.SubprocessLauncher.new(0)

        launcher.set_flags(
            Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_PIPE
        )

        # Propagate linter env variables
        config_manager = Ide.ConfigManager.from_context(context)
        config = config_manager.get_current()
        environ = self.linter_adapter.get_environ(config)
        for k, v in environ.items():
            launcher.setenv(k, v, True)

        launcher.set_cwd(srcdir)
        return launcher

    def do_diagnose_async(
        self, file, file_content, lang_id, cancellable, callback, user_data
    ):
        self.diagnostics_list = []
        task = Gio.Task.new(self, cancellable, callback)
        task.diagnostics_list = []

        if not self.linter_enabled:
            task.return_boolean(False)
            return

        launcher = self.create_launcher()

        # FIXME: Do we reaally need this Thread
        # see: https://gitlab.gnome.org/GNOME/gnome-builder/-/issues/365
        # src/plugins/eslint/eslint_plugin.py has an example, but I don't
        # really like how it's doing things. It's using native threading
        # in Python, which we should avoid. Just do things in a subprocess
        # using Ide.SubprocessLauncher and call wait_async() on the subprocess,
        # completing the task in the callback. (Or communicate_utf8_async()
        # if you need the output).
        #
        threading.Thread(
            target=self._execute,
            args=(task, launcher, file, file_content),
            name="pylinter-thread",
        ).start()

    def _execute(self, task, launcher, file, file_content):
        try:
            stdin = file_content.get_data().decode("UTF-8")
            self.linter_adapter.set_file(file, stdin)
            launcher.push_args(self.linter_adapter.get_args())
            sub_process = launcher.spawn()
            success, stdout, _stderr = sub_process.communicate_utf8(stdin, None)

            if not success:
                task.return_boolean(False)
                return

            for diagnostic in self.linter_adapter.diagnostics(stdout):
                task.diagnostics_list.append(diagnostic)
        except GLib.Error as err:
            task.return_error(err)
        except (LinterError, UnicodeDecodeError, IndexError) as err:
            task.return_error(
                GLib.Error(f"Failed to decode pylint json: {err}")
            )
        else:
            task.return_boolean(True)

    def do_diagnose_finish(self, result):
        if result.propagate_boolean():
            diagnostics = Ide.Diagnostics()
            for diag in result.diagnostics_list:
                diagnostics.add(diag)
            return diagnostics
        return None


