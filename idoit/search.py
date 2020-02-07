"""Implementation of ``idoit-cli search`` command.

Lists the constants.
"""

import argparse
import json

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import Terminal256Formatter

from .api import Client


def setup_argparse(parser: argparse.ArgumentParser) -> None:
    """Main entry point for subcommand."""

    parser.add_argument("terms", nargs="+", help="Search term(s)")


def run(args, parser, subparser):
    """Main entry point for constants command."""
    with Client(args.idoit_url, args.idoit_user, args.idoit_password, args.idoit_api_key) as client:
        result = client.query("idoit.search", params={"q": " ".join(args.terms)})
    print(highlight(json.dumps(result, indent=2), PythonLexer(), Terminal256Formatter()))
