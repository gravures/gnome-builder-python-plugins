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
import json
from abc import ABC, abstractmethod

import gi
from gi.repository import Gio, Ide


class LinterError(Exception):
    """Exception raised by LinterAdapter."""

    def __init__(self, message):
        self.message = message
        super().__init__(message)


class AbstractLinterAdapter(ABC):

    def __init__(self):
        self.file = None
        self.file_content = None
        self.linter = None

    def set_file(self, file, file_content):
        if not isinstance(file, Gio.File):
            raise LinterError(
                f"file should be an instance of Gio.File, got {file.__class__}"
            )
        self.file = file
        self.file_content = file_content

    @staticmethod
    def _diagnostic(
        file, start_line, start_col, end_line, end_col,
        severity, symbol, _id, message,
    ):
        """Return an Ide.Diagnostic."""

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

    @abstractmethod
    def get_args(self):
        pass

    @abstractmethod
    def get_environ(self, config):
        pass

    @abstractmethod
    def diagnostics(self, stdout):
        pass


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

    NOTE_CODE = [
        "W0511"     # put fixme, todo in information not in warnings
    ]

    def __init__(self):
        super().__init__()
        self.linter = "pylint"

    def get_environ(self, config):
        pylint_rc = config.getenv("PYLINTRC")
        env = {"PYLINTRC": pylint_rc} if pylint_rc else {}
        return env

    def get_args(self):
        args = [self.linter, "--output-format",
            "json", "--persistent", "n", "-j", "0",
            "--score", "n", "--exit-zero"]
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
                end_col = start_col

            severity = PyLintAdapter.SEVERITY[item["type"]]
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

            yield PyLintAdapter._diagnostic(
                self.file, start_line, start_col, end_line, end_col,
                severity, symbol, _id, message,
            )


