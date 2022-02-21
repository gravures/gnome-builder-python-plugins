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

Loads a python sources file, parse it as an ast.Module
and write back pickled bytes of this ast tree to a file.
The name of this file is printed to stdout.
The call process should open as bytes the file path
read on stdout, and upickled the data read to
reconstruct the ast tree. It's the responsability
of the call process to remove te generated file on disk.
In case of errors, stdout will be empty, errors will
be logged on stderr, and the script will exit with
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
import tempfile
from pathlib import Path

logger = logging.getLogger("sources_inspect.py")
logger.setLevel(level=logging.INFO)
handler = logging.StreamHandler(stream=sys.stderr)
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)-8s: %(name)-12s -> %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def import_source(path: Path) -> ast.AST:
    """Return the python file located at 'path' as
    an ast.AST tree root node.
    """
    with open(path, encoding='utf-8', mode='r') as file:
        source = file.read()
    return ast.parse(source)


def pickle_ast(node: ast.AST) -> bytes:
    """Pickle dump as bytes node instance."""
    return pickle.dumps(node, protocol=pickle.HIGHEST_PROTOCOL)


def main():  # noqa
    try:
        path = Path(sys.argv[1])
        if path.is_file():
            ast_tree = import_source(path)
            result = pickle_ast(ast_tree)
        else:
            logger.info(f"Not a valide filename {path}.")
            sys.exit(1)
    except IndexError:
        logger.info("Need a filename as positional argument.")
        sys.exit(1)
    except (ValueError, IOError) as err:
        logger.info(f"Can't read file {sys.argv[1]} as source code:\n{err}")
        sys.exit(1)
    except pickle.PickleError as err:
        logger.info(f"PICKLE ERROR: {err}")
        sys.exit(1)
    except Exception as err:
        logger.info(f"UNDEFINED ERROR: {err}")
        sys.exit(1)
    else:
        try:
            tmpdir = Path(tempfile.gettempdir())
            _dir = tmpdir / "_pickled"
            _dir.mkdir(parents=True, exist_ok=True)
            file_path = _dir / f"_PY_{id(result)}.pickle"
            with open(file_path, mode='wb') as file:
                file.write(result)
            sys.stdout.write(str(file_path))
        except OSError as err:
            logger.info(f"OUTPUT ERROR: {err}")
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()
