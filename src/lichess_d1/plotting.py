"""Shared matplotlib style: validated categorical palette, recessive axes, figure saving."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

SERIES: tuple[str, ...] = (
    "#2a78d6",
    "#eb6834",
    "#1baf7a",
    "#eda100",
    "#e87ba4",
    "#008300",
    "#4a3aa7",
    "#e34948",
)
"""Categorical colours in fixed order (CVD-validated reference palette, light mode)."""

SURFACE: str = "#fcfcfb"
"""Figure background."""

TEXT_PRIMARY: str = "#0b0b0b"
"""Primary ink for titles and values."""

TEXT_SECONDARY: str = "#52514e"
"""Secondary ink for axes, ticks and annotations."""

GRID: str = "#e4e3df"
"""Recessive grid colour."""

NEUTRAL: str = "#8a8984"
"""Neutral reference-line colour."""

FONTS: tuple[str, ...] = (
    "Yu Gothic",
    "Meiryo",
    "BIZ UDPGothic",
    "Noto Sans CJK JP",
    "IPAexGothic",
    "DejaVu Sans",
)
"""Sans-serif fonts in order of preference; the first ones cover Japanese text."""


def apply_style() -> None:
    """Applies the project-wide matplotlib rcParams."""
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": list(FONTS),
            "axes.unicode_minus": False,
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "axes.edgecolor": GRID,
            "axes.labelcolor": TEXT_SECONDARY,
            "axes.titlecolor": TEXT_PRIMARY,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.labelsize": 9,
            "axes.grid": True,
            "axes.axisbelow": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "xtick.color": TEXT_SECONDARY,
            "ytick.color": TEXT_SECONDARY,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.frameon": False,
            "legend.fontsize": 8,
            "legend.labelcolor": TEXT_SECONDARY,
            "lines.linewidth": 2.0,
            "lines.markersize": 5,
            "figure.dpi": 110,
        }
    )


def new_figure(
    n_cols: int = 1, width: float = 6.4, height: float = 3.8, *, n_rows: int = 1
) -> tuple[Figure, list[Axes]]:
    """Creates a figure with ``n_rows`` x ``n_cols`` axes, listed row by row."""
    apply_style()
    fig, axes = plt.subplots(
        n_rows, n_cols, figsize=(width * n_cols, height * n_rows), squeeze=False
    )
    return fig, list(axes.flat)


def save_figure(fig: Figure, path: Path) -> Path:
    """Saves a figure as PNG and closes it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
