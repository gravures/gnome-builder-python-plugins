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
import threading

import gi  # noqa
from gi.repository import GLib, GObject, Gio
from gi.repository import Ide

import linters
from linters import LinterError, AbstractLinterAdapter
from linters_preferences import PythonLinterPreferencesAddin  # noqa

_ = Ide.gettext


class PythonLinterDiagnosticProvider(Ide.Object, Ide.DiagnosticProvider):
    linter_enabled = GObject.Property(type=bool, default=True)
    _linter_adapter = None

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

        # linter selection
        linter_name = _gsettings.get_string("linter-name")
        _class = linters.get_adapter_class(linter_name)
        if _class:
            self._linter_adapter = _class()

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

    def on_enable_cb(self, _gparamstring, _):
        """Callback when linter_enable property is changed,
        ui should be update to reflect user change in preferences.
        """
        context = self.get_context()
        if context is not None:
            manager = Ide.DiagnosticsManager.from_context(context)
            buf_manager = Ide.BufferManager.from_context(context)
            buf_manager.foreach(
                lambda buffer, manager: manager.rediagnose(buffer),
                manager
            )

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
        launcher.set_run_on_host(True)

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

        if not self.linter_enabled or not self.linter_adapter:
            task.return_boolean(False)
            return

        launcher = self.create_launcher()

        threading.Thread(
            target=self._execute,
            args=(task, launcher, file, file_content),
            name="pylinter-thread",
        ).start()

    def do_diagnose_finish(self, result):
        if result.propagate_boolean():
            diagnostics = Ide.Diagnostics()
            for diag in result.diagnostics_list:
                diagnostics.add(diag)
            return diagnostics
        return None

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

