"""Notebook cells of stage 3: the Binscatter and the asymmetry around an even game (Q3b).

Names used from earlier stages:
    stage 0: Any, Callable, FIGURE_DIR, Image, Markdown, NEUTRAL, SERIES, cached, display, math,
        new_figure, np, pd, pl, save_figure, stats
    stage 1: ANALYSIS_SPEEDS
    stage 2: ALPHA, CONTROLS, FRAME_COLUMNS, FREE_SPEC, MAIN_SPEC, MIN_RETURN_ROWS, ModelResult,
        OUTCOME_TERM, RETURN_WINDOWS_D, Z95, control_terms, find_spec, fit_fe_lpm, horizons,
        panel_games, spec_columns, spec_key, spec_label, to_model_frame, two_lines_specs
"""

from __future__ import annotations

import nbformat

from .common import code, md

CELLS: list[nbformat.NotebookNode] = [
    md(
        """
## 3. 左右差：互角から同じだけ離れたときの違い

### 問いと進め方

段階2で、再訪が期待スコアについて逆U字になることを確かめた。この段階では、互角から同じだけ離れたとき、難しい側と易しい側のどちらで再訪が大きく下がるかを調べる。2次式は頂点の左右で同じ形を仮定するので、左右の違いは測れない。そこで、形を仮定しない Binscatter を使う。使うのは段階2のモデルだけで、新しい標本、新しい結果の変数、プレイヤーのグループどうしの比較は加えない。

問いは次の1つである。

- Q3b：互角から同じだけ離れたとき、難しい側と易しい側のどちらで再訪が大きく下がるか（非対称性）。

次の順に答える。

- 3.1：Binscatter を定め、主なモデル（結果を統制する場合としない場合）に当てはめて、両端の低下を見る。続けて、2.3の9本のモデルと結果を統制しない7日のモデルの計10本に広げ、ビンどうしの共分散を保存する（Q3b の土台）。
- 3.2：鏡像差の検定で、互角から同じだけ離れた難しい側と易しい側を比べる（Q3b）。

この段階の向きの約束：es では小さい側（左）が難しい側である。
""",
    ),
    md(
        r"""
### 3.1 Binscatter

互角の対局の後と比べて、難しい側と易しい側で再訪がどれだけ下がるかを、2次式を仮定せずに見る。

- **Binscatter**：$b\,\mathrm{es} + c\,\mathrm{es}^2$ の代わりに、es を21のビン（区切り）に分け、ビンごとのダミーを入れたモデルである。名称は Cattaneo et al. (2024) に従う。
  - ビンは0, 0.05, …, 1を中央とする幅0.05の区切りで、境目は0.025, 0.075, …, 0.975である（各ビンは左端を含み右端を含まない）。es は0〜1に収まるので、両端のビン（0〜0.025と0.975〜1）だけは幅が半分になる。
  - 基準は互角（es = 0.5）を中央に持つ0.475〜0.525のビンで、各ビンの係数は「基準ビンと比べて、再訪が何ポイント違うか」を表す。0.5を中央に置くことで、ビンは基準を挟んで左右対称に並ぶ。
  - このモデルの曲線は、ビンの中では一定で、ビンの境目で跳ぶ**階段関数**である（James et al., 2021, 7章）。2次式のような形を仮定しない代わりに、ビンの中での変化は表せない。
  - 図では、ビンごとの推定値を点で示し、点を線で結ぶ。この線は見やすくするためだけのもので、ビンの間の値を推定したものではない。
  - 統制変数は、プレイヤーの固定効果も含めて、ビンのダミーと同じ最小二乗法で一緒に推定する。Cattaneo et al. (2024) は、この推定を共変量で調整した Binscatter と呼ぶ。統制変数を先に取り除いてから再訪をビンごとに平均する方法では、曲線の形を誤りうる（Cattaneo et al., 2024）。
  - ビンの幅0.05は、データを見ずに決めた。Cattaneo et al. (2024) によれば、実務ではビンの数をデータと無関係に10か20とすることが多い。区切りの位置は、基準のビンが互角を中央に持つように選んだ。これは左右対称に比べるための設計上の理由によるもので、推定の結果を見て選んだものではない。
  - 固定効果のパネルで連続の変数をビンのダミーに置き換え、形を仮定せずに推定するのは、気温と死亡率の研究と同じ組み立てである（Deschênes & Greenstone, 2011）。
  - 連続の変数を区切ることへの批判は、検出力の損失、残った交絡、データから選んだ「最適な」区切りによる偏りに向けられている（Royston, Altman & Sauerbrei, 2006）。ここでの区切りは、互角を中央に置いた等間隔のビンである。Binscatter は左右の下がり方の記述と、3.2の検定の材料に使う。逆U字かどうかの判定（2.4）では、es を連続のまま扱う。
  - ビンの数を固定した推定は、各ビンの中の平均として読む。各ビンの95%区間は、そのビンの平均の不確かさを表すだけで、曲線全体の形についての推論には使えない（Cattaneo et al., 2024）。逆U字かどうかの主張は2.4の2直線の検定、左右の違いの主張は3.2の同時の Wald 検定による。
  - この曲線には、$\mathrm{draw}$ と $\mathrm{loss}$ を除いた（結果を統制しない）版もある。

#### Binscatter のコード

- `es_bin_column()`：es をビンに分ける式（ビンの名前は中央の値）。
- `flexible_data()`：7日以内の再訪が分かっている各セッションの終わりに、期待スコアのビンを付ける。
- `flexible_curve()`：es と es² の代わりに21のビンのダミーを入れた7日再訪のモデルを、`fit_fe_lpm()` で当てはめる（`fit_flexible()`）。基準は0.475〜0.525のビンである。対局の結果を統制する場合としない場合の両方を求める。
""",
    ),
    code(
        r'''
FLEX_EDGES = tuple(round(0.025 + 0.05 * i, 3) for i in range(20))  # 21 bins, width 0.05
FLEX_LABELS = tuple(f"{0.05 * i:.3f}" for i in range(len(FLEX_EDGES) + 1))  # bin centres
FLEX_REFERENCE = "0.500"  # the reference bin: expected score 0.475-0.525, centred on an even game


def es_bin_column() -> pl.Expr:
    """The expected-score bin of each row (closed on the left; the two end bins are half wide)."""
    return pl.col("es").cut(list(FLEX_EDGES), labels=list(FLEX_LABELS), left_closed=True)


def flexible_data(panel: pl.DataFrame) -> pl.DataFrame:
    """Session ends with a known 7-day return, each labelled by its expected-score bin."""
    return panel.filter(pl.col("session_last") & pl.col("return_7d").is_not_null()).with_columns(
        es_bin_column().cast(pl.Utf8).alias("es_bin")
    )


def fit_flexible(frame: pd.DataFrame, *, with_result: bool) -> ModelResult:
    """The 7-day return model with one dummy per expected-score bin instead of es and es²."""
    result = f"{OUTCOME_TERM} + " if with_result else ""
    rhs = (
        f"C(es_bin, Treatment('{FLEX_REFERENCE}')) + {result}n_plies_100 + {CONTROLS} + C(month)"
    )
    return fit_fe_lpm(frame, f"return_7d ~ {rhs}", "player", "player", "Binscatter")


def flexible_curve(panel: pl.DataFrame, *, with_result: bool) -> list[dict[str, Any]]:
    """7-day same-bot return per expected-score bin, within player, relative to an even game."""
    data = flexible_data(panel)
    frame = to_model_frame(data, ["return_7d", "es_bin", *FRAME_COLUMNS])
    model = fit_flexible(frame, with_result=with_result)
    counts = data.group_by("es_bin").len().rename({"len": "sessions"}).to_pandas()
    bins = model.terms[model.terms["term"].str.startswith("C(es_bin")].copy()
    bins["es_bin"] = bins["term"].str.extract(r"\[T\.([0-9.]+)\]")[0]
    reference = pd.DataFrame([{"es_bin": FLEX_REFERENCE, "estimate": 0.0}])
    out = pd.concat([bins[["es_bin", "estimate", "ci_low", "ci_high", "p_value"]], reference])
    out = out.merge(counts, on="es_bin", how="left")
    out["es_mid"] = out["es_bin"].astype(float)
    out["with_result"] = with_result
    return out.sort_values("es_mid").reset_index(drop=True).to_dict(orient="records")
''',
        self_contained=True,
    ),
    code(
        r"""
flexible = cached(
    "panel_flexible",
    lambda: [
        *flexible_curve(panel_games(), with_result=False),
        *flexible_curve(panel_games(), with_result=True),
    ],
)
""",
    ),
    md(
        """
#### 図の読み方

図「Binscatter」：主なモデル（7日・同じボット・プレイヤー内、4年分のパネル）の Binscatter。es の各ビンの再訪が、互角のビン（0.475〜0.525）と比べて何ポイント違うかを、95%区間（帯）とともに示す。結果を統制した場合としない場合の2本を描き、セッションが1,000未満のビンは省く。

- 両側で下がり、難しい側（左）の端の低下は、易しい側（右）の端の低下より大きい。互角から同じ距離で比べた検定は3.2で行う。
- 結果を統制すると、易しい側の端の低下が大きくなる。
""",
    ),
    code(
        r'''
# figure 2: the Binscatter of the main model, with and without the result
fig, (ax_flex,) = new_figure(1, width=5.6, height=3.6)
flex = pd.DataFrame(flexible)
ax_flex.axhline(0, color=NEUTRAL, linewidth=1)
flex_series = (
    (False, "no result controls", SERIES[0]),
    (True, "controlling for win/draw/loss", SERIES[1]),
)
for with_result, name, color in flex_series:
    part = flex[(flex["with_result"] == with_result) & (flex["sessions"] >= 1000)]
    ax_flex.fill_between(
        part["es_mid"], 100 * part["ci_low"].fillna(0), 100 * part["ci_high"].fillna(0),
        color=color, alpha=0.15, lw=0,
    )
    ax_flex.plot(part["es_mid"], 100 * part["estimate"], color=color, marker="o", label=name)
ax_flex.set_xlabel("Player's expected score vs the bot")
ax_flex.set_ylabel("Return vs an even game (pp)")
ax_flex.set_title("Binscatter: within player, four-year panel")
ax_flex.legend()
display(Image(filename=save_figure(fig, FIGURE_DIR / "d1_binscatter.png")))
''',
    ),
    md(
        r"""
#### 10本のモデルに広げる

上の Binscatter を、次の10本のモデルのそれぞれに当てはめる。

- 2.3の9本のモデル：7・28・91日 × 同じボット（プレイヤー内、ペア内）とボットを問わない再訪（プレイヤー内）。どれも対局の結果を統制する。
- 結果を統制しない7日・同じボット・プレイヤー内のモデル（上の図の青い線）。

統制変数と比べ方（`within`）は、それぞれ2.3のモデルと同じである。基準は0.475〜0.525のビンで、各ビンの値は「互角の対局の後と比べて、再訪が何ポイント違うか」を表す。

#### 10本のコード

- 2.4の `find_spec()`、`spec_key()`、`spec_label()`、`control_terms()` で、モデル（`two_lines_specs()` の10本）を指定する。
- `model_sample()`：あるモデルが使うセッション（期間内の再訪が分かっているセッションの終わり。セッションが1つしかないプレイヤーや組を除く）を取り出し、レーティング差 `gap`（ボット − プレイヤー）を加える。
- `add_bins()`：ある列をビンに分ける（ビンは左端を含む）。
- `fit_binned()`：ビンのダミーのモデルを `fit_fe_lpm()` で当てはめ、ビンごとの値、95%区間、セッション数、ビンの es とレーティング差の平均、**ビンの係数どうしの共分散行列**を返す。共分散は、3.2以降でビンの値を組み合わせた検定（例えば2つのビンの差）に使う。
- `made_up_panel()`：答えの分かっている作りもののセッションを作る（以降の検査で使う）。

定義の後の検査では、作りものの階段状の曲線から、ビンの値が復元されることを確かめる。
""",
    ),
    code(
        r'''
def model_sample(panel: pl.DataFrame, spec: dict[str, Any]) -> pl.DataFrame:
    """The sessions a model uses, with the rating gap (bot minus player)."""
    kept = dict.fromkeys([spec["outcome"], *FRAME_COLUMNS, "gap", "player_score"])
    data = (
        panel.filter(pl.col(spec["flag"]) & pl.col(spec["outcome"]).is_not_null())
        .with_columns((pl.col("opponent_elo") - pl.col("player_elo")).alias("gap"))
        .select(*kept)
        .drop_nulls([spec["outcome"], *FRAME_COLUMNS])
    )
    # groups with one session carry no within-group information, as in fit_fe_lpm()
    return data.filter(pl.len().over(spec["within"]) > 1)


def add_bins(
    sample: pl.DataFrame, column: str, edges: tuple[float, ...], labels: tuple[str, ...]
) -> pl.DataFrame:
    """Adds `<column>_bin`, the label of the bin each row falls in (bins closed on the left)."""
    binned = pl.col(column).cut(list(edges), labels=list(labels), left_closed=True).cast(pl.Utf8)
    return sample.with_columns(binned.alias(f"{column}_bin"))


REFERENCE_ROW = {"estimate": 0.0, "std_err": 0.0, "ci_low": 0.0, "ci_high": 0.0, "p_value": None}


def fit_binned(
    sample: pl.DataFrame, spec: dict[str, Any], x: str, labels: tuple[str, ...], reference: str,
) -> dict[str, Any]:
    """Return per bin of `x` relative to the reference bin, with the bins' covariance.

    Args:
        sample: Rows of model_sample() with the bin labels in `<x>_bin` (from add_bins()).
        spec: The model whose controls and comparison (`within`) are used.
        x: The binned variable.
        labels: Bin labels in order; bins without sessions are left out.
        reference: The bin every other bin is compared with.
    """
    bin_column = f"{x}_bin"
    columns = dict.fromkeys([spec["outcome"], bin_column, *FRAME_COLUMNS])
    frame = to_model_frame(sample, list(columns))
    term = f"C({bin_column}, Treatment('{reference}'))"
    formula = f"{spec['outcome']} ~ {term} + {control_terms(spec)}"
    model = fit_fe_lpm(frame, formula, spec["within"], "player", spec_label(spec))
    prefix = f"{term}[T."
    estimated = {t[len(prefix) : -1]: t for t in model.terms["term"] if t.startswith(prefix)}
    shown = [label for label in labels if label in estimated or label == reference]
    names = [estimated.get(label) for label in shown]
    index = [i for i, name in enumerate(names) if name is not None]
    picked = [names[i] for i in index]
    cov = np.zeros((len(shown), len(shown)))
    cov[np.ix_(index, index)] = model.cov.loc[picked, picked].to_numpy()
    per_bin = sample.group_by(bin_column).agg(
        pl.len().alias("sessions"), pl.col(x).mean().alias("mean_x"),
        pl.col("es").mean().alias("mean_es"), pl.col("gap").mean().alias("mean_gap"),
    )
    counts = {row[bin_column]: row for row in per_bin.to_dicts()}
    bins = []
    for label, name in zip(shown, names, strict=True):
        values = REFERENCE_ROW if name is None else model.term(name)
        bins.append({
            "bin": label, **{key: values[key] for key in REFERENCE_ROW},
            **{key: counts[label][key] for key in ("sessions", "mean_x", "mean_es", "mean_gap")},
        })
    return {"n_obs": model.n_obs, "n_clusters": model.n_clusters, "bins": bins, "cov": cov.tolist()}


def gap_of_es(es: np.ndarray) -> np.ndarray:
    """The rating gap (bot minus player) that gives this expected score under Elo's formula."""
    return 400 * np.log10((1 - es) / es)


def made_up_panel(
    curve: Callable[[np.ndarray], np.ndarray], *, n_players: int = 300, n_sessions: int = 30,
    noise: float = 0.02, seed: int = 0,
) -> pl.DataFrame:
    """Made-up session ends whose returns are curve(es) plus a player level and noise."""
    rng = np.random.default_rng(seed)
    n = n_players * n_sessions
    player = np.repeat(np.arange(n_players), n_sessions)
    bot = rng.integers(0, 5, n)
    es = rng.uniform(0.01, 0.99, n)
    player_elo = rng.integers(1000, 2000, n)
    outcome = rng.choice(["win", "draw", "loss"], n)
    level = rng.normal(scale=0.1, size=n_players)[player]
    returns = {
        f"{kind}_{days}d": curve(es) + level + rng.normal(scale=noise, size=n)
        for kind in ("return", "any_return") for days in RETURN_WINDOWS_D
    }
    return pl.DataFrame({
        "player": [f"p{i}" for i in player], "opponent": [f"bot{b}" for b in bot],
        "pair": [f"p{i}|bot{b}" for i, b in zip(player, bot, strict=True)],
        "session_last": True, "player_session_last": True, **returns,
        "outcome": outcome,
        "player_score": np.select([outcome == "win", outcome == "draw"], [1.0, 0.5], 0.0),
        "es": es, "n_plies_100": rng.uniform(0.2, 1.5, n),
        "speed": rng.choice(list(ANALYSIS_SPEEDS), n), "player_elo": player_elo,
        "opponent_elo": player_elo + np.round(gap_of_es(es)).astype(int),
        "player_elo_c": (player_elo - 1500) / 100, "log_pair_idx": rng.uniform(0, 3, n),
        "month": rng.choice(["2024-01", "2024-02", "2024-03"], n),
    })


# check: a made-up step curve is recovered bin by bin, with the reference bin at zero
step = made_up_panel(lambda es: np.where(es < 0.45, -0.1, 0.0) - np.where(es > 0.8, 0.05, 0.0))
step_fit = fit_binned(
    add_bins(model_sample(step, MAIN_SPEC), "es", FLEX_EDGES, FLEX_LABELS),
    MAIN_SPEC, "es", FLEX_LABELS, FLEX_REFERENCE,
)
step_bins = {row["bin"]: row for row in step_fit["bins"]}
assert list(step_bins) == list(FLEX_LABELS)
assert abs(step_bins["0.200"]["estimate"] + 0.1) < 0.01
assert abs(step_bins["0.900"]["estimate"] + 0.05) < 0.01
assert step_bins[FLEX_REFERENCE]["estimate"] == 0.0
assert sum(row["sessions"] for row in step_fit["bins"]) == step_fit["n_obs"]
step_cov = np.array(step_fit["cov"])
assert np.allclose(step_cov, step_cov.T)
assert not step_cov[list(step_bins).index(FLEX_REFERENCE)].any()
print("checks passed")
''',
        self_contained=True,
    ),
    md(
        """
次のセルは10本の Binscatter を当てはめる（または保存済みの結果を読み込む）。続けて次を確かめる。

- 同じモデルは同じ数値を返す：主なモデルと結果を統制しないモデルの値は上の Binscatter の値と、各モデルのセッション数は2.3の `n_obs` と一致する（`assert`）。

表は、ビンごとの値（パーセントポイント）を10本のモデルについて並べたもの、その次の表はビンごとのセッション数である。列の名前は「同じボット（same）かボットを問わない（any）か、期間、比べ方」で、`(free)` は結果を統制しないモデルである。
""",
    ),
    code(
        r'''
def spec_short(spec: dict[str, Any]) -> str:
    """A column name for a model."""
    free = "" if spec["with_result"] else " (free)"
    return f"{spec['target'].split()[0]} {spec['days']}d {spec['within']}{free}"


def fit_es_bins(spec: dict[str, Any]) -> dict[str, Any]:
    """The Binscatter of one model."""
    sample = add_bins(model_sample(panel_games(), spec), "es", FLEX_EDGES, FLEX_LABELS)
    return fit_binned(sample, spec, "es", FLEX_LABELS, FLEX_REFERENCE)


ALL_SPECS = two_lines_specs()
flexible_fits = {
    spec_key(spec): cached(f"panel_flexible_{spec_key(spec)}", lambda spec=spec: fit_es_bins(spec))
    for spec in ALL_SPECS
}

# the same models give the same numbers as the Binscatter above and the models of 2.3
for spec in (MAIN_SPEC, FREE_SPEC):
    earlier = {
        r["es_bin"]: r["estimate"] for r in flexible if r["with_result"] == spec["with_result"]
    }
    for row in flexible_fits[spec_key(spec)]["bins"]:
        assert math.isclose(row["estimate"], earlier[row["bin"]], abs_tol=1e-9)
for spec in ALL_SPECS:
    if spec["with_result"]:
        same = next(
            r for r in horizons if all(r[k] == spec[k] for k in ("target", "days", "within"))
        )
        assert flexible_fits[spec_key(spec)]["n_obs"] == same["n_obs"]


def curve_table(field: str, scale: float) -> pl.DataFrame:
    """One column per model, one row per expected-score bin."""
    columns = {
        spec_short(spec): [scale * row[field] for row in flexible_fits[spec_key(spec)]["bins"]]
        for spec in ALL_SPECS
    }
    return pl.DataFrame({"es_bin": FLEX_LABELS, **columns})


display(Markdown("**Return vs an even game (pp), by expected-score bin**"))
display(curve_table("estimate", 100.0))
display(Markdown("**Sessions by expected-score bin**"))
curve_table("sessions", 1.0)
''',
    ),
    md(
        """
#### 図の読み方

図「10本の Binscatter」：期間ごとに1枚（左から7・28・91日）。各図に、結果を統制した3本（同じボット・プレイヤー内、同じボット・ペア内、ボットを問わない・プレイヤー内）を、95%区間（帯）とともに描く。セッションが1,000未満のビンは省く。灰色の棒は、同じボット・プレイヤー内のモデルのビンごとのセッション数（es の分布）で、曲線のどの部分が多くのデータに支えられているかを示す（棒の高さは図の中での相対的な大きさ）。
""",
    ),
    code(
        r'''
def plot_bins(ax: Any, bins: list[dict[str, Any]], x: str, color: str, label: str) -> None:
    """Draws a Binscatter (pp) with its 95% band, leaving out bins with under 1,000 sessions."""
    part = pd.DataFrame(bins)
    part = part[part["sessions"] >= MIN_RETURN_ROWS]
    ax.fill_between(
        part[x], 100 * part["ci_low"], 100 * part["ci_high"], color=color, alpha=0.15, lw=0
    )
    ax.plot(part[x], 100 * part["estimate"], color=color, marker="o", markersize=3, label=label)


def plot_support(ax: Any, bins: list[dict[str, Any]], x: str = "mean_x") -> None:
    """Draws the sessions per bin as grey bars along the bottom of the axes (a histogram of x)."""
    part = pd.DataFrame(bins)
    twin = ax.twinx()
    twin.bar(part[x], part["sessions"], width=0.04, color=NEUTRAL, alpha=0.25, lw=0)
    twin.set_ylim(0, 4 * part["sessions"].max())  # the tallest bar fills a quarter of the height
    twin.set_yticks([])
    twin.grid(False)
    ax.set_zorder(twin.get_zorder() + 1)  # the curve stays in front of the bars
    ax.patch.set_visible(False)


fig, axes = new_figure(3, width=4.2, height=3.6)
for ax, days in zip(axes, RETURN_WINDOWS_D, strict=True):
    ax.axhline(0, color=NEUTRAL, linewidth=1)
    shown = [s for s in ALL_SPECS if s["days"] == days and s["with_result"]]
    same_player = find_spec("same bot", days, "player", with_result=True)
    plot_support(ax, flexible_fits[spec_key(same_player)]["bins"])
    for spec, color in zip(shown, SERIES, strict=False):
        name = f"{spec['target']}, within {spec['within']}"
        plot_bins(ax, flexible_fits[spec_key(spec)]["bins"], "mean_x", color, name)
    ax.set_xlabel("Player's expected score vs the bot")
    ax.set_title(f"{days}-day return (result held fixed)")
axes[0].set_ylabel("Return vs an even game (pp)")
axes[0].legend()
display(Image(filename=save_figure(fig, FIGURE_DIR / "d1_flexible_all.png")))
''',
    ),
    md(
        """
#### 出力の読み方

- 10本すべてで、両側で下がる山の形になっている。
- プレイヤー内の同じボットへの再訪（7・28・91日、結果を統制）では、難しい側の端のビン（es 0〜0.025）で約12〜15ポイント、易しい側の端のビン（es 0.975〜1）で約4〜5ポイント下がり、難しい側の低下が大きい。
- ペア内では、両端の低下が近い大きさになる（7日で難しい側の端が約6.9ポイント、易しい側の端が約8.0ポイント）。プレイヤー内との違いが最も大きいのは、難しい側の端である。同じボットとの組の中で es が端まで動くことは少ないので、この差には es の動く幅の違いも関わりうる。この差が何から来るかは、このノートブックでは調べない。
- ボットを問わない再訪では、低下ははるかに小さい（難しい側の端で約3〜4ポイント、易しい側の端で約1ポイント）。
""",
    ),
    md(
        """
#### 図の読み方

図「期間と比べ方の比較」：同じ Binscatter を、比べる軸ごとに重ねた2枚の図。どれも結果を統制したモデルで、横軸はビンの中央である。モデルは「比べ方 + 期間（日）」で呼ぶ：Base は同じボットへの再訪（プレイヤー内）、PairFE は同じボットへの再訪（ペア内）、AnyBot はボットを問わない再訪（プレイヤー内）。

- 上：Base の7・28・91日（期間の違い）。
- 下：7日の Base・PairFE・AnyBot（比べ方の違い）。
""",
    ),
    code(
        r'''
# figure 3: the Binscatter across horizons (left) and across comparisons (right)
MODEL_NAMES = {
    ("same bot", "player"): "Base", ("same bot", "pair"): "PairFE", ("any bot", "player"): "AnyBot",
}
overlays = (
    ("Base, by horizon", [find_spec("same bot", d, "player", with_result=True)
                          for d in RETURN_WINDOWS_D]),
    ("7-day return, by comparison", [find_spec(t, 7, w, with_result=True)
                                     for t, w in MODEL_NAMES]),
)
fig, axes = new_figure(1, width=5.6, height=3.6, n_rows=2)
for ax, (title, specs) in zip(axes, overlays, strict=True):
    ax.axhline(0, color=NEUTRAL, linewidth=1)
    for spec, color in zip(specs, SERIES, strict=False):
        fit = flexible_fits[spec_key(spec)]
        bins = [{**row, "es_mid": float(row["bin"])} for row in fit["bins"]]
        name = f"{MODEL_NAMES[(spec['target'], spec['within'])]}{spec['days']}"
        plot_bins(ax, bins, "es_mid", color, name)
    ax.set_xlabel("Player's expected score vs the bot")
    ax.set_ylabel("Return vs an even game (pp)")
    ax.set_title(title)
    ax.legend()
display(Image(filename=save_figure(fig, FIGURE_DIR / "d1_binscatter_models.png")))
''',
    ),
    md(
        r"""
### 3.2 非対称性：鏡像差の検定

#### 問い（Q3b）

互角（es = 0.5）から同じだけ離れたとき、ボットが強すぎる場合と弱すぎる場合とで、再訪の低下は同じか。

#### 方法

Binscatter の21のビンは、基準のビン（0.475〜0.525）を挟んで左右対称に並んでいる。基準を除く20のビンは、中央が0.5から同じだけ離れた10組になる（0.45 と 0.55、0.40 と 0.60、…、0 と 1。数字はビンの中央）。各組について、難しい側の値から易しい側の値を引いた**鏡像差**を求める。

- 鏡像差が負：難しい側の方が、再訪がより低い。
- 10組の差は、3.1で保存した係数とその共分散から、係数の線形結合として計算できる。その標準誤差も共分散から直接求まる（Wooldridge, 2010）。
- 検定は2つだけを、結果を見る前に決めておく（10組を1組ずつ検定すると、偶然の有意が混ざりやすい）。
  - 同時の Wald 検定（自由度10）：10組の差がすべて0か。Wald 検定は、推定値のベクトルがその共分散に照らして0からどれだけ離れているかを、カイ二乗分布で評価する。
  - 要約の1つの数：10組の差の平均と、その標準誤差。

#### この検定が答えること・答えないこと

- es は Elo の式で0.5を中心に対称なので、各組は「同じレーティング差だけ強いボットと弱いボット」の比較になる。この検定が答えるのは「同じ点差だけ強すぎる相手と弱すぎる相手のどちらの後に、より戻らなくなるか」である。
- 鏡像差は、頂点が0.5からずれていることと、左右の腕の傾きが違うことの両方を拾う。したがって「曲線の形が左右非対称だ」という意味の検定ではない。頂点から測った比較は、このノートブックでは行わない。
- 両端の組（0〜0.025 と 0.975〜1）は幅が半分で、レーティング差では上限のない開いたビンなので、実際のレーティング差の平均は左右で違う（下の表の `mean_gap`）。この組だけは厳密な鏡像ではない。

#### 両端の比

段階4で照合する `flexible_asymmetry`（難しい側の端のビンの値 ÷ 易しい側の端のビンの値）には、これまで信頼区間がなかった。ここでは、2つの推定値の比の95%区間を Fieller の方法（Fieller, 1954）で求める。Fieller の信頼区間は、比 r について「分子 − r × 分母」が0と有意に違わない r の範囲である。分母がはっきり0と違えば有限の信頼区間になる。

定義の後の検査では、次を確かめる。

- 対称な曲線では鏡像差が0になり、同時の Wald 検定が有意にならないこと。
- 作りもののデータで、既知の非対称（難しい側だけが下がる）が検出されること。
- 分母が確定しているときの Fieller の信頼区間が、通常の95%区間と一致すること。
""",
    ),
    code(
        r'''
ES_MIRROR_PAIRS = tuple(
    (f"{0.5 - 0.05 * k:.3f}", f"{0.5 + 0.05 * k:.3f}") for k in range(1, 11)
)  # (hard, easy) bins at the same distance from an even game, nearest first


def wald_test(values: np.ndarray, cov: np.ndarray) -> tuple[float, float]:
    """Wald statistic that every value is zero, and its chi-squared p-value."""
    statistic = float(values @ np.linalg.solve(cov, values))
    return statistic, float(stats.chi2.sf(statistic, values.size))


def linear_combination(
    estimates: np.ndarray, cov: np.ndarray, weights: np.ndarray
) -> dict[str, float]:
    """A weighted sum of estimates with its standard error, 95% interval and p-value."""
    value = float(weights @ estimates)
    se = math.sqrt(float(weights @ cov @ weights))
    p = float(2 * stats.norm.sf(abs(value) / se)) if se > 0 else math.nan
    return {"estimate": value, "std_err": se, "ci_low": value - Z95 * se,
            "ci_high": value + Z95 * se, "p_value": p}


def bin_arrays(fit: dict[str, Any]) -> tuple[list[str], np.ndarray, np.ndarray]:
    """The bin labels, estimates and covariance of a binned fit."""
    labels = [row["bin"] for row in fit["bins"]]
    return labels, np.array([row["estimate"] for row in fit["bins"]]), np.array(fit["cov"])


def mirror_test(
    fit: dict[str, Any], pairs: tuple[tuple[str, str], ...], min_sessions: int = MIN_RETURN_ROWS
) -> dict[str, Any]:
    """Hard-minus-easy differences of mirror bins: each pair, a joint Wald test, and their mean.

    Pairs with a bin of fewer than `min_sessions` sessions are left out.
    """
    labels, estimates, cov = bin_arrays(fit)
    sessions = {row["bin"]: row["sessions"] for row in fit["bins"]}
    kept = [
        (hard, easy) for hard, easy in pairs
        if min(sessions.get(hard, 0), sessions.get(easy, 0)) >= min_sessions
    ]
    contrast = np.zeros((len(kept), len(labels)))
    for row, (hard, easy) in enumerate(kept):
        contrast[row, labels.index(hard)], contrast[row, labels.index(easy)] = 1.0, -1.0
    differences, diff_cov = contrast @ estimates, contrast @ cov @ contrast.T
    statistic, p_value = wald_test(differences, diff_cov)
    mean = linear_combination(differences, diff_cov, np.full(len(kept), 1 / len(kept)))
    rows = [
        {"hard_bin": hard, "easy_bin": easy,
         **linear_combination(differences, diff_cov, np.eye(len(kept))[row])}
        for row, (hard, easy) in enumerate(kept)
    ]
    return {"pairs": rows, "n_pairs": len(kept), "wald": statistic, "p_value": p_value,
            **{f"mean_{key}": value for key, value in mean.items()}}


def fieller_interval(
    a: float, b: float, v_aa: float, v_ab: float, v_bb: float
) -> tuple[float, float]:
    """95% Fieller (1954) interval of the ratio a / b; (nan, nan) when it is unbounded."""
    z2 = Z95**2
    qa, qb, qc = b * b - z2 * v_bb, -2 * (a * b - z2 * v_ab), a * a - z2 * v_aa
    discriminant = qb * qb - 4 * qa * qc
    if qa <= 0 or discriminant < 0:
        return math.nan, math.nan
    root = math.sqrt(discriminant)
    return (-qb - root) / (2 * qa), (-qb + root) / (2 * qa)


def end_ratio(
    fit: dict[str, Any], hard: str = FLEX_LABELS[0], easy: str = FLEX_LABELS[-1]
) -> dict[str, float]:
    """The hardest bin's value over the easiest bin's value, with a Fieller interval."""
    labels, estimates, cov = bin_arrays(fit)
    i, j = labels.index(hard), labels.index(easy)
    low, high = fieller_interval(estimates[i], estimates[j], cov[i, i], cov[i, j], cov[j, j])
    return {"ratio": float(estimates[i] / estimates[j]), "ci_low": low, "ci_high": high}


def made_up_fit(estimates: dict[str, float], variance: float) -> dict[str, Any]:
    """A binned fit with chosen estimates and independent errors (reference bin exact)."""
    labels = list(estimates)
    cov = np.diag([0.0 if label == FLEX_REFERENCE else variance for label in labels])
    bins = [
        {"bin": label, "estimate": value, "sessions": 10**6} for label, value in estimates.items()
    ]
    return {"bins": bins, "cov": cov.tolist()}


# check 1: a symmetric curve has zero mirror differences
symmetric = made_up_fit({label: -abs(float(label) - 0.5) for label in FLEX_LABELS}, 1e-4)
test = mirror_test(symmetric, ES_MIRROR_PAIRS)
assert test["n_pairs"] == 10 and math.isclose(test["wald"], 0.0, abs_tol=1e-12)
assert math.isclose(test["mean_estimate"], 0.0, abs_tol=1e-12)
# pair (0.450, 0.550): two independent errors of variance 1e-4
assert math.isclose(test["pairs"][0]["std_err"], math.sqrt(2e-4))

# check 2: a made-up hard-side drop is detected, and none is found when there is none
for drop, detected in ((0.05, True), (0.0, False)):
    made_up_drop = made_up_panel(
        lambda es, d=drop: -d * (es < 0.3) - 0.03 * (np.abs(es - 0.5) > 0.3)
    )
    made_up_bins = add_bins(model_sample(made_up_drop, MAIN_SPEC), "es", FLEX_EDGES, FLEX_LABELS)
    fit = fit_binned(made_up_bins, MAIN_SPEC, "es", FLEX_LABELS, FLEX_REFERENCE)
    test = mirror_test(fit, ES_MIRROR_PAIRS, min_sessions=0)
    assert (test["p_value"] < ALPHA) == detected and (test["mean_estimate"] < -0.01) == detected

# check 3: with an exact denominator, Fieller's interval is a / b +- z se(a) / |b|
low, high = fieller_interval(-0.1, -0.04, 0.0001, 0.0, 0.0)
assert math.isclose(low, 2.5 - Z95 * 0.25) and math.isclose(high, 2.5 + Z95 * 0.25)
print("checks passed")
''',
        self_contained=True,
    ),
    md(
        """
次のセルは、10本のモデルの Binscatter に鏡像差の検定を当てはめる。

- 1つ目の表：モデルごとの要約。`n_pairs` は組の数（どちらのビンにも1,000以上のセッションがある組）、`wald` と `p_value` は同時の Wald 検定、`mean_estimate`〜`mean_p_value` は10組の差の平均とその標準誤差、95%区間、p 値（パーセントポイントでなく確率の単位）。`end_bins` は残った組のうち最も外側の組、`end_ratio` はその2つのビンの比（難しい側 ÷ 易しい側）、`end_ratio_ci_low`〜`end_ratio_ci_high` はその Fieller の95%区間。
- 2つ目の表：主なモデル（7日・同じボット・プレイヤー内、結果を統制）の組ごとの差。`distance` はビンの中央と0.5の距離である。
""",
    ),
    code(
        r'''
def mirror_row(fit: dict[str, Any], **labels: Any) -> dict[str, Any]:
    """The mirror test and the end ratio (outermost pair kept) of one fit, as one table row."""
    test = mirror_test(fit, ES_MIRROR_PAIRS)
    outermost = test["pairs"][-1]
    ratio = end_ratio(fit, outermost["hard_bin"], outermost["easy_bin"])
    return {
        **labels, "n_pairs": test["n_pairs"], "wald": test["wald"], "p_value": test["p_value"],
        **{key: value for key, value in test.items() if key.startswith("mean_")},
        "end_bins": f"{outermost['hard_bin']}/{outermost['easy_bin']}",
        "end_ratio": ratio["ratio"], "end_ratio_ci_low": ratio["ci_low"],
        "end_ratio_ci_high": ratio["ci_high"],
    }


def mirror_rows(
    fits: dict[str, dict[str, Any]], specs: list[dict[str, Any]], axis: str
) -> list[dict[str, Any]]:
    """mirror_row() of each model."""
    return [mirror_row(fits[spec_key(spec)], axis=axis, **spec_columns(spec)) for spec in specs]


mirror = mirror_rows(flexible_fits, ALL_SPECS, "es")
main_pairs = [
    {"distance": round(0.5 - float(row["hard_bin"]), 3), **row}
    for row in mirror_test(flexible_fits[spec_key(MAIN_SPEC)], ES_MIRROR_PAIRS)["pairs"]
]
display(pl.DataFrame(mirror))
pl.DataFrame(main_pairs)
''',
    ),
    md(
        """
#### 図の読み方

図「互角を軸に折り返した曲線」：横軸はビンの中央と0.5の距離、縦軸は互角の対局の後と比べた再訪の違い（パーセントポイント）。難しい側（es < 0.5）と易しい側（es > 0.5）を重ねて描く。モデルは主なモデル、すなわち結果を統制した Base7（7日・同じボット・プレイヤー内）である。2本の線の間の縦の差が、鏡像差である。
""",
    ),
    code(
        r'''
# figure 4: the Base7 Binscatter (result held fixed) folded at an even game
fig, (ax,) = new_figure(1, width=5.6, height=3.6)
bins = pd.DataFrame(flexible_fits[spec_key(MAIN_SPEC)]["bins"])
bins["distance"] = (bins["bin"].astype(float) - 0.5).abs()
ax.axhline(0, color=NEUTRAL, linewidth=1)
centre = bins["bin"].astype(float)  # the reference bin (distance 0) starts both sides
for side, chosen, color in (("hard side (es < 0.5)", centre <= 0.5, SERIES[1]),
                            ("easy side (es > 0.5)", centre >= 0.5, SERIES[0])):
    part = bins[chosen].sort_values("distance")
    ax.fill_between(part["distance"], 100 * part["ci_low"], 100 * part["ci_high"],
                    color=color, alpha=0.15, lw=0)
    ax.plot(part["distance"], 100 * part["estimate"], color=color, marker="o", label=side)
ax.set_xlabel("Distance of the bin from an even game (expected score)")
ax.set_ylabel("Return vs an even game (pp)")
ax.set_title("Comparison of left and right in Base7")
ax.legend()
display(Image(filename=save_figure(fig, FIGURE_DIR / "d1_mirror.png")))
''',
    ),
    md(
        """
#### 出力の読み方

- プレイヤー内のモデルでは、6本すべてで鏡像差の平均が負で、同時の Wald 検定も有意である（p < 10⁻⁵）。主なモデルでは、互角から同じだけ離れたとき、難しい側の再訪は易しい側より平均で約1.5ポイント（95%区間 1.0〜2.1）低い。結果を統制しないモデルでは約2.3ポイントである。
- 主なモデルの組ごとの差は、互角から0.3離れるまでは0と区別できず、それより外側で負に大きくなる（最も外側の組で約7.3ポイント）。
- 両端の比は、主なモデルで約2.5（Fieller の95%区間 2.0〜3.5）、結果を統制しないモデルで約3.5（2.5〜5.4）である。段階4で照合する `flexible_asymmetry` に、ここで初めて95%区間が付いた。
- ペア内のモデルでは、非対称性ははっきりしない（7日：鏡像差の平均はほぼ0、同時の検定 p ≈ 0.5、両端の比 ≈ 0.9）。「同じ点差だけ強すぎる相手の後のほうが戻らない」という非対称性は、主に、ボットを選び替えるセッションどうしの比較から来ている。ペア内では es の動く幅が狭いことも関わりうる。その点は、このノートブックでは調べない。
""",
    ),
]
"""The cells, in notebook order."""
