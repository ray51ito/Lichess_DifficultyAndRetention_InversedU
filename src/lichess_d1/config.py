"""Data locations of the reproduction; the study design and every analysis live in the notebook."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
"""Repository root directory."""

NOTEBOOK_PATH: Path = PROJECT_ROOT / "notebooks" / "D1_reproduction.ipynb"
"""The reproduction notebook, which holds all of the analysis code."""

DATA_ROOT: Path = Path(os.environ.get("D1_DATA_ROOT", PROJECT_ROOT / "data"))
"""Data root written by Lichess_BotDataCollection (``D1_DATA_ROOT`` overrides)."""

INTERIM_DIR: Path = Path(os.environ.get("D1_INTERIM_DIR", DATA_ROOT / "interim"))
"""One folder per month plus ``census-panel`` (``D1_INTERIM_DIR`` overrides)."""

BOT_ACCOUNTS_PATH: Path = Path(
    os.environ.get("D1_BOT_ACCOUNTS", DATA_ROOT / "external" / "bot_accounts.parquet")
)
"""Known bot accounts, incl. those shown without the BOT title (``D1_BOT_ACCOUNTS`` overrides)."""

RESULTS_DIR: Path = Path(os.environ.get("D1_RESULTS_DIR", PROJECT_ROOT / "results"))
"""Reproduced tables and figures (``D1_RESULTS_DIR`` overrides)."""

EXPECTED_PATH: Path = PROJECT_ROOT / "expected" / "paper_values.json"
"""Numbers stated in the paper, checked against the reproduction."""

PANEL_NAME: str = "census-panel"
"""Interim folder of the stacked four-year panel."""


def month_dir(month: str) -> Path:
    """Folder of one month's tables (or of the panel)."""
    return INTERIM_DIR / month
