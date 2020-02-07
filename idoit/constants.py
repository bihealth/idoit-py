"""Implementation of ``idoit-cli constants`` command.

Lists the constants.
"""

import argparse
import json

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import Terminal256Formatter

from .api import Client


def setup_argparse(_parser: argparse.ArgumentParser) -> None:
    """Main entry point for subcommand."""


def run(args, parser, subparser):
    """Main entry point for constants command."""
    with Client(args.idoit_url, args.idoit_user, args.idoit_password, args.idoit_api_key) as client:
        constants = client.query("idoit.constants")
    print(highlight(json.dumps(constants, indent=2), PythonLexer(), Terminal256Formatter()))
