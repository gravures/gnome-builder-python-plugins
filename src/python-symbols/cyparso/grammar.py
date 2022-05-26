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
import os
from typing import Dict

from cyparso.cython.tokenize import tokenize, tokenize_lines
from parso.grammar import Grammar
from parso.python.errors import ErrorFinderConfig
from parso.python.parser import Parser as PythonParser
from parso.python.token import PythonTokenTypes
from parso.utils import PythonVersionInfo, parse_version_string

_loaded_grammars: Dict[str, 'Grammar'] = {}


class CythonGrammar(Grammar):
    _error_normalizer_config = ErrorFinderConfig()
    _token_namespace = PythonTokenTypes
    _start_nonterminal = 'file_input'

    def __init__(self, version_info: PythonVersionInfo, bnf_text: str):
        super().__init__(
            bnf_text,
            tokenizer=self._tokenize_lines,
            parser=PythonParser,
            diff_parser=None  # diff_parser
        )
        self.version_info = version_info

    def _tokenize_lines(self, lines, **kwargs):
        return tokenize_lines(lines, version_info=self.version_info, **kwargs)

    def _tokenize(self, code):
        # Used by Jedi.
        return tokenize(code, version_info=self.version_info)


def load_grammar(*, version: str = None, path: str = None):
    """
    Loads a :py:class:`parso.Grammar`. The default version is the current Python
    version.

    :param str version: A python version string, e.g. ``version='3.8'``.
    :param str path: A path to a grammar file
    """
    version_info = parse_version_string(version)

    file = path or os.path.join(
        'cython',
        'grammar%s%s.txt' % (version_info.major, version_info.minor)
    )

    global _loaded_grammars
    path = os.path.join(os.path.dirname(__file__), file)
    try:
        return _loaded_grammars[path]
    except KeyError:
        try:
            with open(path) as f:
                bnf_text = f.read()

            grammar = CythonGrammar(version_info, bnf_text)
            return _loaded_grammars.setdefault(path, grammar)
        except FileNotFoundError:
            message = "Python version %s.%s is currently not supported." % (
                version_info.major, version_info.minor
            )
            raise NotImplementedError(message)
