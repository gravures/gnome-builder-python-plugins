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
import threading
from collections import namedtuple
from collections.abc import Callable
from pathlib import Path
from typing import Any, List, Optional

import gi  # noqa
from gi.repository import Gio, GLib, GObject, Ide

SYMBOL_PARAM_FLAGS = flags = (
    GObject.ParamFlags.CONSTRUCT_ONLY | GObject.ParamFlags.READWRITE
)


log = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)-8s: %(name)-12s -> %(message)s")
handler.setFormatter(formatter)
log.addHandler(handler)


def warn(func):
    """decorator to log functon call."""
    def _func(*args, **kwargs):
        log.warn(f"{func.__qualname__}()")
        func(*args, **kwargs)
    return _func


class PythonSymbolNode(Ide.SymbolNode):
    __gtype_name__ = 'PythonSymbolNode'
    file = GObject.Property(type=Gio.File, flags=SYMBOL_PARAM_FLAGS)
    line = GObject.Property(type=int, flags=SYMBOL_PARAM_FLAGS)
    col = GObject.Property(type=int, flags=SYMBOL_PARAM_FLAGS)
    children = GObject.Property(type=object, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, children=[], **kwargs)

    def __len__(self) -> int:
        return len(self.children)

    def __bool__(self) -> bool:
        return True

    def __getitem__(self, index: int) -> Optional['PythonSymbolNode']:
        try:
            return self.children[index]
        except IndexError:
            return None

    def __iter__(self):
        return iter(self.children)

    def __repr__(self) -> str:
        return (
            f"PythonSymbolNode(line={self.line}, col={self.col}, "
            f"name={self.props.name}, kind={(self.props.kind.value_name)}, "
            # f"file={self.file.get_path()})"
        )

    def do_get_location_async(
        self, cancellable: Optional[Gio.Cancellable],
        callback: Optional[Callable],
        user_data: Any = None
    ) -> None:
        """Request to gets the location for the symbol node."""
        task = Gio.Task.new(self, cancellable, callback)
        task.return_boolean(True)

    def do_get_location_finish(
        self, result: Gio.AsyncResult
    ) -> Optional[Ide.Location]:
        """Completes the request to gets the location for the symbol node."""
        if result.propagate_boolean():
            return Ide.Location.new(self.file, self.line, self.col)
        return None

    def append(self, node: 'PythonSymbolNode') -> None:
        self.children.append(node)

    def dump(self, parent_dump="", indent=0):
        _indent = "".join(["   "] * indent)
        dump = f"{parent_dump}\n{_indent}{self.__repr__()}"
        indent += 1
        for child in self:
            dump = child.dump(dump, indent)
        return dump


Desc = namedtuple("Desc", ["kind", "name"])


def _get_func_def(ast_node, parent_symbol_node):
    decorator_list = []
    for _d in ast_node.decorator_list:
        if isinstance(_d, ast.Name):
            decorator_list.append(_d.id)
        elif isinstance(_d, ast.Call):
            decorator_list.append(_d.func.id)
    if parent_symbol_node.props.kind == Ide.SymbolKind.CLASS:
        if ast_node.name == "__new__":
            return Ide.SymbolKind.CONSTRUCTOR
        elif "property" in decorator_list:
            return Ide.SymbolKind.PROPERTY
        else:
            return Ide.SymbolKind.METHOD
    return Ide.SymbolKind.FUNCTION


