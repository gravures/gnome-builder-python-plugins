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
from parso.python import tree
from parso.python.tree import _create_params  # _defined_names,
from parso.python.tree import (
    AssertStmt, Class, ClassOrFunc, Decorator, DocstringMixin,
    EndMarker, ExprStmt, Flow, ForStmt, FStringEnd, FStringStart,
    FStringString, Function, GlobalStmt, IfStmt, Import, ImportFrom,
    ImportName, Keyword, KeywordStatement, Lambda, Literal, Module
)
from parso.python.tree import Name as _Name
from parso.python.tree import (
    NamedExpr, Newline, Number, Operator, Param, PythonBaseNode,
    PythonErrorLeaf, PythonErrorNode, PythonNode, ReturnStmt,
    Scope, String, SyncCompFor, TryStmt, UsedNamesMapping,
    WhileStmt, WithStmt, YieldExpr, _StringComparisonMixin
)

_CFUNC_CONTAINERS = set([
    'cvar_def',  # 'cvar_decl',
]) | tree._FUNC_CONTAINERS


_GET_DEFINITION_TYPES = set([
    'expr_stmt', 'sync_comp_for', 'with_stmt', 'for_stmt', 'import_name',
    'import_from', 'param', 'del_stmt', 'namedexpr_test',
])

_IMPORTS = set(['import_name', 'import_from'])


# Cython base classes
class CythonNode(PythonNode):
    __slots__ = ()


class CythonErrorNode(PythonErrorNode):
    __slots__ = ()


class CythonErrorLeaf(PythonErrorLeaf):
    __slots__ = ()


class Name(_Name):
    __slots__ = ()

    def get_definition(self, import_name_always=False, include_setitem=False):
        """
        Returns None if there's no definition for a name.

        :param import_name_always: Specifies if an import name is always a
            definition. Normally foo in `from foo import bar` is not a
            definition.
        """
        node = self.parent
        type_ = node.type

        if type_ in ('funcdef', 'classdef', 'cfuncdef', 'cclassdef'):
            if self == node.name:
                return node
            return None

        if type_ == 'except_clause':
            if self.get_previous_sibling() == 'as':
                return node.parent  # The try_stmt.
            return None

        while node is not None:
            if node.type == 'suite':
                return None
            if node.type in _GET_DEFINITION_TYPES:
                if self in node.get_defined_names(include_setitem):
                    return node
                if import_name_always and node.type in _IMPORTS:
                    return node
                return None
            node = node.parent
        return None


class CClassOrCFunc(Scope):
    __slots__ = ()

    @property
    def name(self):
        """
        Returns the `Name` leaf that defines the function or class name.
        """
        return self.children[1]

    def get_decorators(self):
        """
        :rtype: list of :class:`Decorator`
        """
        decorated = self.parent
        if decorated.type == 'async_funcdef':
            decorated = decorated.parent

        if decorated.type == 'decorated':
            if decorated.children[0].type == 'decorators':
                return decorated.children[0].children
            else:
                return decorated.children[:1]
        else:
            return []

    def _search_in_scope(self, *names):
        def scan(children):
            for element in children:
                if element.type in names:
                    yield element
                if element.type in _CFUNC_CONTAINERS:
                    yield from scan(element.children)
        return scan(self.children)


class CClass(CClassOrCFunc):
    """
    Used to store the parsed contents of a cython cdef class.
    """
    type = 'cclassdef'
    __slots__ = ()

    def __init__(self, children):
        super().__init__(children)

    def get_super_arglist(self):
        """
        Returns the `arglist` node that defines the super classes. It returns
        None if there are no arguments.
        """
        if self.children[2] != '(':  # Has no parentheses
            return None
        else:
            if self.children[3] == ')':  # Empty parentheses
                return None
            else:
                return self.children[3]


class CFunction(CClassOrCFunc):
    """
    Used to store the parsed contents of a python function.

    Children::

        0. <Keyword: def>
        1. <Name>
        2. parameter list (including open-paren and close-paren <Operator>s)
        3. or 5. <Operator: :>
        4. or 6. Node() representing function body
        3. -> (if annotation is also present)
        4. annotation (if present)
    """
    type = 'cfuncdef'
    __slots__ = ()

    def __init__(self, children):
        super().__init__(children)
        parameters = self.children[2]  # After `def foo`
        parameters_children = parameters.children[1:-1]
        # If input parameters list already has Param objects, keep it as is;
        # otherwise, convert it to a list of Param objects.
        if not any(isinstance(child, Param) for child in parameters_children):
            parameters.children[1:-1] = _create_params(
                parameters, parameters_children
            )

    def _get_param_nodes(self):  # noqa
        return self.children[2].children

    def get_params(self):  # noqa
        """
        Returns a list of `Param()`.
        """
        return [p for p in self._get_param_nodes() if p.type == 'param']

    @property
    def name(self):
        return self.children[1]  # First token after `def`

    def iter_yield_exprs(self):
        """
        Returns a generator of `yield_expr`.
        """
        def scan(children):
            for element in children:
                if element.type in ('classdef', 'funcdef', 'lambdef'):
                    continue

                try:
                    nested_children = element.children
                except AttributeError:
                    if element.value == 'yield':
                        if element.parent.type == 'yield_expr':
                            yield element.parent
                        else:
                            yield element
                else:
                    yield from scan(nested_children)

        return scan(self.children)

    def iter_return_stmts(self):
        """
        Returns a generator of `return_stmt`.
        """
        def scan(children):
            for element in children:
                if (
                    element.type == 'return_stmt'
                    or element.type == 'keyword'
                    and element.value == 'return'
                ):
                    yield element
                if element.type in tree._RETURN_STMT_CONTAINERS:
                    yield from scan(element.children)

        return scan(self.children)

    def iter_raise_stmts(self):
        """
        Returns a generator of `raise_stmt`. Includes raise
        statements inside try-except blocks
        """
        def scan(children):
            for element in children:
                if (
                    element.type == 'raise_stmt'
                    or element.type == 'keyword'
                    and element.value == 'raise'
                ):
                    yield element
                if element.type in tree._RETURN_STMT_CONTAINERS:
                    yield from scan(element.children)

        return scan(self.children)

    def is_generator(self):  # noqa
        """
        :return bool: Checks if a function is a generator or not.
        """
        return next(self.iter_yield_exprs(), None) is not None

    @property
    def annotation(self):
        """
        Returns the test node after `->` or `None` if there is no annotation.
        """
        try:
            if self.children[3] == "->":
                return self.children[4]
            assert self.children[3] == ":"
            return None
        except IndexError:
            return None
