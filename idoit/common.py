"""Shared code."""

import json
import sys

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import Terminal256Formatter


def run_nocmd(_, parser, subparser=None):  # pragma: no cover
    """No command given, print help and ``exit(1)``."""
    if subparser:
        subparser.print_help()
        subparser.exit(1)
    else:
        parser.print_help()
        parser.exit(1)


def pprint(x, file=sys.stdout):
    if file.isatty():
        print(
            highlight(json.dumps(x, indent=2), PythonLexer(), Terminal256Formatter()),
            file=file,
            end="",
        )
    else:
        print(json.dumps(x, indent=2), file=file)