def _get_assign_def(ast_node, parent_symbol_node):
    if (
        parent_symbol_node.props.kind in
        [Ide.SymbolKind.PACKAGE, Ide.SymbolKind.CLASS]
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


class PythonSymbolTree(GObject.Object, Ide.SymbolTree):

    AST_STMT = {
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
        ast.Import: Desc(
            kind=lambda _n, _p: Ide.SymbolKind.PACKAGE,
            name=lambda _n: ", ".join([_a.name for _a in _n.names]),
        ),
        ast.ImportFrom: Desc(
            kind=lambda _n, _p: Ide.SymbolKind.PACKAGE,
            name=lambda _n: ", ".join([_a.name for _a in _n.names]),
        ),
        ast.Assign: Desc(
            kind=_get_assign_def,
            name=_get_assign_name,
        )
    }

    @warn
    def __init__(self, ast_module: ast.Module, file: Gio.File):
        super().__init__()
        self.root_node = self._parse_ast_module(ast_module, file)

    @classmethod
    def _parse_ast_module(
        cls, ast_module: ast.Module, file: Gio.File
    ) -> PythonSymbolNode:
        """Visit the ast.Module ast_module recursivly
        and return the tree's root as a PythonSymbolNode
        of Kind Ide.SymbolKind.PACKAGE.
        """
        # log.warn(cls._dump_ast_tree(ast_module))
        root = PythonSymbolNode(
            line=0, col=0,
            name=Path(file.get_path()).name,
            kind=Ide.SymbolKind.PACKAGE,
            file=file
        )
        ast.fix_missing_locations(ast_module)
        for node in ast.iter_child_nodes(ast_module):
            cls._visit_ast_node(node, root, file)
        return root

    @classmethod
    def _dump_ast_tree(cls, ast_tree):
        dump = ""
        for node in ast.walk(ast_tree):
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

    @classmethod
    def _visit_ast_node(
        cls, node: ast.AST,
        parent: PythonSymbolNode,
        file: Gio.File
    ) -> None:
        """Visit the AST 'node'.

        If the type of node is of interest (function, class, etc...)
        fill the SymbolNode parent's children list with a new instance
        of SymbolNode. Call visit_ast_node recursivly on children.
        """
        symbole_node = None
        desc = cls.AST_STMT.get(type(node), None)
        if desc:
            kind = desc.kind(node, parent)
            if kind:
                name = desc.name(node)
                symbole_node = PythonSymbolNode(
                    line=node.lineno - 1,
                    col=node.col_offset,
                    kind=kind,
                    name=name,
                    file=file
                )
                parent.append(symbole_node)
                #
                for node in ast.iter_child_nodes(node):
                    cls._visit_ast_node(node, symbole_node, file)

    def do_get_n_children(self, node: Ide.SymbolNode) -> int:
        """Get the number of children of @node.
        If @node is None, the root node is assumed.

        Returns: An unsigned integer containing the number of children.
        """
        return len(node) if node else len(self.root_node)

    def do_get_nth_child(
        self,
        node: Optional[Ide.SymbolNode],
        nth: int
    ) -> Optional[Ide.SymbolNode]:
        """Gets the nth child node of @node.

        Returns: an Ide.SymbolNode or None.
        """
        return node[nth] if node else self.root_node[nth]

    def get_root(self) -> PythonSymbolNode:
        """Returns the root node of this SymbolTree.

        The root is always of kind Ide.SymbolKind.PACKAGE.
        """
        return self.root_node

    def dump(self):
        return self.root_node.dump()


class PythonSymbolProvider(Ide.Object, Ide.SymbolResolver):
    """PythonSymbolProvIder."""

    @warn
    def do_lookup_symbol_async(
        self, location: Ide.Location,
        cancellable: Optional[Gio.Cancellable],
        callback: Optional[Callable],
        user_data: Any = None
    ) -> None:
        """Asynchronously requests that we determine the symbol existing
        at the source location denoted by @self. @callback should call
        lookup_symbol_finish() to retrieve the result.
        """
        task = Gio.Task.new(self, cancellable, callback)
        # task.return_error(GLib.Error('Not implemented'))
        task.return_boolean(False)

    def do_lookup_symbol_finish(
        self, result: Gio.AsyncResult
    ) -> Optional[Ide.Symbol]:
        """Completes an asynchronous call to lookup a symbol using
        ide_symbol_resolver_lookup_symbol_async().

        Returns: An #IdeSymbol if successful; otherwise None
        """
        result.propagate_boolean()

    @warn
    def do_get_symbol_tree_async(
        self, file: Gio.File,
        buffer: Optional[bytes],
        cancellable: Optional[Gio.Cancellable],
        callback: Optional[Callable],
        user_data: Any = None
    ) -> None:
        """Asynchronously fetch an up to date symbol tree for @file."""
        task = Gio.Task.new(self, cancellable, callback)
        task.root_task = user_data

        # create subprocess launcher
        context = self.get_context()
        srcdir = context.ref_workdir().get_path()
        launcher = Ide.SubprocessLauncher()
        launcher.set_flags(Gio.SubprocessFlags.STDOUT_PIPE)
        launcher.set_cwd(srcdir)

        threading.Thread(
            target=self._inspect_module,
            args=(task, launcher, file),
            name='python-symbols-thread'
        ).start()

    def do_get_symbol_tree_finish(
        self, result: Gio.AsyncResult
    ) -> Optional[Ide.SymbolTree]:
        """Completes an asynchronous request
        to get the symbol tree for the requested file.
        """
        if result.propagate_boolean():
            return result.symbol_tree
        return None

    @warn
    def _inspect_module(
        self, task: Gio.Task,
        launcher: Ide.SubprocessLauncher,
        file: Gio.File
    ):
        args = ['sources_inspect.py', file.get_path()]
        try:
            launcher.push_args(args)
            subprocess = launcher.spawn()
            success, stdout, stderr = subprocess.communicate_utf8(None, None)
            if not success:
                log.warn('Failed to run sources_inspect.py')
                task.return_error(
                    GLib.Error('Failed to run sources_inspect.py')
                )
                return

            tmp_path = Path(stdout)
            with open(tmp_path, mode='rb') as _file:
                data = _file.read()
            ast_tree = pickle.loads(data)
            os.unlink(tmp_path)

            if not isinstance(ast_tree, ast.Module):
                log.warn("Failed to unpickle to an ast.Module")
                task.return_error(
                    GLib.Error("Failed to unpickle to an ast.Module")
                )
            task.symbol_tree = PythonSymbolTree(ast_tree, file)
            # log.warn(f"{task.symbol_tree.dump()}")
        except GLib.Error as err:
            log.warn(f"GLib.Error: {err}")
            task.return_error(err)
        except OSError as err:
            log.warn(f"Failed to open stream: {err}")
            task.return_error(GLib.Error(f"Failed to open stream: {err}"))
        except pickle.UnpicklingError as err:
            log.warn(f"Failed to unpickle stream: {err}")
            task.return_error(GLib.Error(f"Failed to unpickle stream: {err}"))
        except (IndexError, KeyError) as err:
            log.warn(f"Failed to extract information from ast: {err}")
            task.return_error(
                GLib.Error(f"Failed to extract information from ast: {err}")
            )
        else:
            task.return_boolean(True)

    @warn
    def do_load(self) -> None:
        pass

    @warn
    def do_unload(self) -> None:
        pass

    @warn
    def do_find_references_async(
        self,
        location: Ide.Location,
        language_id: Optional[str],
        cancellable: Optional[Gio.Cancellable],
        callback: Callable,
        user_data: Any = None
    ) -> None:
        """Dont Know"""
        task = Gio.Task.new(self, cancellable, callback)
        # task.return_error(GLib.Error('Not implemented'))
        task.return_boolean(False)

    def do_find_references_finish(
        self, result: Gio.AsyncResult
    ) -> Optional[List[Ide.Range]]:
        """Completes an asynchronous request find_references_async()."""
        result.propagate_boolean()

    @warn
    def do_find_nearest_scope_async(
        self, location: Ide.Location,
        cancellable: Optional[Gio.Cancellable],
        callback: Callable,
        user_data: Any = None
    ) -> None:
        """This function asynchronously requests to locate
        the containing scope for a given source location.
        """
        task = Gio.Task.new(self, cancellable, callback)
        task.return_error(GLib.Error('Not implemented'))

    def do_find_nearest_scope_finish(
        self, result: Gio.AsyncResult
    ) -> Optional[Ide.Symbol]:
        """This function completes an asynchronous operation
        to locate the containing scope for a given source location.
        """
        return result.propagate_boolean()


# class PythonCodeIndexEntries(GObject.Object, Ide.CodeIndexEntries):
#     def __init__(self, file, entries):
#         super().__init__()
#         self.entries = entries
#         self.entry_iter = iter(entries)
#         self.file = file

#     def do_get_next_entry(self):
#         if self.entry_iter is not None:
#             try:
#                 return next(self.entry_iter)
#             except StopIteration:
#                 self.entry_iter = None
#         return None

#     def do_get_file(self):
#         return self.file


# class PythonCodeIndexer(Ide.Object, Ide.CodeIndexer):
#     active = False
#     queue = None

#     def __init__(self):
#         super().__init__()
#         self.queue = []

#     @staticmethod
#     def _get_node_name(node):
#         prefix = {
#             Ide.SymbolKind.FUNCTION: 'f',
#             Ide.SymbolKind.METHOD: 'f',
#             Ide.SymbolKind.VARIABLE: 'v',
#             Ide.SymbolKind.CONSTANT: 'v',
#             Ide.SymbolKind.CLASS: 'c',
#         }.get(node.props.kind, 'x')
#         return prefix + '\x1F' + node.props.name

#     def _flatten_node_list(self, root_node):
#         nodes = [root_node]
#         for node in root_node:
#             nodes += self._flatten_node_list(node)
#         return nodes

#     @staticmethod
#     @warn
#     def _index_file_cb(
#         source_object,
#         res: Gio.AsyncResult,
#     ) -> None:
#         """A Gio.AsyncReadyCallback"""
#         self = source_object
#         task = res.root_task
#         log.warn(f"{res.symbol_tree.get_root()}")
#         root_node = res.symbol_tree.get_root()
#         builder = Ide.CodeIndexEntryBuilder()
#         entries = []

#         for node in self._flatten_node_list(root_node):
#             builder.set_key(f"{id(node)}|{node.props.name}")  # Some unique id
#             builder.set_name(self._get_node_name(node))
#             builder.set_kind(node.props.kind)
#             builder.set_flags(node.props.flags)
            # Not sure why offset here doesn't match tree
#             builder.set_range(node.props.line + 1, node.props.col + 1, 0, 0)
#             entries.append(builder.build())

#         task.entries = PythonCodeIndexEntries(task. file, entries)
#         task.return_boolean(True)
#         self.active = False

#     @warn
#     def do_index_file_async(
#         self, file, build_flags, cancellable, callback, data=None
#     ):
#         task = Gio.Task.new(self, cancellable, callback)
#         task.entries = None
#         task.file = file
#         if self.active:
#             self.queue.append(task)
#             return

#         self.active = True
#         provider = PythonSymbolProvider()
#         provider.get_symbol_tree_async(
#             file, None, cancellable, self._index_file_cb, task
#         )

#     def do_index_file_finish(self, result):
#         if result.propagate_boolean():
#             return result.entries
#         return None

#     @warn
#     def do_generate_key_async(
#         self, location, flags, cancellable, callback, user_data=None
#     ):
#         task = Gio.Task.new(self, cancellable, callback)
#         task.return_error(GLib.Error('Not implemented'))

#     def do_generate_key_finish(self, result):
#         if result.propagate_boolean():
#             return ''
#         return None

