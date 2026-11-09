"""Runs the notebook's self-contained cells (analysis functions and their checks) and checks the
saved comparison of every printed number."""

import nbformat
import polars as pl

from lichess_d1 import config

SELF_CONTAINED = "self-contained"


def test_self_contained_cells_run() -> None:
    notebook = nbformat.read(config.NOTEBOOK_PATH, as_version=4)  # type: ignore[no-untyped-call]
    cells = [
        cell
        for cell in notebook.cells
        if cell.cell_type == "code" and SELF_CONTAINED in cell.metadata.get("tags", [])
    ]
    assert cells, "the notebook has no self-contained cells"
    namespace: dict[str, object] = {}
    for index, cell in enumerate(cells):
        exec(compile(cell.source, f"<self-contained cell {index}>", "exec"), namespace)


def test_every_printed_number_reproduced() -> None:
    table = pl.read_csv(config.RESULTS_DIR / "comparison.csv")
    assert table.height > 0
    assert table["matches"].all(), table.filter(~pl.col("matches"))
