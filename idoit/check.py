"""Implementation of ``idoit-cli check`` command.

This checks the general connectivity to the server.
"""

import argparse

from logzero import logger

from .api import Client


def setup_argparse(_parser: argparse.ArgumentParser) -> None:
    """Main entry point for subcommand."""


def run(args, parser, subparser):
    """Main entry point for check command."""
    with Client(args.idoit_url, args.idoit_user, args.idoit_password, args.idoit_api_key) as client:
        version = client.query_version()
    logger.info("OK, server version is %s", version)
