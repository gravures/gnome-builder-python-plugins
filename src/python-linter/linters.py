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
import json
from abc import ABC, abstractmethod

import gi  # noqa
from gi.repository import Gio, GLib, Ide


class LinterError(Exception):
    """Exception raised by LinterAdapter."""
    def __init__(self, message):
        self.message = message
        super().__init__(message)


VERSION_HOOK = """import @LINTER@

print(@LINTER@.__version__)
"""


class AbstractLinterAdapter(ABC):
    linter = None

    def __init__(self):
        self.file = None
        self.file_content = None

    @classmethod
    def get_name(cls):
        return cls.linter if cls.linter else ""

    @classmethod
    def get_version(cls):
        if cls.linter is None:
            return None
        try:
            launcher = Ide.SubprocessLauncher()
            launcher.set_flags(
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDIN_PIPE
            )
            launcher.set_run_on_host(True)
            launcher.push_args(['python', '-'])
            subprocess = launcher.spawn()
            stdin = VERSION_HOOK.replace("@LINTER@", cls.get_name(), 2)
            success, stdout, stderr = subprocess.communicate_utf8(stdin, None)
            if not success:
                print(f"DEBUG: {stderr} {stdout} ret({success})")
                return None
            return stdout
        except GLib.Error:
            return None

    @staticmethod
    def _diagnostic(
        file, start_line, start_col, end_line, end_col,
        severity, symbol, _id, message,
    ):
        """Return an Ide.Diagnostic."""

        start = Ide.Location.new(file, start_line, start_col)
        end = Ide.Location.new(file, end_line, end_col)
        diagnostic_ = Ide.Diagnostic.new(
            severity,
            f"{symbol} ({_id})\n{message}",
            start,
        )
        range_ = Ide.Range.new(start, end)
        diagnostic_.add_range(range_)
        return diagnostic_

    def set_file(self, file, file_content):
        if not isinstance(file, Gio.File):
            raise LinterError(
                f"file should be an instance of Gio.File, got {file.__class__}"
            )
        self.file = file
        self.file_content = file_content

    def find_end_col(self, line, start, eol=False):
        if self.file_content:
            _line = self.file_content.splitlines()[line]
            end = -1 if eol else _line.find(" ", start)
            return len(_line) if end == -1 else end
        return start

    @abstractmethod
    def get_args(self):
        pass

    @abstractmethod
    def get_environ(self, config):
        pass

    @abstractmethod
    def diagnostics(self, stdout):
        pass


class Flake8Adapter(AbstractLinterAdapter):

    SEVERITY = {
        'ignored': Ide.DiagnosticSeverity.IGNORED,
        'convention': Ide.DiagnosticSeverity.NOTE,
        'refactor': Ide.DiagnosticSeverity.NOTE,
        'information': Ide.DiagnosticSeverity.NOTE,
        'D': Ide.DiagnosticSeverity.DEPRECATED,  # plugin deprecated
        'W': Ide.DiagnosticSeverity.WARNING,
        'E': Ide.DiagnosticSeverity.ERROR,  # pyCodeStyle errors
        'F': Ide.DiagnosticSeverity.FATAL,  # PyFlakes errors
        'C': Ide.DiagnosticSeverity.WARNING,  # McCabe complexity
        'B': Ide.DiagnosticSeverity.WARNING,  # bugBear plugin
        'A': Ide.DiagnosticSeverity.WARNING,  # builtins plugin
        'R': Ide.DiagnosticSeverity.WARNING,  # return plugin
        'I': Ide.DiagnosticSeverity.NOTE,  # isort plugin
        'T': Ide.DiagnosticSeverity.NOTE,  # fixme plugin
        'DC': Ide.DiagnosticSeverity.NOTE,  # docstring-checker plugin
        'CLST': Ide.DiagnosticSeverity.ERROR,  # classmethod-staticmethod plugin
        'CCE': Ide.DiagnosticSeverity.ERROR,  # function-order plugin
        'unused': (Ide.DiagnosticSeverity.UNUSED if Ide.MAJOR_VERSION >= 41 else
                   Ide.DiagnosticSeverity.NOTE),
    }

    UNUSED_CODE = [
        "F401",
        "F504",
        "F522",
        "F523",
        "F811",
        "F841",
    ]

    linter = "flake8"

    def get_environ(self, config):
        return {}

    def get_args(self):
        gsetttings = Gio.Settings.new_with_path(
            "org.gnome.builder.editor.language",
            "/org/gnome/builder/editor/language/python3/"
        )
        max_line_length = str(gsetttings.get_int("right-margin-position"))
        indent_size = str(gsetttings.get_int("tab-width"))
        _format = "%(row)d|%(col)d|%(code)s|%(text)s"
        args = ["python", '-m',
                Flake8Adapter.linter,
                "--no-show-source",
                "--format", _format,
                "--max-line-length", max_line_length,
                "--indent-size", indent_size,
                "-j", "auto",
                "--exit-zero"]

        if self.file_content:
            args += ["--stdin-display-name",
                     self.file.get_path(),
                     "-"]
        else:
            args += [self.file.get_path()]
        return tuple(args)

    def diagnostics(self, stdout):
        warnings = stdout.splitlines()
        for _warn in warnings:
            elmnts = _warn.split("|")
            if len(elmnts) < 4:
                continue
            _id = elmnts[2]
            _key = _id.strip("0123456789")
            eol = _key == "I"  # for isort plugin
            end_line = start_line = max(int(elmnts[0]) - 1, 0)
            start_col = max(int(elmnts[1]) - 1, 0)
            end_col = self.find_end_col(start_line, start_col, eol)
            symbol = ""
            message = elmnts[3]
            severity = Flake8Adapter.SEVERITY.get(
                _key,
                Flake8Adapter.SEVERITY['information']
            )

            # Additional sorting
            if severity is Flake8Adapter.SEVERITY['F']:
                if _id in Flake8Adapter.UNUSED_CODE:
                    severity = Flake8Adapter.SEVERITY['unused']

            yield Flake8Adapter._diagnostic(
                self.file, start_line, start_col, end_line, end_col,
                severity, symbol, _id, message,
            )


