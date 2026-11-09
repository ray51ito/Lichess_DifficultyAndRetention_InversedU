"""Command-line entry point (``d1 run``): executes the reproduction notebook in place."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

import nbformat
from nbclient import NotebookClient

from lichess_d1 import config

TIMEOUT_S: int = 7200
"""Longest time one notebook cell may run (the panel fits take up to 30 minutes)."""


def _cmd_run(args: argparse.Namespace) -> None:
    if args.refresh:
        # the kernel inherits this process's environment
        os.environ["D1_REFRESH"] = "1"
    notebook = nbformat.read(config.NOTEBOOK_PATH, as_version=4)  # type: ignore[no-untyped-call]
    client = NotebookClient(
        notebook, timeout=TIMEOUT_S, resources={"metadata": {"path": str(config.PROJECT_ROOT)}}
    )
    client.execute()
    nbformat.write(notebook, config.NOTEBOOK_PATH)  # type: ignore[no-untyped-call]
    print(f"executed {config.NOTEBOOK_PATH}; outputs are in {config.RESULTS_DIR}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="d1", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="execute the notebook: every fit, table, figure and check")
    run.add_argument("--refresh", action="store_true", help="refit instead of reading saved fits")
    run.set_defaults(func=_cmd_run)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Parses arguments and runs the selected command."""
    args = _build_parser().parse_args(argv)
    args.func(args)
