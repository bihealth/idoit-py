"""Implementation of ``idoit-cli constants`` command.

Lists the constants.
"""

import argparse

from .api import Client
from .common import pprint


def setup_argparse(_parser: argparse.ArgumentParser) -> None:
    """Main entry point for subcommand."""


def run(args, parser, subparser):
    """Main entry point for constants command."""
    with Client(args.idoit_url, args.idoit_user, args.idoit_password, args.idoit_api_key) as client:
        constants = client.query("idoit.constants")
    pprint(constants)
