"""Writes notebooks/D1_reproduction.ipynb (markdown text in Japanese only; code and outputs in English).

The notebook holds every line of the analysis so that it can be audited on its own; the
package keeps only the data locations and the plotting style. Its cells live in
``scripts/cells/``: ``overview.py``, one module per stage in ``stages.yaml`` order, and
``references.py``. Run ``uv run python scripts/build_notebook.py`` and then execute the
notebook (``uv run python scripts/build_notebook.py --execute`` does both).
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from stage_list import load_stages

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "D1_reproduction.ipynb"
SCRIPTS = ROOT / "scripts"


def module_name(module_path: str) -> str:
    """The import name of a cell module given by its path, e.g. ``cells.stage_2``."""
    relative = (ROOT / module_path).relative_to(SCRIPTS).with_suffix("")
    return ".".join(relative.parts)


def collect_cells() -> list[nbformat.NotebookNode]:
    """Every cell of the notebook: the overview, each stage, then the references."""
    stages = [module_name(stage.module) for stage in load_stages(ROOT)]
    names = ["cells.overview", *stages, "cells.references"]
    cells: list[nbformat.NotebookNode] = []
    for name in names:
        cells += importlib.import_module(name).CELLS
    return cells


def build(execute: bool) -> Path:
    """Writes the notebook, optionally executing it in place."""
    notebook = nbformat.v4.new_notebook()
    notebook.cells = collect_cells()
    notebook.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    if execute:
        NotebookClient(
            notebook, timeout=7200, resources={"metadata": {"path": str(ROOT)}}
        ).execute()
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, NOTEBOOK)
    return NOTEBOOK


def main() -> None:
    """Parses arguments and writes the notebook."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="run every cell before saving")
    print(build(parser.parse_args().execute))


if __name__ == "__main__":
    main()
