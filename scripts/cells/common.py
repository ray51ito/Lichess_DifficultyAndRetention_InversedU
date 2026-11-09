"""Cell constructors shared by every cell module of the notebook."""

from __future__ import annotations

import nbformat

SELF_CONTAINED: str = "self-contained"
"""Tag of code cells that need no data (definitions and their checks); the tests run them."""


def md(text: str) -> nbformat.NotebookNode:
    """A markdown cell holding the Japanese text."""
    return nbformat.v4.new_markdown_cell(text.strip())


def code(source: str, *, self_contained: bool = False) -> nbformat.NotebookNode:
    """A code cell; ``self_contained`` marks cells that run without the data."""
    cell = nbformat.v4.new_code_cell(source.strip())
    if self_contained:
        cell.metadata["tags"] = [SELF_CONTAINED]
    return cell