class PyLintAdapter(AbstractLinterAdapter):

    SEVERITY = {
        'ignored': Ide.DiagnosticSeverity.IGNORED,
        'convention': Ide.DiagnosticSeverity.NOTE,
        'refactor': Ide.DiagnosticSeverity.NOTE,
        'information': Ide.DiagnosticSeverity.NOTE,
        'deprecated': Ide.DiagnosticSeverity.DEPRECATED,
        'warning': Ide.DiagnosticSeverity.WARNING,
        'error': Ide.DiagnosticSeverity.ERROR,
        'fatal': Ide.DiagnosticSeverity.FATAL,
        'unused': (Ide.DiagnosticSeverity.UNUSED if Ide.MAJOR_VERSION >= 41 else
                   Ide.DiagnosticSeverity.NOTE),
    }

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

    NOTE_CODE = [
        "W0511"     # put fixme, todo in information not in warnings
    ]

    linter = "pylint"

    def get_environ(self, config):
        if config:
            pylint_rc = config.getenv("PYLINTRC")
            return {"PYLINTRC": pylint_rc} if pylint_rc else {}
        return {}

    def get_args(self):
        args = ["python", '-m',
                PyLintAdapter.linter,
                "--output-format", "json",
                "--persistent", "n",
                "-j", "0",
                "--score", "n",
                "--exit-zero"]
        if self.file_content:
            args += ["--from-stdin", self.file.get_path()]
        else:
            args += [self.file.get_path()]
        return tuple(args)

    def diagnostics(self, stdout):
        try:
            mapping = json.loads(stdout)
        except json.JSONDecodeError:
            raise LinterError("Failed parsing linter output.")

        for item in mapping:
            line = item.get("line", None)
            column = item.get("column", None)
            if not line or not column:
                continue
            start_line = max(item["line"] - 1, 0)
            start_col = max(item["column"], 0)

            end_line = item.get("endLine", None)
            end_col = item.get("endColumn", None)
            if end_line and end_col:
                end_line = max(end_line - 1, 0)
                end_col = max(end_col, 0)
            else:
                end_line = start_line
                end_col = self.find_end_col(start_line, start_col)

            severity = PyLintAdapter.SEVERITY.get(
                item["type"], PyLintAdapter.SEVERITY['information']
            )
            symbol = item.get("symbol")
            message = item.get("message")
            _id = item.get("message-id")

            # Additional sorting
            if severity is PyLintAdapter.SEVERITY['warning']:
                if _id in PyLintAdapter.UNUSED_CODE:
                    severity = PyLintAdapter.SEVERITY['unused']
                elif _id in PyLintAdapter.DEPRECATED_CODE:
                    severity = PyLintAdapter.SEVERITY['deprecated']
                elif _id in PyLintAdapter.NOTE_CODE:
                    severity = PyLintAdapter.SEVERITY['information']

            if severity not in (
                Ide.DiagnosticSeverity.ERROR,
                Ide.DiagnosticSeverity.FATAL,
            ):
                # make underlined run on multiple lines
                # only for hight severity code
                if start_line != end_line:
                    end_col = self.find_end_col(start_line, start_col)
                end_line = start_line

            yield PyLintAdapter._diagnostic(
                self.file, start_line, start_col, end_line,
                end_col, severity, symbol, _id, message,
            )


def get_linters():
    return [PyLintAdapter, Flake8Adapter]


def get_adapter_class(name):
    for linter in get_linters():
        if linter.linter == name:
            version = linter.get_version()
            _ret = linter if version else None
            return _ret
    return None
