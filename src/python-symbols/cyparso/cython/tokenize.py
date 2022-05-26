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
import sys

import parso
from parso.python.tokenize import (
    BOM_UTF8_STRING, DEDENT, ENDMARKER, ERROR_DEDENT, ERRORTOKEN, FSTRING_END,
    FSTRING_START, FSTRING_STRING, INDENT, MAX_UNICODE, NAME, NEWLINE, NUMBER,
    OP, STRING, FStringNode, PythonToken, Token, TokenCollection,
    _all_string_prefixes, _compile, group, maybe, tokenize, tokenize_lines
)
from parso.utils import parse_version_string


def _create_token_collection(version_info):
    # Note: we use unicode matching for names ("\w") but ascii matching for
    # number literals.
    Whitespace = r'[ \f\t]*'
    whitespace = _compile(Whitespace)
    Comment = r'#[^\r\n]*'
    Name = '([A-Za-z_0-9\u0080-' + MAX_UNICODE + ']+)'

    Hexnumber = r'0[xX](?:_?[0-9a-fA-F])+'
    Binnumber = r'0[bB](?:_?[01])+'
    Octnumber = r'0[oO](?:_?[0-7])+'
    Decnumber = r'(?:0(?:_?0)*|[1-9](?:_?[0-9])*)'
    Intnumber = group(Hexnumber, Binnumber, Octnumber, Decnumber)
    Exponent = r'[eE][-+]?[0-9](?:_?[0-9])*'
    Pointfloat = group(r'[0-9](?:_?[0-9])*\.(?:[0-9](?:_?[0-9])*)?',
                       r'\.[0-9](?:_?[0-9])*') + maybe(Exponent)
    Expfloat = r'[0-9](?:_?[0-9])*' + Exponent
    Floatnumber = group(Pointfloat, Expfloat)
    Imagnumber = group(r'[0-9](?:_?[0-9])*[jJ]', Floatnumber + r'[jJ]')
    Number = group(Imagnumber, Floatnumber, Intnumber)

    # Note that since _all_string_prefixes includes the empty string,
    #  StringPrefix can be the empty string (making it optional).
    possible_prefixes = _all_string_prefixes()
    StringPrefix = group(*possible_prefixes)
    StringPrefixWithF = group(*_all_string_prefixes(include_fstring=True))
    fstring_prefixes = _all_string_prefixes(include_fstring=True, only_fstring=True)
    FStringStart = group(*fstring_prefixes)

    # Tail end of ' string.
    Single = r"(?:\\.|[^'\\])*'"
    # Tail end of " string.
    Double = r'(?:\\.|[^"\\])*"'
    # Tail end of ''' string.
    Single3 = r"(?:\\.|'(?!'')|[^'\\])*'''"
    # Tail end of """ string.
    Double3 = r'(?:\\.|"(?!"")|[^"\\])*"""'
    Triple = group(StringPrefixWithF + "'''", StringPrefixWithF + '"""')

    # Because of leftmost-then-longest match semantics, be sure to put the
    # longest operators first (e.g., if = came before ==, == would get
    # recognized as two instances of =).
    Operator = group(r"\*\*=?", r">>=?", r"<<=?",
                     r"//=?", r"->",
                     r"[+\-*/%&@`|^!=<>]=?",
                     r"~")

    Bracket = '[][(){}]'

    special_args = [r'\.\.\.', r'\r\n?', r'\n', r'[;.,@]']
    if version_info >= (3, 8):
        special_args.insert(0, ":=?")
    else:
        special_args.insert(0, ":")
    Special = group(*special_args)

    Funny = group(Operator, Bracket, Special)

    # First (or only) line of ' or " string.
    ContStr = group(StringPrefix + r"'[^\r\n'\\]*(?:\\.[^\r\n'\\]*)*"
                    + group("'", r'\\(?:\r\n?|\n)'),
                    StringPrefix + r'"[^\r\n"\\]*(?:\\.[^\r\n"\\]*)*'
                    + group('"', r'\\(?:\r\n?|\n)'))
    pseudo_extra_pool = [Comment, Triple]
    all_quotes = '"', "'", '"""', "'''"
    if fstring_prefixes:
        pseudo_extra_pool.append(FStringStart + group(*all_quotes))

    PseudoExtras = group(r'\\(?:\r\n?|\n)|\Z', *pseudo_extra_pool)
    PseudoToken = group(Whitespace, capture=True) + \
        group(PseudoExtras, Number, Funny, ContStr, Name, capture=True)

    # For a given string prefix plus quotes, endpats maps it to a regex
    #  to match the remainder of that string. _prefix can be empty, for
    #  a normal single or triple quoted string (with no prefix).
    endpats = {}
    for _prefix in possible_prefixes:
        endpats[_prefix + "'"] = _compile(Single)
        endpats[_prefix + '"'] = _compile(Double)
        endpats[_prefix + "'''"] = _compile(Single3)
        endpats[_prefix + '"""'] = _compile(Double3)

    # A set of all of the single and triple quoted string prefixes,
    #  including the opening quotes.
    single_quoted = set()
    triple_quoted = set()
    fstring_pattern_map = {}
    for t in possible_prefixes:
        for quote in '"', "'":
            single_quoted.add(t + quote)

        for quote in '"""', "'''":
            triple_quoted.add(t + quote)

    for t in fstring_prefixes:
        for quote in all_quotes:
            fstring_pattern_map[t + quote] = quote

    # TODO: extend ALWAYS_BREAK_TOKENS
    ALWAYS_BREAK_TOKENS = (
        ';', 'import', 'class', 'def', 'try', 'except',
        'finally', 'while', 'with', 'return', 'continue',
        'break', 'del', 'pass', 'global', 'assert', 'nonlocal',
        'cdef', 'ctypedef',
    )
    pseudo_token_compiled = _compile(PseudoToken)
    return TokenCollection(
        pseudo_token_compiled, single_quoted, triple_quoted, endpats,
        whitespace, fstring_pattern_map, set(ALWAYS_BREAK_TOKENS)
    )


# Monkey patching _create_token_collection
parso.python.tokenize._create_token_collection = _create_token_collection


if __name__ == "__main__":
    path = sys.argv[1]
    with open(path) as f:
        code = f.read()

    for token in tokenize(code, version_info=parse_version_string('3.10')):
        print(token)
