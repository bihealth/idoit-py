"""Implementation of ``idoit-cli create`` command.

Create entries.
"""

import argparse
import json

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import Terminal256Formatter

from .api import Client

#: Further arguments for servers.
VIRTUAL_SERVER_ARGS = {"title": None}

#: Virtual machine args.
VIRTUAL_HOST_ARGS = {"title": None}

#: Available object types.
TYPES = {"virtual_servers": VIRTUAL_SERVER_ARGS, "virtual_host": VIRTUAL_HOST_ARGS}


def setup_argparse(parser: argparse.ArgumentParser) -> None:
    """Main entry point for subcommand."""
    parser.add_argument("command", nargs="+", help="Command line.")


def run(args, parser, subparser):
    """Main entry point for constants command."""
    with Client(args.idoit_url, args.idoit_user, args.idoit_password, args.idoit_api_key) as client:
        res = client.query(
            "cmdb.object.create",
            params={"type": "C__OBJTYPE__VIRTUAL_SERVER", "title": args.command[1]},
        )
        print(highlight(json.dumps(res, indent=2), PythonLexer(), Terminal256Formatter()))
