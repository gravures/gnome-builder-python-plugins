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
import ast
import logging
import os
import pickle
from abc import ABC, abstractmethod
from collections import namedtuple
from enum import Flag
from pathlib import Path

import gi  # noqa
from gi.repository import Gio, GLib, Ide

import parso

log = logging.getLogger(__name__)
log = logging.getLogger(__name__)
log.setLevel(Ide.log_get_verbosity() * 10)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)-13s %(name)+49s %(levelname)+8s: %(message)s',
    '%H:%M:%S.%04d'
)
handler.setFormatter(formatter)
log.addHandler(handler)


def debug(func):
    """decorator to log function call."""
    def _func(*args, **kwargs):
        log.debug(f"{func.__qualname__}()")
        func(*args, **kwargs)
    return _func


class SyntaxNodeError(Exception):
    """Exception raised by LinterAdapter."""
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class SYNTAX_KIND(Flag):
    NONE = 0


class SyntaxNode(ABC):
    """SyntaxNode"""

    def __new__(cls, source, *args, parent=None, **kwargs):
        instance = super().__new__(cls)
        if isinstance(source, Gio.File):
            instance.source = cls._source_from_file(source, **kwargs)
            instance._is_root = True
        else:
            instance.source = source
            instance._is_root = False
        return instance

    @abstractmethod
    def __init__(self, source, *args, parent=None, **kwargs):
        self.parent = parent
        self._kind = None
        self._children = []

    @classmethod
    @abstractmethod
    def _source_from_file(cls, **kwargs):  # noqa
        pass

    @abstractmethod
    def iter_child_nodes(self):
        pass

    @abstractmethod
    def dump(self):
        pass

    def is_root(self):
        return self._is_root

    def get_parent(self):
        return self.parent

    def get_kind(self):
        return self._kind

    def get_name(self):
        return self._name

    def get_line(self):
        return self._line

    def get_col(self):
        return self._col


