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
from enum import Enum
from pathlib import Path
import json
import threading

# for raising an ImportError so our plugin wont load
# if pylint is not installed.
import pylint
import gi

from gi.repository import GLib, GObject, Gio
from gi.repository import Ide


_ = Ide.gettext


SEVERITY = {
    'ignored': Ide.DiagnosticSeverity.IGNORED,
    'convention': Ide.DiagnosticSeverity.NOTE,
    'refactor': Ide.DiagnosticSeverity.NOTE,
    'information': Ide.DiagnosticSeverity.NOTE,
    'deprecated': Ide.DiagnosticSeverity.DEPRECATED,
    'warning': Ide.DiagnosticSeverity.WARNING,
    'error': Ide.DiagnosticSeverity.ERROR,
    'fatal': Ide.DiagnosticSeverity.FATAL,
    'unused': Ide.DiagnosticSeverity.NOTE,
}
if Ide.MAJOR_VERSION >= 41:
    SEVERITY['unused'] = Ide.DiagnosticSeverity.UNUSED


UNUSED_CODE = [
    "W0641",
    "W0613",
    "W1304",
    "W1301",
    "W0611",
    "W0238",
    "W0612",
    "W0614",
]

DEPRECATED_CODE = [
    "W1511",
    "W1512",
    "W1513",
    "W1505",
    "W0402",
]


class PythonLinterDiagnosticProvider(Ide.Object, Ide.DiagnosticProvider):
    linter_enabled = GObject.Property(type=bool, default=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

    def on_enable_cb(self, gparamstring, _):
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
            name="pylint-thread",
        ).start()

    def _execute(self, task, launcher, file, file_content):
        try:
            launcher.push_args(
                (
                    "pylint",
                    "--output-format",
                    "json",
                    "--persistent",
                    "n",
                    "-j",
                    "1",
                    "--exit-zero",
                )
            )

            if file_content:
                launcher.push_argv("--from-stdin")
                launcher.push_argv(file.get_path())
            else:
                launcher.push_argv(file.get_path())

            sub_process = launcher.spawn()
            stdin = file_content.get_data().decode("UTF-8")
            success, stdout, _stderr = sub_process.communicate_utf8(stdin, None)

            if not success:
                task.return_boolean(False)
                return

            results = json.loads(stdout)
            for item in results:
                line = item.get("line", None)
                column = item.get("column", None)
                if not line or not column:
                    continue
                start_line = max(item["line"] - 1, 0)
                start_col = max(item["column"], 0)
                start = Ide.Location.new(file, start_line, start_col)

                severity = SEVERITY[item["type"]]
                end = None

                end_line = item.get("endLine", None)
                end_col = item.get("endColumn", None)
                if end_line and end_col:
                    end_line = max(end_line - 1, 0)
                    end_col = max(end_col, 0)
                    if not severity in (
                        Ide.DiagnosticSeverity.ERROR,
                        Ide.DiagnosticSeverity.FATAL,
                    ):
                        # make underlined run on multiple lines
                        # only for hight severity code
                        end_col = (
                            start_col if start_line != end_line else end_col
                        )
                        end_line = start_line
                    end = Ide.Location.new(file, end_line, end_col)

                _symbol = item.get("symbol")
                _message = item.get("message")
                _code = item.get("message-id")

                # Additional sorting
                if severity is SEVERITY['warning']:
                    if _code in UNUSED_CODE:
                        severity = SEVERITY['unused']
                    elif _code in DEPRECATED_CODE:
                        severity = SEVERITY['deprecated']

                diagnostic = Ide.Diagnostic.new(
                    severity,
                    f"{_symbol} ({_code})\n{_message}",
                    start,
                )
                if end is not None:
                    range_ = Ide.Range.new(start, end)
                    diagnostic.add_range(range_)
                    # if 'fix' in message:
                    # Fixes often come without end* information so we
                    # will rarely get here, instead it has a file offset
                    # which is not actually implemented in IdeSourceLocation
                    # fixit = Ide.Fixit.new(range_, message['fix']['text'])
                    # diagnostic.take_fixit(fixit)

                task.diagnostics_list.append(diagnostic)
        except GLib.Error as err:
            task.return_error(err)
        except (json.JSONDecodeError, UnicodeDecodeError, IndexError) as err:
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


# FIXME: meson.build:glib-compile-schemas need to handle flatpack install
class PythonLinterPreferencesAddin(GObject.Object, Ide.PreferencesAddin):
    """PythonLinterPreferencesAddin."""

    def do_load(self, preferences):
        """
        This interface method is called when a preferences addin is initialized.
        It could be initialized from multiple preferences implementations,
        so consumers should use the #DzlPreferences interface to add their
        preferences controls to the container.
        Such implementations might include a preferences dialog window,
        or a preferences widget which could be rendered as a perspective.
        """
        self.python_linter_id = preferences.add_switch(
            # to the code-insight page
            "code-insight",
            # in the diagnostics group
            "diagnostics",
            # mapping to the gsettings schema
            "org.gnome.builder.plugins.python-linter",
            # with the gsettings schema key
            "enable-python-linter",
            # And the gsettings path
            None,
            # The target GVariant value if necessary (usually not)
            "false",
            # title
            "Python Linter",
            # subtitle
            "Enable the use of PyLint, which may execute code in your project",
            # translators: these are keywords used to search for preferences
            "pylint python lint code execute execution",
            # with sort priority
            500)

    def do_unload(self, preferences):
        """This interface method is called when the preferences addin
        should remove all controls added to @preferences. This could
        happen during desctruction of preferences, or when the plugin
        is unloaded.preferences.remove_id(self.python_linter_id)
        """
        preferences.remove_id(self.python_linter_id)

