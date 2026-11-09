"""Notebook cells of stage 0: libraries, the study period and the data locations.

Names used from earlier stages: none.
"""

from __future__ import annotations

import nbformat

from .common import code, md

CELLS: list[nbformat.NotebookNode] = [
    md(
        """
## 0. 準備

### この段階の内容

- ライブラリを読み込み、研究の期間（49か月）を固定する。
- データの場所をノートブックに伝える。
- 49か月分のデータと4年分のパネルがそろっているかを確かめる。

### 環境変数

Jupyter を起動する前に、次を設定する（括弧内は既定値）。

- `D1_DATA_ROOT`：Lichess_BotDataCollection のデータのフォルダ（`<repo>/data`）
- `D1_INTERIM_DIR`：月ごとのフォルダと `census-panel`（`<D1_DATA_ROOT>/interim`）
- `D1_BOT_ACCOUNTS`：ボットのアカウントの一覧 `bot_accounts.parquet`（`<D1_DATA_ROOT>/external/bot_accounts.parquet`）
- `D1_RESULTS_DIR`：表、図、保存したモデルの推定結果の出力先（`<repo>/results`）
- `D1_REFRESH`：`1` にすると、保存済みの結果を読まず、すべてのモデルを推定し直す

### 保存した推定結果

- モデルの推定結果は、計算した直後に `results/cache/` に保存され、次回からはそれを読み込む（下の関数 `cached()`）。
- すべて推定し直すと、月ごとの分析に約10分、パネルに10〜30分と数GBのメモリを要する。

### 出力の読み方

- `missing: none` と `panel present: True` が出ていれば、必要なデータはすべてそろっている。
- 後で別の実行と比較できるように、パッケージのバージョンも表示する。
""",
    ),
    code(
        r'''
import json
import math
import os
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from functools import cache
from importlib.metadata import version
from typing import Any

import numpy as np
import pandas as pd
import patsy
import polars as pl
import statsmodels.api as sm
from IPython.display import Image, Markdown, display
from matplotlib.axes import Axes
from scipy import optimize, stats

from lichess_d1 import config
from lichess_d1.plotting import NEUTRAL, SERIES, new_figure, save_figure

pl.Config.set_tbl_rows(60)
pl.Config.set_tbl_cols(20)

# study period (2026-09 is held out for a pre-registered test)
FIRST_MONTH, LAST_MONTH = "2022-08", "2026-08"


def month_range(first: str, last: str) -> Iterator[str]:
    """Yields YYYY-MM months from first to last inclusive."""
    year, month = (int(p) for p in first.split("-"))
    while f"{year:04d}-{month:02d}" <= last:
        yield f"{year:04d}-{month:02d}"
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


STUDY_MONTHS = tuple(month_range(FIRST_MONTH, LAST_MONTH))

REFRESH = os.environ.get("D1_REFRESH") == "1"
CACHE_DIR = config.RESULTS_DIR / "cache"
FIGURE_DIR = config.RESULTS_DIR / "figures"


def json_default(value: object) -> object:
    """Turns numpy scalars into Python numbers for JSON."""
    return value.item() if hasattr(value, "item") else str(value)


def cached(name: str, compute: Callable[[], Any]) -> Any:
    """The saved result `name` from results/cache; computed and saved first when missing."""
    path = CACHE_DIR / f"{name}.json"
    if REFRESH or not path.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(compute(), default=json_default), encoding="utf-8")
    # read back in both cases, so that fresh and saved results are the same Python objects
    return json.loads(path.read_text(encoding="utf-8"))


assert len(STUDY_MONTHS) == 49
print("checks passed")
''',
        self_contained=True,
    ),
    code(
        r"""
print("interim folder:", config.INTERIM_DIR)
print("bot accounts:  ", config.BOT_ACCOUNTS_PATH)
print("results:       ", config.RESULTS_DIR, "| refit everything:", REFRESH)
missing = [m for m in STUDY_MONTHS if not (config.month_dir(m) / "player_games.parquet").exists()]
print("study months:", len(STUDY_MONTHS), "| missing:", missing or "none")
print("panel present:", (config.month_dir(config.PANEL_NAME) / "player_games.parquet").exists())
for package in ("polars", "pandas", "numpy", "statsmodels", "scipy", "patsy"):
    print(f"{package} {version(package)}")
""",
    ),
]
"""The cells, in notebook order."""