class ParsoSyntaxNode(SyntaxNode):
    """ParsoSyntaxNode"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.source.type == 'file_input':
            self._kind = Ide.SymbolKind.PACKAGE
            self._name = "module"
            self._line, self._col = (0, 0)
            self._children = list(self.source.children)
            return

        if self.source.type == 'decorated':
            self.decorators = self.source.children[:-1]
            self.source = self.source.children[-1]

        if self.source.type == 'classdef':
            self._kind = Ide.SymbolKind.CLASS
            self._name = self.source.name.value
            self._line, self._col = self.source.start_pos
            self._children = list(self.source.get_suite().children)

        elif self.source.type == 'funcdef':
            self._kind = (
                Ide.SymbolKind.METHOD
                if self.parent._kind is Ide.SymbolKind.CLASS
                else Ide.SymbolKind.FUNCTION
            )
            self._name = self.source.name.value
            self._line, self._col = self.source.start_pos
            self._children = list(self.source.get_suite().children)

        # FIXME: simple import not exported
        elif self.source.type == 'simple_stmt':
            self.source = self.source.children[0]
            if self.source.type in ('import_names', 'import_from'):
                self._kind = Ide.SymbolKind.PACKAGE
                self._name = ", ".join(
                    [n.value for n in self.source.get_defined_names()]
                )
            self._line, self._col = self.source.start_pos

        # TODO: module variable & class variable

    @classmethod
    def _source_from_file(cls, file, **kwargs):  # noqa
        try:
            with open(file.get_path(), "r") as _file:
                data = _file.read()
            source = parso.parse(data)
        except IOError as err:
            raise SyntaxNodeError(f"Failed to open stream: {err}")
        except Exception as err:
            raise SyntaxNodeError(f"Unexpected error: {err}")
        return source  # noqa

    def iter_child_nodes(self):
        for parso_node in self._children:
            yield ParsoSyntaxNode(parso_node, parent=self)

    def get_line(self):
        return max(self._line - 1, 0)

    def dump(self):
        # TODO: dump method
        pass


EXPORT_VARIABLE_SCOPE = [Ide.SymbolKind.PACKAGE, Ide.SymbolKind.CLASS]


def _get_func_def(ast_node, parent_syntax_node):
    decorator_list = []
    for _d in ast_node.decorator_list:
        if isinstance(_d, ast.Name):
            decorator_list.append(_d.id)
        elif isinstance(_d, ast.Call):
            decorator_list.append(_d.func.id)
    if parent_syntax_node.get_kind() == Ide.SymbolKind.CLASS:
        if ast_node.name == "__new__":
            return Ide.SymbolKind.CONSTRUCTOR
        elif "property" in decorator_list:
            return Ide.SymbolKind.PROPERTY
        else:
            return Ide.SymbolKind.METHOD
    return Ide.SymbolKind.FUNCTION


def _get_assign_def(ast_node, parent_syntax_node):
    if (
        parent_syntax_node.get_kind() in
        EXPORT_VARIABLE_SCOPE
    ):
        return Ide.SymbolKind.VARIABLE
    return None


def _get_assign_name(ast_node):
    if isinstance(ast_node.targets[0], ast.Name):
        return ast_node.targets[0].id
    elif isinstance(ast_node.targets[0], ast.Tuple):
        return ast_node.targets[0].elts[0].id
    else:
        return "UNDEFINED"


Desc = namedtuple("Desc", ["kind", "name"])


class AstSyntaxNode(SyntaxNode):
    """AstSyntaxNode"""

    AST_BASE_STMT = {
        ast.FunctionDef: Desc(
            kind=_get_func_def,
            name=lambda _n: _n.name,
        ),
        ast.AsyncFunctionDef: Desc(
            kind=_get_func_def,
            name=lambda _n: _n.name,
        ),
        ast.ClassDef: Desc(
            kind=lambda _n, _p: Ide.SymbolKind.CLASS,
            name=lambda _n: _n.name,
        ),
    }

    AST_IMPT_STMT = {
        ast.Import: Desc(
            kind=lambda _n, _p: Ide.SymbolKind.PACKAGE,
            name=lambda _n: ", ".join([_a.name for _a in _n.names]),
        ),
        ast.ImportFrom: Desc(
            kind=lambda _n, _p: Ide.SymbolKind.PACKAGE,
            name=lambda _n: ", ".join([_a.name for _a in _n.names]),
        ),
    }

    AST_VAR_STMT = {
        ast.Assign: Desc(
            kind=_get_assign_def,
            name=_get_assign_name,
        ),
    }

    AST_STMT = {}

    @debug
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._children = []
        for ast_node in ast.iter_child_nodes(self.source):
            self._children.append(ast_node)

        desc = self.AST_STMT.get(type(self.source), None)
        if desc:
            self._kind = desc.kind(self.source, self.parent)
            self._name = desc.name(self.source)
            self._line = self.source.lineno - 1
            self._col = self.source.col_offset

    @classmethod
    def _source_from_file(cls, file, **kwargs):
        # context = kwargs.get("context", None)
        # if context is None:
        #     raise AttributeError("need an Ide.Context")
        # srcdir = context.ref_workdir().get_path()
        launcher = Ide.SubprocessLauncher()
        launcher.set_flags(Gio.SubprocessFlags.STDOUT_PIPE)
        # launcher.set_cwd(srcdir)
        launcher.push_args(['sources_inspect.py', file.get_path()])

        try:
            subprocess = launcher.spawn()
            success, stdout, stderr = subprocess.communicate_utf8(None, None)
            if not success:
                raise SyntaxNodeError('Failed to run sources_inspect.py')
            tmp_path = Path(stdout)
            with open(tmp_path, mode='rb') as _file:
                data = _file.read()
            ast_tree = pickle.loads(data)
            os.unlink(tmp_path)

        except GLib.Error as err:
            raise SyntaxNodeError(err)
        except OSError as err:
            raise SyntaxNodeError(f"Failed to open stream: {err}")
        except pickle.UnpicklingError as err:
            raise SyntaxNodeError(f"Failed to unpickle stream: {err}")

        if not isinstance(ast_tree, ast.Module):
            raise SyntaxNodeError("Failed to unpickle to an ast.Module")
        ast.fix_missing_locations(ast_tree)

        global EXPORT_VARIABLE_SCOPE
        EXPORT_VARIABLE_SCOPE.clear()
        cls.AST_STMT = dict(cls.AST_BASE_STMT)
        if kwargs.get("xprt_impts"):
            cls.AST_STMT |= cls.AST_IMPT_STMT
        if kwargs.get("xprt_mod_var"):
            cls.AST_STMT |= cls.AST_VAR_STMT
            EXPORT_VARIABLE_SCOPE.append(Ide.SymbolKind.PACKAGE)
        if kwargs.get("xprt_class_var"):
            cls.AST_STMT |= cls.AST_VAR_STMT
            EXPORT_VARIABLE_SCOPE.append(Ide.SymbolKind.CLASS)
        return ast_tree

    def dump(self):
        dump = ""
        for node in ast.walk(self.source):
            _type = type(node)
            expr = "expr" if issubclass(_type, ast.expr) else ""
            stmt = "stmt" if issubclass(_type, ast.stmt) else ""
            line = node.lineno if hasattr(node, "lineno") else ""
            name = node.name if hasattr(node, "name") else ""
            dump += f"{type(node)}({expr},{stmt})"
            if name:
                dump += f" name:{name}"
            if line:
                dump += f" line:{line}"
            dump += "\n"
        return dump

    def iter_child_nodes(self):
        for ast_node in self._children:
            yield AstSyntaxNode(ast_node, parent=self)

