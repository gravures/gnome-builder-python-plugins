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
from cyparso.cython import tree
from parso.python.parser import Parser as _Parser
from parso.python.token import PythonTokenTypes


class Parser(_Parser):
    """
    This class is used to parse Cython files, it then divides them into a
    class structure of different scopes.

    :param pgen_grammar: The grammar object of pgen2. Loaded by load_grammar.
    """

    node_map = {
        'expr_stmt': tree.ExprStmt,
        'classdef': tree.Class,
        'funcdef': tree.Function,
        'file_input': tree.Module,
        'import_name': tree.ImportName,
        'import_from': tree.ImportFrom,
        'break_stmt': tree.KeywordStatement,
        'continue_stmt': tree.KeywordStatement,
        'return_stmt': tree.ReturnStmt,
        'raise_stmt': tree.KeywordStatement,
        'yield_expr': tree.YieldExpr,
        'del_stmt': tree.KeywordStatement,
        'pass_stmt': tree.KeywordStatement,
        'global_stmt': tree.GlobalStmt,
        'nonlocal_stmt': tree.KeywordStatement,
        'print_stmt': tree.KeywordStatement,
        'assert_stmt': tree.AssertStmt,
        'if_stmt': tree.IfStmt,
        'with_stmt': tree.WithStmt,
        'for_stmt': tree.ForStmt,
        'while_stmt': tree.WhileStmt,
        'try_stmt': tree.TryStmt,
        'sync_comp_for': tree.SyncCompFor,
        # Not sure if this is the best idea, but IMO it's the easiest way to
        # avoid extreme amounts of work around the subtle difference of 2/3
        # grammar in list comoprehensions.
        'decorator': tree.Decorator,
        'lambdef': tree.Lambda,
        'lambdef_nocond': tree.Lambda,
        'namedexpr_test': tree.NamedExpr,
        # Cython nodes
        #
        'cclassdef': tree.CClass,
        'cfuncdef': tree.CFunction,
        # cimport_name: tree.CImportName,
        # cimport_from: tree.CImportFrom,
    }
    default_node = tree.CythonNode

    # Names/Keywords are handled separately
    _leaf_map = {
        PythonTokenTypes.STRING: tree.String,
        PythonTokenTypes.NUMBER: tree.Number,
        PythonTokenTypes.NEWLINE: tree.Newline,
        PythonTokenTypes.ENDMARKER: tree.EndMarker,
        PythonTokenTypes.FSTRING_STRING: tree.FStringString,
        PythonTokenTypes.FSTRING_START: tree.FStringStart,
        PythonTokenTypes.FSTRING_END: tree.FStringEnd,
    }

    def __init__(
        self, pgen_grammar, error_recovery=True, start_nonterminal='file_input'
    ):
        super().__init__(
            pgen_grammar,
            error_recovery=error_recovery,
            start_nonterminal=start_nonterminal,
        )

