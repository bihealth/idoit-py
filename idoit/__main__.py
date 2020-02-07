"""Main entry point for i-doit CLI in Python3."""

import argparse
import logging
import os
import sys

import logzero
from logzero import logger

from idoit import __version__
from .common import run_nocmd
from .check import setup_argparse as setup_argparse_check
from .check import run as run_check


def setup_argparse_only():  # pragma: nocover
    """Wrapper for ``setup_argparse()`` that only returns the parser.

    Only used in sphinx documentation via ``sphinx-argparse``.
    """
    return setup_argparse()[0]


def setup_argparse():
    """Create argument parser."""
    # Construct argument parser and set global options.
    parser = argparse.ArgumentParser(prog="idoit-py")
    parser.add_argument("--verbose", action="store_true", default=False, help="Increase verbosity.")
    parser.add_argument("--version", action="version", version="%%(prog)s %s" % __version__)

    parser.add_argument(
        "--idoit-user", default=os.environ.get("IDOIT_USER"), help="Name of account to use"
    )
    parser.add_argument(
        "--idoit-password",
        default=os.environ.get("IDOIT_PASSWORD"),
        help="Password of account to use",
    )
    parser.add_argument(
        "--idoit-url",
        default=os.environ.get("IDOIT_URL"),
        help="URL to i-doit instance, defaults to value of IDOIT_URL environment variable",
    )
    parser.add_argument(
        "--idoit-api-key",
        default=os.environ.get("IDOIT_API_KEY"),
        help="i-doit API key, defaults to value of IDOIT_API_KEY environment variable",
    )

    # Add sub parsers for each argument.
    subparsers = parser.add_subparsers(dest="cmd")

    setup_argparse_check(subparsers.add_parser("check", help="check description."))

    return parser, subparsers


def main(argv=None):
    """Main entry point before parsing command line arguments."""
    # Setup command line parser.
    parser, subparsers = setup_argparse()

    # Actually parse command line arguments.
    args = parser.parse_args(argv)

    # Check API key.
    ok = True
    for key in ("idoit_user", "idoit_password", "idoit_url", "idoit_api_key"):
        if not getattr(args, key):
            logger.error(
                "i-doit %s not set, either user %s or set %s environment variable",
                key.replace("_", " "),
                "--" + key.replace("_", "-"),
                key.upper(),
            )
            ok = False
    if not ok:
        return parser.exit(1, "There was a configuration problem.")

    # Setup logging verbosity.
    if args.verbose:  # pragma: no cover
        level = logging.DEBUG
    else:
        level = logging.INFO
    logzero.loglevel(level=level)

    # Handle the actual command line.
    cmds = {None: run_nocmd, "check": run_check}

    res = cmds[args.cmd](args, parser, subparsers.choices[args.cmd] if args.cmd else None)
    if not res:
        logger.info("All done. Have a nice day!")
    else:  # pragma: nocover
        logger.error("Something did not work out correctly.")
    return res


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv))
