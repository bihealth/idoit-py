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
from .constants import setup_argparse as setup_argparse_constants
from .constants import run as run_constants
from .shell import setup_argparse as setup_argparse_shell
from .shell import run as run_shell
from .read import setup_argparse as setup_argparse_read
from .read import run as run_read
from .search import setup_argparse as setup_argparse_search
from .search import run as run_search


def setup_argparse_only():  # pragma: nocover
    """Wrapper for ``setup_argparse()`` that only returns the parser.

    Only used in sphinx documentation via ``sphinx-argparse``.
    """
    return setup_argparse()[0]


def setup_argparse():
    """shell argument parser."""
    # Construct argument parser and set global options.
    parser = argparse.ArgumentParser(prog="idoit-py")
    parser.add_argument("--quiet", action="store_true", default=False, help="Decreate verbosity.")
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

    setup_argparse_check(
        subparsers.add_parser("check", help="Check connectivity and print version.")
    )
    setup_argparse_constants(subparsers.add_parser("constants", help="Print i-doit constants."))
    setup_argparse_search(subparsers.add_parser("search", help="Search i-doit."))
    setup_argparse_shell(subparsers.add_parser("shell", help="Item creation."))
    setup_argparse_read(subparsers.add_parser("read", help="Item retrieval."))

    return parser, subparsers


def main(argv=None):
    """Main entry point before parsing command line arguments."""
    # Setup command line parser.
    parser, subparsers = setup_argparse()

    # Actually parse command line arguments.
    args = parser.parse_args(argv)

    # Setup logging verbosity.
    if args.quiet:  # pragma: no cover
        level = logging.WARN
    elif args.verbose:  # pragma: no cover
        level = logging.DEBUG
    #        import ishell; ishell.logger.setLevel(level)
    #        logging.basicConfig()
    #        logging.getLogger().setLevel(level)
    else:
        formatter = logzero.LogFormatter(
            fmt="%(color)s[%(levelname)1.1s %(asctime)s]%(end_color)s %(message)s"
        )
        logzero.formatter(formatter)
        level = logging.INFO
    logzero.loglevel(level=level)

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

    # Handle the actual command line.
    cmds = {
        None: run_nocmd,
        "check": run_check,
        "constants": run_constants,
        "search": run_search,
        "shell": run_shell,
        "read": run_read,
    }

    res = cmds[args.cmd](args, parser, subparsers.choices[args.cmd] if args.cmd else None)
    if not res:
        logger.info("All done. Have a nice day!")
    else:  # pragma: nocover
        logger.error("Something did not work out correctly.")
    return res


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv))
