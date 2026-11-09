"""Notebook cells of stage 4: the check of every number printed in the paper.

Names used from earlier stages:
    stage 0: Any, Markdown, config, display, json, json_default, math, pl, re
    stage 2: binned, horizons, n_session_ends_7d, panel_size, shape_tests, spec_columns,
        spec_key
    stage 3: ALL_SPECS, FLEX_LABELS, flexible, flexible_fits, main_pairs, mirror
"""

from __future__ import annotations

import nbformat

from .common import code, md

CELLS: list[nbformat.NotebookNode] = [
    md(
        """
## 4. 論文のすべての数値の照合

### 問い

論文に書いたすべての数値を、このコードから再現できるか。

### 数値を集める

最初のセルは、段階2・3の結果を1つの辞書 `summary` にまとめ、次を書き出す。

- `summary`（`results/summary.json`）。段階3の結果は `summary["shape"]` にある。
- そのもとになる表（`results/*.csv`。段階3の表は `results/shape_*.csv`）

ここで、次の2つの数値を導く。

- 段階2の曲線の項の p 値のうち、最大のもの。
- 段階2のプレイヤー内の曲線で、es = 0.10 から頂点まで動いたときの、7日再訪の増分。

### 照合

`expected/paper_values.json` に、論文に書いたとおりの数値と、それが `summary` のどこにあるかを並べてある。
次のいずれかを満たせば、再現できたとみなす。

- 計算し直した値を同じ桁数に丸めた値が一致する（`kind` = `round`）。
- 論文に書いた上限を満たす（例えば「p < 0.001」。`kind` = `below`）。
- 論文に書いた下限に達する（例えば「有意でない」を p ≥ 0.05 とする場合。`kind` = `at_least`）。

### 出力の読み方

- 太字の行：再現できた数値の数。
- 最初の表：一致*しなかった*数値の一覧。空であるべきである。
- 2つ目の表：すべての数値の一覧。`results/comparison.csv` にも保存する。
  - `section`、`what`：どの箇所の何の数値か。
  - `paper`：論文の値。`reproduced`：計算し直した値。
  - `matches`：判定結果。`error`：計算できなかったときの理由。
""",
    ),
    code(
        r'''
week = next(
    r for r in horizons if (r["target"], r["days"], r["within"]) == ("same bot", 7, "player")
)
top = week["peak_es"]
any_week = next(
    r for r in horizons if (r["target"], r["days"], r["within"]) == ("any bot", 7, "player")
)


def flexible_bin(es_bin: str, with_result: bool) -> float:
    """The Binscatter's estimate in one bin."""
    return next(
        r["estimate"] for r in flexible if r["es_bin"] == es_bin and r["with_result"] == with_result
    )


def raw_drop_from_peak(bins: pl.DataFrame, min_sessions: int = 100) -> dict[str, float]:
    """Drop of the raw return rate from its highest bin to the hardest and the easiest bin."""
    shown = bins.filter(pl.col("n") >= min_sessions).sort("es_mid")
    rate = shown["rate"]
    return {"hard_end": float(rate.max() - rate[0]), "easy_end": float(rate.max() - rate[-1])}


summary = {
    "panel": {
        "describe": panel_size,
        "n_session_ends_7d": n_session_ends_7d,
        "horizons": horizons,
        "flexible": flexible,
        "two_lines": shape_tests,
        "two_lines_n_inverted_u": sum(
            r["u_shape"] and r["shape"] == "inverted U" for r in shape_tests if r["with_result"]
        ),
        # the ten two-lines tests, including the 7-day model without the result
        "two_lines_n_inverted_u_all": sum(
            r["u_shape"] and r["shape"] == "inverted U" for r in shape_tests
        ),
        "two_lines_max_p": max(max(r["slope_hard_p"], r["slope_easy_p"]) for r in shape_tests),
        # raw 7-day return (figure 1): drop from the highest bin to each end bin
        "raw_drop_from_peak": raw_drop_from_peak(binned),
        "horizons_max_p": max(max(r["es_p"], r["es2_p"]) for r in horizons),
        # 7-day return gained from es = 0.10 to the peak on the within-player curve
        "gain_beginner_to_peak": week["es"] * (top - 0.10) + week["es2"] * (top**2 - 0.10**2),
        # any-bot curvature as a share of the same-bot curvature (7 days, within player)
        "any_bot_curvature_share": any_week["es2"] / week["es2"],
        # drop in the hardest bin (es 0-0.025) over the drop in the easiest bin (es 0.975-1)
        "flexible_asymmetry": {
            name: flexible_bin(FLEX_LABELS[0], with_result)
            / flexible_bin(FLEX_LABELS[-1], with_result)
            for name, with_result in (("result_free", False), ("result_fixed", True))
        },
    },
}

# stage 3: the asymmetry of the curve
summary["shape"] = {
    "flexible": [
        {**spec_columns(spec), **row} for spec in ALL_SPECS
        for row in flexible_fits[spec_key(spec)]["bins"]
    ],
    "mirror": mirror,
    "mirror_pairs": main_pairs,
}

out_dir = config.RESULTS_DIR
binned.write_csv(out_dir / "return_by_es_bin.csv")
for key in ("horizons", "flexible", "two_lines"):
    pl.DataFrame(summary["panel"][key]).write_csv(out_dir / f"panel_{key}.csv")
for key, rows in summary["shape"].items():
    pl.DataFrame(rows, infer_schema_length=None).write_csv(out_dir / f"shape_{key}.csv")
(out_dir / "summary.json").write_text(
    json.dumps(summary, indent=2, default=json_default), encoding="utf-8", newline="\n"
)
print("written to", out_dir)
''',
    ),
    code(
        r'''
def resolve(tree: dict[str, Any], path: str) -> Any:
    """Follows a dot path; `name[key=value,...]` picks the one list item whose fields match.

    A comma starts a new `key=value` only when an `=` follows it, so values may hold commas.
    """
    node: Any = tree
    # split on the dots outside brackets, so selector values may hold decimals
    for part in re.split(r"\.(?![^\[]*\])", path):
        name, _, selector = part.partition("[")
        node = node[name] if name else node
        if selector:
            fields = re.split(r",(?=[^,=]*=)", selector.rstrip("]"))
            wanted = dict(kv.split("=", 1) for kv in fields)
            matches = [item for item in node if all(str(item[k]) == v for k, v in wanted.items())]
            if len(matches) != 1:
                raise KeyError(f"{part}: {len(matches)} matches")
            node = matches[0]
    return node


def agrees(value: float, item: dict[str, Any]) -> bool:
    """Whether a recomputed value agrees with the printed one (see `kind` above)."""
    kind, printed = item.get("kind", "round"), float(item["paper"])
    if kind == "below":
        return value < printed
    if kind == "at_least":
        return value >= printed
    decimals = int(item["decimals"])
    return math.isclose(round(value, decimals), printed, abs_tol=10 ** -(decimals + 3))


def compare(tree: dict[str, Any], expected: dict[str, Any]) -> pl.DataFrame:
    """One row per printed number: printed value, recomputed value, and whether they agree."""
    rows = []
    for item in expected["values"]:
        row = {
            "section": item["section"], "what": item["what"], "paper": float(item["paper"]),
            "kind": item.get("kind", "round"),
        }
        try:
            value = float(resolve(tree, item["path"])) * float(item.get("scale", 1.0))
        except (KeyError, TypeError, ValueError) as exc:
            rows.append({**row, "reproduced": math.nan, "matches": False, "error": str(exc)})
            continue
        rows.append({**row, "reproduced": value, "matches": agrees(value, item), "error": ""})
    return pl.DataFrame(rows)


made_up = {"a": {"b": [{"days": 7, "x": 0.1234}, {"days": 28, "x": 9.0}]}}
assert resolve(made_up, "a.b[days=7].x") == 0.1234
assert resolve({"a": [{"bin": "0.025", "x": 1.0}]}, "a[bin=0.025].x") == 1.0
assert resolve({"a": [{"k": "p, q", "j": 1, "x": 2.0}]}, "a[k=p, q,j=1].x") == 2.0
assert compare(made_up, {"values": [
    {"section": "s", "what": "w", "path": "a.b[days=7].x", "paper": 0.12, "decimals": 2},
    {"section": "s", "what": "w", "path": "a.b[days=7].x", "paper": 0.1, "kind": "below"},
    {"section": "s", "what": "w", "path": "a.missing", "paper": 1.0, "decimals": 0},
]})["matches"].to_list() == [True, False, False]
print("checks passed")
''',
        self_contained=True,
    ),
    code(
        r"""
table = compare(summary, json.loads(config.EXPECTED_PATH.read_text(encoding="utf-8")))
table.write_csv(config.RESULTS_DIR / "comparison.csv")
n_matched = int(table["matches"].sum())
display(Markdown(f"**{n_matched} of {table.height} numbers in the paper reproduced.**"))
display(table.filter(~pl.col("matches")))
table
""",
    ),
]
"""The cells, in notebook order."""
