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
"""sources_inspect.py

Analyze python sources file and return a hierarchical
representation of the code with its functions, class
and class methods definitions. The result is a json
formatted string printed on stdout.
In case of errors, stdout will be empty, errors will
be printed on stderr, and the script will exit with
a status code of 1.
Warning: It is possible to crash the Python
interpreter with a sufficiently large/complex string
due to stack depth limitations in Python’s AST compiler.
Be prepare to this with your calling process.
"""

import ast
import logging
import pickle
import sys
from collections import OrderedDict
from pathlib import Path
from typing import OrderedDict as OrderedDict_T
import tempfile

logger = logging.getLogger("sources_inspect.py")
logger.setLevel(level=logging.INFO)
handler = logging.FileHandler("/home/gilles/PYTHON.log")
formatter = logging.Formatter("%(asctime)s - %(levelname)-8s: %(name)-12s -> %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.info(f"module {__file__} imported...")

def import_source(path: Path) -> ast.AST:
    """Return the python file located at 'path' as
    an ast.AST tree root node.
    """
    with open(path, encoding='utf-8', mode='r') as file:
        # major = 3
        # minor = 9
        source = file.read()
        # tree = ast.parse(
        #     source,
        #     filename="<string>",
        #     mode="eval",
        #     feature_version=(major, minor),
        #     type_comments=False
        # )
    return ast.parse(source)


def parse(ast_tree: ast.AST) -> OrderedDict_T[str, OrderedDict_T]:
    """Visit the root ast tree recursivly and return
    a tree as an OrderedDict of pertinent code object
    elements.
    """
    root = OrderedDict()
    ast.fix_missing_locations(ast_tree)
    for node in ast.iter_child_nodes(ast_tree):
        visit_node(node, root)
    return root


def visit_node(node: ast.AST, parent: OrderedDict_T) -> None:
    """Visit the ast 'node' and fill the 'parent' OrderedDict
    with the node name as key if the type of node is
    of interest(function, class, etc...). Call recursivly
    on node child until reaching end of tree.
    """
    childs = None
    lineno = node.lineno if hasattr(node, "lineno") else "__"
    col_offset = node.col_offset if hasattr(node, "col_offset") else "__"
    logger.info(f"{lineno}:{col_offset} {ast.dump(node)}\n")
    if isinstance(node, ast.FunctionDef):
        parent[node.name] = {"type": "FunctionDef", "childs": {}}
        childs = parent[node.name]["childs"]
    elif isinstance(node, ast.ClassDef):
        parent[node.name] = {"type": "ClassDef", "childs": {}}
        childs = parent[node.name]["childs"]
    if childs is not None:
        for node in ast.iter_child_nodes(node):
            visit_node(node, childs)


def pickle_ast(node: ast.AST) -> bytes:
    return pickle.dumps(node, protocol=pickle.HIGHEST_PROTOCOL)


def main():  # noqa
    try:
        path = Path(sys.argv[1])
        logger.info(f"running {__file__}...{sys.argv[1]}")
        if path.is_file():
            ast_tree = import_source(path)
            # result = parse(ast_tree)
            logger.debug(ast.dump(ast_tree))
            result = pickle_ast(ast_tree)
        else:
            logger.info(
                f"Not a valide filename {path}.",
                file=sys.stderr
            )
            sys.exit(1)
    except IndexError:
        logger.info(
            "Need a filename as positional argument.",
            file=sys.stderr
        )
        sys.exit(1)
    except (ValueError, IOError) as err:
        logger.info(
            f"Can't read file {sys.argv[1]} as source code:\n{err}",
            file=sys.stderr
        )
        sys.exit(1)
    except pickle.PickleError as err:
        logger.info(f"PICKLE ERROR: {err}")
        sys.exit(1)
    except Exception as err:
        logger.info(f"UNDEFINED ERROR: {err}")
        sys.exit(1)
    else:
        # stdout = json.dumps(result)
        # print(stdout, file=sys.stdout)
        try:
            tmpdir = tempfile.gettempdir()
            tmpdir = "/home/gilles/.tmp"
            file_path = Path(tmpdir) / f"_PY_{id(result)}.pickle"
            logger.info(f"write python object to: {file_path}")
            with open(file_path, mode='wb') as file:
                file.write(result)
            sys.stdout.write(str(file_path))
            # sys.stdout.buffer.write(result)
        except OSError as err:
            logger.info(f"OUTPUT ERROR: {err}")
            sys.exit(1)
        logger.info("sources_inspect exit with success")
        sys.exit(0)


if __name__ == "__main__":
    main()
