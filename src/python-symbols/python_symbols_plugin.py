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
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, List, Optional

import gi  # noqa
from gi.repository import Gio, GLib, GObject, Ide

from parsers import AstSyntaxNode, ParsoSyntaxNode, SyntaxNode, SyntaxNodeError
from symbols_preferences import PythonSymbolsPreferencesAddin  # noqa

SYMBOL_PARAM_FLAGS = flags = (
    GObject.ParamFlags.CONSTRUCT_ONLY | GObject.ParamFlags.READWRITE
)


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


class PythonSymbolTree(GObject.Object, Ide.SymbolTree):

    @debug
    def __init__(self, file: Gio.File):
        """Visit the ast.Module ast_module recursivly
        and return the tree's root as a PythonSymbolNode
        of Kind Ide.SymbolKind.PACKAGE.
        """
        super().__init__()
        gsettings = Gio.Settings(
            schema="org.gnome.builder.plugins.python-symbols"
        )

        self.root_node = PythonSymbolNode(
            line=0, col=0,
            name=Path(file.get_path()).name,
            kind=Ide.SymbolKind.PACKAGE,
            file=file
        )

        parser = gsettings.get_string("symbol-parser")
        if parser == "ast":
            self.syntax_tree = AstSyntaxNode(
                file,
                xprt_impts=gsettings.get_boolean("export-imports"),
                xprt_mod_var=gsettings.get_boolean("export-modules-variables"),
                xprt_cls_var=gsettings.get_boolean("export-class-variables"),
            )
        elif parser == "parso":
            self.syntax_tree = ParsoSyntaxNode(
                file,
                xprt_impts=gsettings.get_boolean("export-imports"),
                xprt_mod_var=gsettings.get_boolean("export-modules-variables"),
                xprt_cls_var=gsettings.get_boolean("export-class-variables"),
            )
        else:
            raise SyntaxNodeError(f"{parser} not a SyntaxParser")

        log.debug(self.syntax_tree.dump())
        for syntax_node in self.syntax_tree.iter_child_nodes():
            self._visit_syntax_node(syntax_node, self.root_node, file)

    @classmethod
    def _visit_syntax_node(
        cls, syntax_node: SyntaxNode,
        parent: PythonSymbolNode,
        file: Gio.File,
    ) -> None:
        """Visit the AST 'node'.

        If the type of node is of interest (function, class, etc...)
        fill the SymbolNode parent's children list with a new instance
        of SymbolNode. Call visit_ast_node recursivly on children.
        """
        symbole_node = None
        kind = syntax_node.get_kind()
        if kind:
            symbole_node = PythonSymbolNode(
                line=syntax_node.get_line(),
                col=syntax_node.get_col(),
                kind=syntax_node.get_kind(),
                name=syntax_node.get_name(),
                file=file
            )
            parent.append(symbole_node)
            for node in syntax_node.iter_child_nodes():
                cls._visit_syntax_node(node, symbole_node, file)

    @staticmethod
    def _dump_syntax_tree(syntax_tree):
        return syntax_tree.dump()

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

    # @debug
    # def do_load(self) -> None:
    #     pass

    # @debug
    # def do_unload(self) -> None:
    #     pass

    @debug
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

    @debug
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

    @debug
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

    @debug
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

        # gsettings = Gio.Settings(
        #     schema="org.gnome.builder.plugins.python-symbols"
        # )
        # parser = gsettings.get_string("symbol-parser")
        # context = self.get_context()
        # buf_man = Ide.BufferManager.from_context(context)
        # buffer = buf_man.find_buffer(file)
        # lang = buffer.get_language_id()
        # if lang == "cython" and parser == "ast":
        #     task.return_boolean(False)
        #     return

        threading.Thread(
            target=self._inspect_module,
            args=(task, file),
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

    @debug
    def _inspect_module(self, task: Gio.Task, file: Gio.File):
        try:
            context = self.get_context()
            if not context:
                task.return_boolean(False)
                return
            task.symbol_tree = PythonSymbolTree(file)
            # log.debug(f"{task.symbol_tree.dump()}")
        except SyntaxNodeError as err:
            log.exception("SyntaxNodeError")
            task.return_error(GLib.Error(str(err)))
        else:
            task.return_boolean(True)


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
#     @debug
#     def _index_file_cb(
#         source_object,
#         res: Gio.AsyncResult,
#     ) -> None:
#         """A Gio.AsyncReadyCallback"""
#         self = source_object
#         task = res.root_task
#         log.debug(f"{res.symbol_tree.get_root()}")
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

#     @debug
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

#     @debug
#     def do_generate_key_async(
#         self, location, flags, cancellable, callback, user_data=None
#     ):
#         task = Gio.Task.new(self, cancellable, callback)
#         task.return_error(GLib.Error('Not implemented'))

#     def do_generate_key_finish(self, result):
#         if result.propagate_boolean():
#             return ''
#         return None

