"""Notebook cells of stage 2: the test of the inverted U (Q2a-Q2e) and figure 1.

Names used from earlier stages:
    stage 0: Any, Axes, FIGURE_DIR, Image, Markdown, NEUTRAL, SERIES, STUDY_MONTHS, cache,
        cached, config, dataclass, display, math, new_figure, np, optimize, patsy, pd, pl,
        save_figure, sm
    stage 1: PANEL_COLUMNS, bots, example, load_games, load_month
"""

from __future__ import annotations

import nbformat

from .common import code, md

CELLS: list[nbformat.NotebookNode] = [
    md(
        """
## 2. 逆U字の検定

### 問いと進め方

問いは次の5つである。

- Q2a：期待スコアと7日以内の再訪の関係は、山の形（逆U字）か。つまり、互角の付近で最も高く、難しい側でも易しい側でも下がるか。
- Q2b：その山の形は、28日・91日以内の再訪でも保たれるか。
- Q2c：対局の結果（勝ち・引き分け・負け）を統制変数として加えても保たれるか。つまり、「易しいボットには勝ちやすい」ことだけでは説明できないか。結果ごとに別の曲線を描くのではなく、3つの結果で共通の形を、高さだけ結果ごとにずらして推定する。
- Q2d：同じプレイヤーと同じボットのペアの中でも保たれるか。
- Q2e：同じボットへの再訪に限らず、ボットとの対局そのものへの再訪（相手は同じボットでも別のボットでもよい）でも保たれるか。

次の順に答える。

- 2.1：4年分を1つのパネルに積み、月の境をまたいでセッションと再訪を作り直す。
- 2.2：この段階のすべての当てはめの基になる、プレイヤー内の線形確率モデルを定める。統制変数には、対局の結果と暦月（月の固定効果）も入れる。
- 2.3：期間、再訪の数え方、比べ方を変えた9本のモデルを当てはめる（Q2b〜Q2e）。2次式の項と頂点は、9本を並べるための要約である。
- 2.4：山の形かどうかを、2直線の検定（Simonsohn, 2018）で、9本のモデルのそれぞれと、結果を統制しない7日のモデルについて判定する（Q2a〜Q2e）。モデルを使わない生の値と並べて、図に示す。

この段階では、逆U字かどうかだけを判定する。難しい側と易しい側の下がり方の違いは段階3で調べる。頂上の位置と幅は、このノートブックでは測らない。
""",
    ),
    md(
        """
### 2.1 4年分のパネル

4年分を1つのパネルに積み、月の境をまたいでセッションと再訪を作り直す。

次のセルは、段階1の例の組をパネルの中で示す。新しい種類の列が2つ現れる。

- `return_28d`、`return_91d`：同じボットへ28日・91日以内に再訪したか。
- `any_return_7d`、`any_return_28d`、`any_return_91d`：7・28・91日以内に、ボットとの対局に戻ってきたか。相手は同じボットでも別のボットでもよい。
  - ここでは、相手のボットを問わず、30分を超える間隔なしに続いたプレイヤーの一連の対局を1つのセッションとする。
  - `player_session_last` がその最後の対局を示す。

#### 期間どうしの関係

7日・28日・91日の再訪は、どれも「30分後から N 日後までに同じボットとまた指した」ことを表し、期間の始点は同じである。
つまり `return_91d` は29〜91日目だけを見るのではなく、30分後から91日後までの全体を見ており、`return_28d` の期間をそのまま含む。

- `return_28d` が true なら、`return_91d` も必ず true である（`return_28d` は `return_91d` が true であるための十分条件）。
- 逆は成り立たない。28日以内には戻らず、29〜91日目の間に戻った場合は、`return_28d` は false、`return_91d` は true になる。
- 7日と28日の間も、`any_return_*` の各期間の間も、同じ関係にある。
- ただし欠測は包含関係にならない。期間がデータの終わりを越えるセッションは `null`（分からない）になる。期間が長いほど `null` が多いので、`return_28d` が分かっていて `return_91d` が `null` のセッションがある。

この関係は、例の表の後のセルで4年分のパネルについて確かめる。
""",
    ),
    code(
        r"""
pl.scan_parquet(config.month_dir(config.PANEL_NAME) / "player_games.parquet").filter(
    (pl.col("player") == example["player"]) & (pl.col("opponent") == example["opponent"])
).select(
    "month", "start", "session_last", "return_7d", "return_28d", "return_91d",
    "player_session_last", "any_return_7d", "any_return_28d", "any_return_91d",
).sort("start").collect()
""",
    ),
    md(
        """
#### 例の読み方

セッションの区切り方は段階1と同じである。

- 12月1日のセッションの後は、2日後に戻ってきた。そのため、どの期間でも、またボットとの対局そのものへの再訪でも true である。
- 12月3日のセッションの後は、91日以内にどのボットとも指していない。そのため、再訪の列がすべて false になる。
- この前後にほかのボットとは指していないので、ここでは `player_session_last` が `session_last` と同じになる。

#### 包含関係の確認

続くセルは、上で述べた包含関係を4年分のパネルで数える。

- 破れを調べる4行：`7d true, 28d false`、`28d true, 91d false`、`any 7d true, 28d false`、`any 28d true, 91d false`。
  - 「短い期間で true なのに、長い期間で false」のセッションの数である。包含関係が破れるのはこの場合だけである。
  - すべて 0 になる。
- 参考の1行：`28d known, 91d null` は包含関係の破れではない。データの終わりの近くで、28日は追えるが91日は追えないセッションである。
""",
    ),
    code(
        r"""
nested = (
    pl.scan_parquet(config.month_dir(config.PANEL_NAME) / "player_games.parquet")
    .select(
        pl.len().alias("games"),
        (pl.col("return_7d") & ~pl.col("return_28d")).sum().alias("7d true, 28d false"),
        (pl.col("return_28d") & ~pl.col("return_91d")).sum().alias("28d true, 91d false"),
        (pl.col("any_return_7d") & ~pl.col("any_return_28d")).sum().alias("any 7d true, 28d false"),
        (pl.col("any_return_28d") & ~pl.col("any_return_91d"))
        .sum()
        .alias("any 28d true, 91d false"),
        (pl.col("return_28d").is_not_null() & pl.col("return_91d").is_null())
        .sum()
        .alias("28d known, 91d null"),
    )
    .collect()
)
assert nested.row(0, named=True)["7d true, 28d false"] == 0
assert nested.row(0, named=True)["28d true, 91d false"] == 0
assert nested.row(0, named=True)["any 7d true, 28d false"] == 0
assert nested.row(0, named=True)["any 28d true, 91d false"] == 0
nested.transpose(include_header=True, column_names=["games"])
""",
    ),
    md(
        """
#### 分析に使う標本

- `prepare()`：パネルのモデルに必要な変数を加える。プレイヤーとボットの組、対局の長さ（100手（半手）単位）である。
- `describe()`：標本の大きさ（対局、プレイヤー、ボット、月の数）を数える。
- `panel_games()`：まだ保存していない当てはめが初めて必要としたときに、パネルを1回だけ読み込む。

続くセルの出力は、パネルの大きさと、7日以内の再訪が分かっているセッションの終わりの数である。
""",
    ),
    code(
        r'''
def prepare(panel: pl.DataFrame) -> pl.DataFrame:
    """Adds the player-bot pair id and the game length."""
    return panel.with_columns(
        (pl.col("player") + "|" + pl.col("opponent")).alias("pair"),
        (pl.col("n_plies") / 100).alias("n_plies_100"),
    )


def describe(panel: pl.DataFrame) -> dict[str, int]:
    """Size of the analysis sample."""
    return {
        "n_games": panel.height,
        "n_players": panel["player"].n_unique(),
        "n_bots": panel["opponent"].n_unique(),
        "n_months": panel["month"].n_unique(),
    }
''',
        self_contained=True,
    ),
    code(
        r'''
@cache
def panel_games() -> pl.DataFrame:
    """The four-year panel's analysis sample (read on first use; several GB of memory)."""
    return prepare(load_games(config.month_dir(config.PANEL_NAME), PANEL_COLUMNS, bots))


panel_size = cached("panel_describe", lambda: describe(panel_games()))
n_session_ends_7d = cached(
    "panel_n_session_ends_7d",
    lambda: panel_games().filter(pl.col("session_last") & pl.col("return_7d").is_not_null()).height,
)
display(Markdown(
    f"**Panel:** {panel_size['n_games']:,} games, {panel_size['n_players']:,} players, "
    f"{panel_size['n_bots']:,} bots, {panel_size['n_months']} months; "
    f"{n_session_ends_7d:,} session ends with a known 7-day return"
))
''',
    ),
    md(
        r"""
### 2.2 主なモデル

2.3の9本のモデル、2.4の2直線の検定、段階3の Binscatter は、どれも次の線形確率モデルを基にしている。
1行は1つのセッション（その最後の対局）である。プレイヤー $i$ の $s$ 番目のセッションについて、次の式を `fit_fe_lpm()` で当てはめる。

$$
\begin{aligned}
y_{is} = {} & b\,\mathrm{es}_{is} + c\,\mathrm{es}_{is}^2 \\
& + \beta_1\,\mathrm{draw}_{is} + \beta_2\,\mathrm{loss}_{is} + \gamma_1\,\mathrm{plies}_{is} \\
& + \textstyle\sum_k \delta_k\,\mathrm{speed}_{k,is} + \gamma_2\,\mathrm{elo}_{is} + \gamma_3 \log(1 + n_{is})
  + \mu_{m(is)} + \alpha_i + \varepsilon_{is}
\end{aligned}
$$

| 記号 | 列 | 意味 |
|---|---|---|
| $y_{is}$ | `return_7d`（2.3のほかのモデルでは `return_28d`、`return_91d`、`any_return_*`） | 結果変数。セッションの後、期間内に再訪すれば1、しなければ0 |
| $\mathrm{es}_{is}$ | `es` | 期待スコア（0〜1）。大きいほどボットが易しい |
| $\mathrm{draw}_{is}$、$\mathrm{loss}_{is}$ | `outcome` | 引き分けなら1、負けなら1のダミー。勝ちが基準 |
| $\mathrm{plies}_{is}$ | `n_plies_100` | 対局の長さ（半手の数 / 100） |
| $\mathrm{speed}_{k,is}$ | `speed` | 持ち時間の種類のダミー |
| $\mathrm{elo}_{is}$ | `player_elo_c` | 対局前のプレイヤーのレーティング。(レーティング − 1500) / 100 |
| $n_{is}$ | `log_pair_idx` = log(1 + n) | このボットとそれまでに指した局数 |
| $\mu_{m(is)}$ | `month` | 暦月の固定効果。その月に全員の再訪率が一緒に上下する分 |
| $\alpha_i$ | `player`（ペア内のモデルでは `pair`） | プレイヤー（ペア内では組）の固定効果。その人のもともとの再訪しやすさ |
| $\varepsilon_{is}$ | — | 誤差 |

- 説明変数は、すべてセッションの最後の対局の値である。プレイヤーが「やめる」と決めた時点から再訪を数えるためである。
- 曲線の形は $b$ と $c$ で決まる。$c < 0$ なら上に凸で、頂点は $\mathrm{es}^* = -b / (2c)$ である。ただし、$c < 0$ だけでは逆U字とは言えないので、逆U字かどうかは2.4の2直線の検定で確かめる。
#### 推定の方法

- `fit_fe_lpm()`：グループ（ここではプレイヤー）内で線形確率モデルを推定する。
  - $\alpha_i$ を一つずつ推定する代わりに、結果変数とすべての説明変数から各プレイヤー自身の平均を引き、その残差に最小二乗法を当てはめる（within推定量；Wooldridge, 2010, 10章）。これにより、同じプレイヤーのセッション間の違いだけが使われる。
  - セッションが1つしかないプレイヤーは、比較相手がないので除く。変数が欠けた行も除く。
  - 標準誤差は、プレイヤー単位のクラスター頑健標準誤差とする（Cameron & Miller, 2015）。
- `peak()`：曲線の頂上 −b / (2c) と、デルタ法によるその95%信頼区間を求める（Oehlert, 1992）。

#### このモデルを選ぶ理由

- 線形確率モデルにする理由（ロジットにしない理由）：
  - 係数が、そのまま確率の差（パーセントポイント）として読める（Wooldridge, 2010, 15章；Angrist & Pischke, 2009）。
  - プレイヤーの固定効果は非常に多い。線形なら、各プレイヤーの平均を引くだけで取り除ける。ロジットのような非線形のモデルに多数の固定効果を入れると、推定値が偏りうる（付随パラメータ問題；Wooldridge, 2010, 15章）。
  - 欠点は、予測した確率が0〜1をはみ出しうることである。ここで見るのは es による再訪の差なので、問題になりにくい。また、誤差の分散が一定でないので、頑健な標準誤差を使う。
- es と es² の2次式にする理由：
  - 逆U字を表せる最も単純な形で、頂点が −b / (2c) という1つの数で求まる。
  - 2次式は、頂点の左右で同じ形を仮定する。そのため、左右の下がり方の違いは2次式では測れない。段階3で、形を仮定しない Binscatter で調べる。
  - レーティング差ではなく es を使うのは、どのレーティング帯でも、同じ es が同じ勝つ見込みを表すためである。
- プレイヤーの固定効果を入れる理由：
  - 「難しい相手を選ぶ人は、あまり戻ってこない」という人どうしの違いと、「同じ人が、いつもより難しい対局の後には戻ってきにくい」という同じ人の中の過程は、別の問いである（Curran & Bauer, 2011）。
  - 固定効果は前者を取り除き、後者に答える。挑戦と技能の釣り合いを語るフロー理論（Csikszentmihalyi, 1990）が対象とするのも、後者である。
- 統制変数を入れる理由：es とも再訪とも関係しうるものを、そろえて比べるためである。
  - 持ち時間の種類：ブレットとクラシカルでは、再訪の習慣が違う。
  - レーティング：同じ人の中でも、レーティングは時間とともに動く。
  - それまでの対局数：慣れや習慣で、戻りやすさが変わる。
  - 対局の長さ：難しさ以外の対局の性質も、再訪を左右しうる。
  - 暦月：季節やサイトの変化で、全員の再訪率が一緒に上下する分を除く。
  - 対局の結果：「易しいボットには勝ちやすく、勝つと戻りやすい」というだけで山ができていないかを見る。ただし結果は難しさの後に決まるので、これを統制した推定値は「結果を通らない難しさの効果」ではない（悪い統制変数；Angrist & Pischke, 2009）。「勝ち負けが同じ対局どうしでも形が残る」と読むにとどめる。
  - 入れないもの：
    - セッションの対局数。それまでの対局の難しさにも左右されるので、固定すると難しさの効果の一部を取り除いてしまう（悪い統制変数；Angrist & Pischke, 2009）。
    - ボットの指し方（即座に指す割合、人間らしく指すよう作られたボットか）。本研究が問うのはプレイヤーから見た難しさであり、ボットの性質は問いの外にあるためである。
- クラスター頑健標準誤差を使う理由：同じプレイヤーのセッションは互いに独立でなく、通常の標準誤差では精度を過大に見積もる（Cameron & Miller, 2015）。

#### 平易な意味

- このモデルが答えるのは、「同じ人が、いつもより易しい（難しい）ボットと指してやめたとき、その後7日以内に同じボットとまた指す確率は何ポイント変わるか」という問いである。
- 比べるときには、持ち時間、レーティング、そのボットとの慣れ、対局の長さ、時期をそろえる。結果を統制したモデルでは、勝ち負けもそろえる。
- $b$ と $c$ は、その確率が es とともにどう変わるかという曲線の形を表す。頂点は、その確率が最も高くなる難しさである。
- 大きさの目安：$c = -0.3$ なら、頂点から es が0.3離れると、再訪は約 0.3 × 0.3² ≈ 2.7ポイント下がる。
- これは観察データでの関係であり、実験による因果効果ではない。プレイヤーは相手を自分で選ぶので、その時々の選び方の理由までは取り除けない。

定義の後の検査では、人工データを使って次を確かめる。

- within推定量が、プレイヤーごとのダミー変数を入れた回帰と同じ傾きを返すこと（重みを付けた場合も）。
- `peak()` が既知の答えを返すこと。
""",
    ),
    code(
        r'''
Z95 = 1.959963984540054  # two-sided 95% normal quantile
ALPHA = 0.05  # significance level of every test
ES, ES2 = "es", "I(es ** 2)"  # the names patsy gives the two curve terms
@dataclass(frozen=True)
class ModelResult:
    """A fitted regression: one row per coefficient, plus the coefficients' covariance."""

    name: str
    terms: pd.DataFrame  # term, estimate, std_err, ci_low, ci_high, p_value
    cov: pd.DataFrame  # cluster-robust covariance of the coefficients
    n_obs: int
    n_clusters: int

    def term(self, name: str) -> dict[str, float]:
        """The statistics of one coefficient."""
        row = self.terms[self.terms["term"] == name]
        if row.empty:
            raise KeyError(name)
        return {str(k): float(v) for k, v in row.iloc[0].items() if k != "term"}


def tidy(result: Any, name: str, n_clusters: int) -> ModelResult:
    """Wraps a fitted statsmodels result, with normal 95% intervals."""
    params, se = result.params, result.bse
    terms = pd.DataFrame({
        "term": params.index,
        "estimate": params.to_numpy(),
        "std_err": se.to_numpy(),
        "ci_low": (params - Z95 * se).to_numpy(),
        "ci_high": (params + Z95 * se).to_numpy(),
        "p_value": result.pvalues.to_numpy(),
    })
    return ModelResult(name, terms, result.cov_params(), int(result.nobs), n_clusters)


def to_model_frame(games: pl.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Selected columns as pandas, with true/false turned into 1/0."""
    return games.select(columns).with_columns(pl.col(pl.Boolean).cast(pl.Int8)).to_pandas()


def fit_fe_lpm(
    df: pd.DataFrame, formula: str, fe: str, cluster: str, name: str
) -> ModelResult:
    """Linear probability model within `fe` groups, errors clustered on `cluster`."""
    data = df.dropna(subset=[fe, cluster])
    y, x = patsy.dmatrices(formula, data, return_type="dataframe")
    # groups with one row carry no within-group information (counted after patsy drops NAs)
    used = data.loc[x.index, fe]
    informative = (used.groupby(used).transform("size") > 1).to_numpy()
    y, x = y[informative], x[informative]
    x = x.drop(columns=[c for c in x.columns if c == "Intercept"])
    keys = data.loc[x.index, fe].to_numpy()
    # within estimator: subtract each group's mean from the outcome and every column
    y_dm = y.iloc[:, 0] - y.iloc[:, 0].groupby(keys).transform("mean")
    x_dm = x - x.groupby(keys).transform("mean")
    # columns constant within every group (e.g. a level never seen twice) vanish
    x_dm = x_dm.loc[:, x_dm.abs().sum() > 1e-12]
    groups = pd.factorize(data.loc[x.index, cluster])[0]
    result = sm.OLS(y_dm, x_dm).fit(cov_type="cluster", cov_kwds={"groups": groups})
    return tidy(result, name, int(groups.max() + 1))


def peak(model: ModelResult, linear: str = ES, square: str = ES2) -> dict[str, float]:
    """Top of b·es + c·es², es = -b / (2c), with its delta-method 95% interval."""
    b, c = model.term(linear)["estimate"], model.term(square)["estimate"]
    top = -b / (2 * c)
    grad = np.array([-1 / (2 * c), b / (2 * c**2)])  # derivative of the top in (b, c)
    cov = model.cov.loc[[linear, square], [linear, square]].to_numpy()
    se = math.sqrt(float(grad @ cov @ grad))
    return {"es": top, "se": se, "ci_low": top - Z95 * se, "ci_high": top + Z95 * se}


# check 1: the within estimator equals a regression with one dummy per player
rng = np.random.default_rng(0)
player = np.repeat(np.arange(200), 20)
level = rng.normal(size=200)[player]
x = rng.normal(size=player.size) + level
made_up = pd.DataFrame({
    "y": 0.3 * x + 2.0 * level + rng.normal(scale=0.1, size=player.size), "x": x, "player": player,
})
within = fit_fe_lpm(made_up, "y ~ x", "player", "player", "within")
y_d, x_d = patsy.dmatrices("y ~ x + C(player)", made_up, return_type="dataframe")
assert math.isclose(within.term("x")["estimate"], sm.OLS(y_d, x_d).fit().params["x"], abs_tol=1e-9)
assert abs(within.term("x")["estimate"] - 0.3) < 0.01


def made_up_model(b: float, c: float, cov: list[list[float]]) -> ModelResult:
    """A model with only the two curve terms and a chosen covariance."""
    terms = pd.DataFrame({
        "term": [ES, ES2],
        "estimate": [b, c],
        "std_err": [math.sqrt(cov[0][0]), math.sqrt(cov[1][1])],
        "ci_low": [0.0, 0.0], "ci_high": [0.0, 0.0], "p_value": [0.0, 0.0],
    })
    covariance = pd.DataFrame(cov, index=[ES, ES2], columns=[ES, ES2])
    return ModelResult("made up", terms, covariance, 1, 1)


# check 2: top at 0.6; with only b uncertain, se(top) = se(b) / (2|c|)
top = peak(made_up_model(0.6, -0.5, [[0.01, 0.0], [0.0, 0.0]]))
assert math.isclose(top["es"], 0.6) and math.isclose(top["se"], 0.1)

print("checks passed")
''',
        self_contained=True,
    ),
    md(
        """
### 2.3 9本のモデル

2.2のモデルを、設定を変えた9本として4年分のパネルに `fit_fe_lpm()` で当てはめる（`horizon_rows()`）。9本は問い Q2b〜Q2e に対応する。各モデルが山の形かどうかは、2.4の2直線の検定で判定する。下の表の1行が1本のモデルである。

- Q2b 期間：7日・28日・91日の再訪（`days`）。期間ごとに、少なくとも1,000のセッションの終わりが必要である。
- Q2c 結果の統制：9本すべてに対局の結果を入れる（2.4の2直線の検定では、入れない場合とも比べる）。
- Q2d ペア内：同じプレイヤーと同じボットの組の中で比べる（`within` が `pair`）。
- Q2e ボットとの対局そのもの：相手のボットを問わず再訪を数える（`target` が `any bot`）。

モデルはデータを記述するだけで、何かを予測するよう学習させたものではない。行どうしの違いは、何を再訪と数えるか（`target`、`days`）と、各セッションを誰と比べるか（`within`）だけである。

論文では、各モデルを「比べ方 + 期間（日）」で呼ぶ。Base は同じボットへの再訪・プレイヤー内（`same bot`、`player`）、PairFE は同じボットへの再訪・ペア内（`same bot`、`pair`）、AnyBot はボットを問わない再訪・プレイヤー内（`any bot`、`player`）である。例えば Base7 は、7日以内の同じボットへの再訪をプレイヤー内で比べるモデルである。

#### `target`：何を再訪と数えるか

- `same bot`：プレイヤーが**同じボット**とまた指すことを再訪と数える。このノートブックのほかの箇所で使っている再訪は、すべてこれである。セッションはそのボット1体との一連の対局で、行はその最後の対局である。
- `any bot`：プレイヤーが**ボットとの対局そのもの**に戻ってくることを再訪と数える。相手は同じボットでも別のボットでもよい。
  - セッション：相手のボットを問わず、30分を超える間隔なしに続いたプレイヤーの一連の対局。行はその最後の対局である。その後30分〜`days` 日の間にどれかのボットと指せば、再訪は yes となる。
  - 例：プレイヤーが夜にボットAと指してやめ、翌日はボットBとだけ指した。このとき、A の後の「同じボット」への再訪は no だが、「any bot」の再訪は yes である。
  - 問い（Q2e）：難しすぎる対局や易しすぎる対局の後に、プレイヤーは別のボットに移るだけなのか、ボットとの対局そのものから離れるのか。

#### `within`：何を一定にして比べるか

- 同じ es の値でも、再訪しやすさはプレイヤーによっても、ボットによっても違う。
- そこで `within` は、比べる相手を同じプレイヤー（または同じプレイヤーとボットの組）のセッションに限り、そのプレイヤー（組）がもともと持っている再訪しやすさの差を取り除く。
- 例：プレイヤーAは再訪率が平均70%、プレイヤーBは平均30%だとする（数字は説明のための仮のもの）。
  - この2人を混ぜて比べると、「Aは易しいボットと多く当たっていた」のような偶然が、es の効果に見えてしまう。
  - `within` では、Aの中ではAの平均との差、Bの中ではBの平均との差だけを見る。

`within` の値は次の2つである。

- `player`（プレイヤー内）：同じプレイヤーの、ほかのセッションとだけ比べる。
  - 例：Aは、ふだん互角のボットとの対局の後に70%の確率で戻ってくる。そのAが、自分にとって易しすぎるボットに当たった後は、戻る確率が65%に下がった。このとき、効果は「−5ポイント」と数える。
  - 問い（Q2a）：同じ人が、自分にとっていつもより易しい（難しい）ボットに当たったとき、戻る割合は上がるか、下がるか。
  - 仕組み：各プレイヤー自身の平均的な再訪率を取り除く（プレイヤーの固定効果；Wooldridge, 2010, 10章）。
- `pair`（ペア内）：さらに厳しく、同じプレイヤーが同じボットと指した、ほかのセッションとだけ比べる。`pair` の行は `same bot` にだけある。
  - 例：AはボットXと何か月にもわたって何度も指す。AとXのレーティングは時間とともに動くので、同じ組でも es はセッションごとに変わる。Aが勝ち続けてレーティングが上がった時期は、XはAから見て易しい（es が大きい）。Aが負け続けて下がった時期は、同じXが難しい（es が小さい）。
  - 問い（Q2d）：Xが相対的に難しかった時期の後と、易しかった時期の後とで、AがXに戻る割合はどう違うか。
  - 仕組み：各プレイヤー・ボットの組自身の平均的な再訪率を取り除く。そのため、プレイヤーが何度も戻ってくるお気に入りのボットがいるというだけでは、結果は生じない。

つまり、`player` はどの相手と指すかの違いを含めて「その人の中」で比べ、`pair` は相手のボットまで固定して「その組の中」で比べる。`pair` のほうが、比べる相手が少なく、条件が厳しい。

#### 表のそのほかの列

- `days`：再訪を数える期間（7、28、91日）。
- `n_obs`：使ったセッションの数。
- `es`、`es2`：曲線の2つの項（用語の b と c）。
- `es_p`、`es2_p`：それぞれの p 値。`es2_se`：`es2` の標準誤差。
- `peak_es`、`peak_ci_low`〜`peak_ci_high`：山の頂上と、その95%区間。

#### 確認すべき点

どの行でも es2 が負で、頂点が0.5〜0.6付近にあること。
""",
    ),
    code(
        r'''
OUTCOME_TERM = "C(outcome, Treatment('win'))"  # result dummies, win as the reference
CONTROLS = "C(speed) + player_elo_c + log_pair_idx"
FRAME_COLUMNS = [
    "outcome", "es", "n_plies_100", "speed", "player_elo_c", "log_pair_idx", "month", "player",
    "pair",
]
GAME_CONTROLS = f"es + I(es**2) + n_plies_100 + {CONTROLS}"
RETURN_WINDOWS_D = (7, 28, 91)
MIN_RETURN_ROWS = 1_000  # session ends a return window needs


def difficulty_row(model: ModelResult, **labels: Any) -> dict[str, Any]:
    """The curve terms and the peak of a model, as one table row."""
    top = peak(model)
    es, es2 = model.term(ES), model.term(ES2)
    return {
        **labels, "n_obs": model.n_obs, "es": es["estimate"], "es_p": es["p_value"],
        "es2": es2["estimate"], "es2_se": es2["std_err"], "es2_p": es2["p_value"],
        "peak_es": top["es"], "peak_ci_low": top["ci_low"], "peak_ci_high": top["ci_high"],
    }


def return_targets(days: int) -> tuple[tuple[str, str, str], ...]:
    """(outcome column, session-end flag, target) of the same-bot and the any-bot return."""
    return (
        (f"return_{days}d", "session_last", "same bot"),
        (f"any_return_{days}d", "player_session_last", "any bot"),
    )


def comparisons(target: str) -> tuple[str, ...]:
    """Whom a session is compared with; within pair exists only for the same bot."""
    return ("pair", "player") if target == "same bot" else ("player",)


def horizon_rows(panel: pl.DataFrame) -> list[dict[str, Any]]:
    """Curve terms of the return models at 7, 28 and 91 days (same bot and any bot)."""
    rows = []
    rhs = f"{OUTCOME_TERM} + {GAME_CONTROLS} + C(month)"
    for days in RETURN_WINDOWS_D:
        for outcome, flag, target in return_targets(days):
            data = panel.filter(pl.col(flag) & pl.col(outcome).is_not_null())
            if data.height < MIN_RETURN_ROWS:
                continue
            frame = to_model_frame(data, [outcome, *FRAME_COLUMNS])
            for within in comparisons(target):
                name = f"{target} return within {days} days, within {within}"
                model = fit_fe_lpm(frame, f"{outcome} ~ {rhs}", within, "player", name)
                rows.append(difficulty_row(model, target=target, days=days, within=within))
            del frame
    return rows
''',
        self_contained=True,
    ),
    code(
        r"""
horizons = cached("panel_horizons", lambda: horizon_rows(panel_games()))
pl.DataFrame(horizons)
""",
    ),
    md(
        """
#### 図の読み方

図「より長い期間の曲線」：上の表のプレイヤー内の4行（同じボットへの7・28・91日の再訪と、ボットとの対局そのものへの7日の再訪）から得られる曲線を、互角（es = 0.5）を基準に描いたもの。縦軸は再訪の変化（パーセントポイント）である。
""",
    ),
    code(
        r"""
# figure: the curves implied by the within-player horizon models, relative to es = 0.5
grid = np.linspace(0.02, 0.98, 97)
fig, (ax,) = new_figure(1, width=5.6, height=3.6)
ax.axhline(0, color=NEUTRAL, linewidth=1)
shown = [("same bot", 7, SERIES[0]), ("same bot", 28, SERIES[1]), ("same bot", 91, SERIES[2]),
         ("any bot", 7, SERIES[3])]
for target, days, color in shown:
    row = next(
        r for r in horizons if (r["target"], r["days"], r["within"]) == (target, days, "player")
    )
    change = row["es"] * grid + row["es2"] * grid**2 - (row["es"] * 0.5 + row["es2"] * 0.25)
    ax.plot(grid, 100 * change, color=color, label=f"{target}, {days} days")
ax.set_xlabel("Player's expected score vs the bot")
ax.set_ylabel("Return vs an even game (pp)")
ax.set_title("The curve at longer horizons (result held fixed)")
ax.legend()
display(Image(filename=save_figure(fig, FIGURE_DIR / "d1_horizons.png")))
""",
    ),
    md(
        r"""
### 2.4 逆U字の検定：2直線の検定

9本のモデルのそれぞれで、曲線が山の形かどうかを判定する（Q2a〜Q2e）。この段階の逆U字の判定は、この検定だけで行う。

#### なぜ必要か

- es² の項 $c$ が負であることが示すのは、曲線が上に凸であることだけである。頂点 $-b / (2c)$ がデータの範囲の外にあれば、範囲の中の曲線は上がるだけか、下がるだけである（Lind & Mehlum, 2010；Haans et al., 2016）。
- さらに、真の曲線が上がってから平らになるだけのときにも、2次式による検定は偽の頂点を示しうる（Simonsohn, 2018）。
- そこで、2次式を使わずに山の両側を別々の直線で表す、2直線の検定（Simonsohn, 2018）で逆U字を判定する。

#### 手順

Simonsohn（2018）の公開コード（twolines.R, v0.52）の手順に従う。

1. **向きを決める。** es と es² の2次式を当てはめ、es の最小値での傾きが正なら逆U字の向き（山）、そうでなければU字の向き（谷）として、以下を進める。
2. **一般化加法モデルを当てはめる。** es の3次回帰スプライン（基底の数10、節点は es の異なる値に等間隔に置く）と、2次式以外の統制変数を入れた一般化加法モデルを `fit_fe_gam()` で当てはめる（Wood, 2017）。滑らかさは一般化交差検証（GCV）で選ぶ。
3. **平らな上部を決める。** es の10〜90パーセンタイルの範囲のセッションについて、モデルの予測値 $\hat y$ とその標準誤差 $\mathrm{se}$ を求める。山の向きなら、$\hat y + \mathrm{se}$ がその範囲での $\hat y$ の最大値を超えるセッションの es を「平らな上部」$x_\mathrm{flat}$ とする（`flat_top()`）。
4. **最初の区切り。** 区切り $x_c$ を $x_\mathrm{flat}$ の中央値に置き、2本の直線を当てはめる（下の5）。
5. **2本の直線。** 主なモデルの $b\,\mathrm{es} + c\,\mathrm{es}^2$ を、次の3項に置き換えて `fit_fe_lpm()` で推定する（`split_at()`、`two_slopes()`）。
   - `es_low` = $\mathrm{es} - x_c$（区切りより難しい側。それ以外は0）：難しい側の傾き $b_1$
   - `es_high` = $\mathrm{es} - x_c$（区切りより易しい側。それ以外は0）：易しい側の傾き $b_2$
   - `high`：易しい側なら1。区切りでの段差を許す。
   - 区切りちょうどの es は、$b_1$ を推定する回帰では難しい側に、$b_2$ を推定する回帰では易しい側に入れる。原法と同じく、1本の直線につき1回、計2回当てはめる。
6. **区切りを動かす（Robin Hood 法）。** 4で得た2本の傾きの $|z_1|$、$|z_2|$ から、区切りを $x_\mathrm{flat}$ の $|z_2| / (|z_1| + |z_2|)$ 分位点に移し、もう一度2本の直線を当てはめる（`robin_hood()`）。弱い（|z| が小さい）直線により多くのデータを与えるためである。報告するのはこの2回目の推定である。
7. **判定。** $b_1$ と $b_2$ の符号が逆で、どちらも両側 p < 0.05 なら、U字または逆U字と判定する。

#### 原法との違い

- **プレイヤーの固定効果。** 原法は固定効果を想定しない。ここでは、主なモデルと同じく、一般化加法モデルにも2本の直線にもプレイヤー（ペア内のモデルでは組）の固定効果を入れる。
  - `fit_fe_gam()` は、スプラインの基底とほかのすべての列から各プレイヤーの平均を引き、罰則付き最小二乗法を当てはめる。罰則のない固定効果を取り除いても、残りの推定値は変わらない（Frisch–Waugh–Lovell の定理；Wooldridge, 2010）。
  - GCV の有効自由度には、固定効果の数を足す。
  - 予測値は、統制変数を平均に置いたときの値から定数を除いたもの（スプラインの部分）である。予測値の差は定数によらないが、標準誤差もスプラインの部分だけのものなので、原法の標準誤差（定数の不確かさを含む）とは少し異なる。
- **2本の直線の標準誤差。** 原法は HC3 を使う。ここでは、同じプレイヤーのセッションが独立でないので、ほかのモデルと同じくプレイヤー単位のクラスター頑健標準誤差を使う（Cameron & Miller, 2015）。

#### 設定

- 2.3の9本のモデル（対局の結果を入れる）すべてに適用する。
- 7日の同じボットへの再訪・プレイヤー内のモデルでは、対局の結果を入れない場合も推定する（Q2c で、入れる場合と比べるため）。
- ペア内のモデルでは、一般化加法モデルにも2本の直線にも、プレイヤーの代わりにプレイヤーとボットの組の固定効果を入れる。標準誤差はどのモデルでもプレイヤー単位でクラスター化する。

#### 表の読み方

- `target`、`days`、`within`：2.3の表と同じモデルの区別。`with_result`：対局の結果を入れたか。
- `shape`：手順1の向き（`inverted U` なら山）。
- `gam_edf`：一般化加法モデルのスプラインの有効自由度。
- `flat_low`〜`flat_high`：平らな上部の es の範囲。区切りを決めるための手順の一部で、標本が大きいほど狭くなるので、頂上の幅を表すものではない。`breakpoint_first`、`breakpoint`：最初の区切りと、Robin Hood 法で動かした区切り。
- `slope_hard`、`slope_easy`：$b_1$ と $b_2$（es が1増えたときの再訪の変化。0.1増えたときは、その10分の1）。それぞれの95%区間と p 値。`slope_hard_z`、`slope_easy_z` は z 統計量（傾き ÷ 標準誤差。標準誤差は95%区間の幅から求める）。
- `u_shape`：手順7の判定。

#### 確認すべき点

すべての行で、`shape` が `inverted U` で、`u_shape` が true であること。

定義の後の検査では、人工データを使って次を確かめる。

- 節点が mgcv の置き方と同じになり、罰則行列が直線を罰しないこと。
- 一般化加法モデルが、プレイヤーごとの水準の違いがあっても、人工の山の形を復元すること。
- 平らな上部、2本の直線の変数、Robin Hood 法の区切りが、既知の答えを返すこと。
- 人工の折れ線のデータから、2本の傾きが復元されること。
""",
    ),
    code(
        r'''
GAM_BASIS = 10  # basis size of the cubic regression spline, as in twolines.R (k = 10)
GAM_LOG_LAMBDAS = np.linspace(-20.0, 20.0, 81)  # smoothing parameters searched (log, rescaled)
MIDDLE = (0.1, 0.9)  # quantiles of es between which the flat top is sought


def place_knots(x: np.ndarray, n_knots: int) -> np.ndarray:
    """Knots of mgcv's cubic regression spline: spread evenly through the unique values."""
    unique = np.unique(x)
    delta = (unique.size - 1) / (n_knots - 1)
    steps = delta * np.arange(1, n_knots - 1)
    lower = np.floor(steps).astype(int)
    frac = steps - lower
    inner = unique[lower] * (1 - frac) + unique[np.minimum(lower + 1, unique.size - 1)] * frac
    return np.concatenate([[unique[0]], inner, [unique[-1]]])


def cr_basis(x: np.ndarray, knots: np.ndarray) -> np.ndarray:
    """Cubic regression spline basis; its coefficients are the curve's values at the knots."""
    return np.asarray(patsy.dmatrix(
        "cr(x, knots=inner, lower_bound=low, upper_bound=high) - 1",
        {"x": x, "inner": knots[1:-1], "low": knots[0], "high": knots[-1]},
    ))


def cr_penalty(knots: np.ndarray) -> np.ndarray:
    """Integrated squared second derivative of the spline, as a matrix in its coefficients."""
    h = np.diff(knots)
    k = knots.size
    d = np.zeros((k - 2, k))
    b = np.zeros((k - 2, k - 2))
    for i in range(k - 2):
        d[i, i], d[i, i + 1], d[i, i + 2] = 1 / h[i], -1 / h[i] - 1 / h[i + 1], 1 / h[i + 1]
        b[i, i] = (h[i] + h[i + 1]) / 3
        if i < k - 3:
            b[i, i + 1] = b[i + 1, i] = h[i + 1] / 6
    return d.T @ np.linalg.solve(b, d)


@dataclass(frozen=True)
class SmoothFit:
    """A fitted smooth of one variable: its basis, coefficients and their covariance."""

    knots: np.ndarray
    constraint: np.ndarray  # maps the centred coefficients to the knot values
    coef: np.ndarray
    cov: np.ndarray  # Bayesian covariance of coef, as mgcv's Vp
    edf: float

    def predict(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """The smooth and its standard error at x."""
        basis = cr_basis(x, self.knots) @ self.constraint
        se = np.sqrt(np.einsum("ij,jk,ik->i", basis, self.cov, basis))
        return basis @ self.coef, se


def demean(values: np.ndarray, keys: np.ndarray) -> np.ndarray:
    """Subtracts each group's mean from every column."""
    return values - pd.DataFrame(values).groupby(keys).transform("mean").to_numpy()


def fit_fe_gam(
    df: pd.DataFrame, formula: str, smooth: str, fe: str, knots: np.ndarray | None = None
) -> SmoothFit:
    """Gaussian GAM: a spline in `smooth`, the linear terms of `formula`, fixed effects for `fe`.

    The smoothing parameter minimises GCV (Wood, 2017). Knots are placed as mgcv does unless given.
    """
    data = df.dropna(subset=[fe, smooth])
    y, x = patsy.dmatrices(formula, data, return_type="dataframe")
    x = x.drop(columns=[c for c in x.columns if c == "Intercept"])
    used = data.loc[x.index, fe]
    informative = (used.groupby(used).transform("size") > 1).to_numpy()
    y, x = y[informative], x[informative]
    keys = data.loc[x.index, fe].to_numpy()
    s = data.loc[x.index, smooth].to_numpy(dtype=float)
    knots = place_knots(s, GAM_BASIS) if knots is None else knots
    basis = cr_basis(s, knots)
    # sum-to-zero constraint, as mgcv: drop the direction of the basis column sums
    q, _ = np.linalg.qr(basis.sum(axis=0)[:, None], mode="complete")
    constraint = q[:, 1:]
    linear = demean(x.to_numpy(dtype=float), keys)
    linear = linear[:, np.abs(linear).sum(axis=0) > 1e-12]
    z = np.hstack([linear, demean(basis @ constraint, keys)])
    y_dm = demean(y.to_numpy(dtype=float), keys)[:, 0]
    m, r, yy = z.T @ z, z.T @ y_dm, float(y_dm @ y_dm)
    n_lin = linear.shape[1]
    penalty = np.zeros_like(m)
    penalty[n_lin:, n_lin:] = constraint.T @ cr_penalty(knots) @ constraint
    scale = np.linalg.norm(m[n_lin:, n_lin:]) / np.linalg.norm(penalty)
    n, n_groups = y_dm.size, np.unique(keys).size

    def fit(log_lambda: float) -> tuple[float, np.ndarray, np.ndarray, float, float]:
        a = m + scale * math.exp(log_lambda) * penalty
        beta = np.linalg.solve(a, r)
        rss = yy - 2 * beta @ r + beta @ m @ beta
        edf_terms = np.diag(np.linalg.solve(a, m))
        dof = n - n_groups - edf_terms.sum()
        return n * rss / dof**2, beta, a, rss / dof, float(edf_terms[n_lin:].sum())

    best = min(GAM_LOG_LAMBDAS, key=lambda v: fit(v)[0])
    step = GAM_LOG_LAMBDAS[1] - GAM_LOG_LAMBDAS[0]
    refined = optimize.minimize_scalar(
        lambda v: fit(v)[0], bounds=(best - step, best + step), method="bounded"
    )
    _, beta, a, sigma2, edf = fit(float(refined.x))
    cov = sigma2 * np.linalg.inv(a)
    return SmoothFit(knots, constraint, beta[n_lin:], cov[n_lin:, n_lin:], edf)


def flat_top(x: np.ndarray, fit: np.ndarray, se: np.ndarray, *, inverted: bool) -> np.ndarray:
    """The x values whose fit is within 1 SE of the most extreme fit (twolines.R)."""
    if inverted:
        return x[fit + se > fit.max()]
    return x[fit - se < fit.min()]


def split_at(frame: pd.DataFrame, breakpoint: float, *, break_low: bool) -> pd.DataFrame:
    """Adds the two-lines terms; the breakpoint itself joins the low side if break_low."""
    low = frame["es"] <= breakpoint if break_low else frame["es"] < breakpoint
    gap = frame["es"] - breakpoint
    return frame.assign(
        es_low=np.where(low, gap, 0.0), es_high=np.where(low, 0.0, gap), high=(~low).astype(int)
    )


def two_slopes(
    frame: pd.DataFrame, breakpoint: float, formula: str, within: str
) -> dict[str, dict[str, float]]:
    """The slope below and above the breakpoint, each from its own fit (twolines.R)."""
    slopes = {}
    for side, term, break_low in (("hard", "es_low", True), ("easy", "es_high", False)):
        data = split_at(frame, breakpoint, break_low=break_low)
        model = fit_fe_lpm(data, formula, within, "player", f"two lines, {side} side")
        slopes[side] = {**model.term(term), "n_obs": model.n_obs}
    return slopes


def robin_hood(flat_es: np.ndarray, z_hard: float, z_easy: float) -> float:
    """Moves the breakpoint so that the weaker line gets more data (Simonsohn, 2018)."""
    return float(np.quantile(flat_es, abs(z_easy) / (abs(z_hard) + abs(z_easy))))


def z_value(slope: dict[str, float]) -> float:
    """The z statistic of a slope."""
    return slope["estimate"] / slope["std_err"]


def two_lines_specs() -> list[dict[str, Any]]:
    """The nine horizon models (result held fixed), and the 7-day same-bot one without it."""
    base = {
        "target": "same bot", "days": 7, "within": "player", "outcome": "return_7d",
        "flag": "session_last", "with_result": False,
    }
    specs = [base]
    for days in RETURN_WINDOWS_D:
        for outcome, flag, target in return_targets(days):
            for within in comparisons(target):
                specs.append({
                    "target": target, "days": days, "within": within, "outcome": outcome,
                    "flag": flag, "with_result": True,
                })
    return specs


def two_lines(
    panel: pl.DataFrame, *, outcome: str, flag: str, within: str, with_result: bool
) -> dict[str, Any]:
    """Two-lines test (Simonsohn, 2018) of a return model in es, within player or pair."""
    data = panel.filter(pl.col(flag) & pl.col(outcome).is_not_null())
    frame = to_model_frame(data, [outcome, *FRAME_COLUMNS])
    rest = f"{OUTCOME_TERM + ' + ' if with_result else ''}n_plies_100 + {CONTROLS} + C(month)"
    es = frame["es"].dropna().to_numpy()
    # 1. direction: the quadratic's slope at the lowest es
    quadratic = fit_fe_lpm(frame, f"{outcome} ~ {ES} + {ES2} + {rest}", within, "player", "q")
    inverted = quadratic.term(ES)["estimate"] + 2 * quadratic.term(ES2)["estimate"] * es.min() > 0
    # 2-3. flat top of the GAM within the middle 80% of es
    smooth = fit_fe_gam(frame, f"{outcome} ~ {rest}", "es", within)
    low, high = np.quantile(es, MIDDLE)
    middle = es[(es > low) & (es < high)]
    values, index = np.unique(middle, return_inverse=True)
    fit, se = smooth.predict(values)
    flat = flat_top(middle, fit[index], se[index], inverted=inverted)
    # 4-6. lines at the median of the flat top, then at the Robin Hood breakpoint
    first_break = float(np.median(flat))
    lines = f"{outcome} ~ es_low + es_high + high + {rest}"
    first = two_slopes(frame, first_break, lines, within)
    breakpoint = robin_hood(flat, z_value(first["hard"]), z_value(first["easy"]))
    hard, easy = two_slopes(frame, breakpoint, lines, within).values()
    return {
        "n_obs": hard["n_obs"],
        "shape": "inverted U" if inverted else "U", "gam_edf": smooth.edf,
        "flat_low": float(flat.min()), "flat_high": float(flat.max()),
        "breakpoint_first": first_break, "breakpoint": breakpoint,
        "slope_hard": hard["estimate"], "slope_hard_ci_low": hard["ci_low"],
        "slope_hard_ci_high": hard["ci_high"], "slope_hard_p": hard["p_value"],
        "slope_easy": easy["estimate"], "slope_easy_ci_low": easy["ci_low"],
        "slope_easy_ci_high": easy["ci_high"], "slope_easy_p": easy["p_value"],
        "u_shape": bool(
            hard["estimate"] * easy["estimate"] < 0
            and hard["p_value"] < ALPHA and easy["p_value"] < ALPHA
        ),
    }


# check 1: knots as mgcv places them, and a penalty that leaves straight lines alone
knots = place_knots(np.arange(11.0), 5)
assert np.allclose(knots, [0.0, 2.5, 5.0, 7.5, 10.0])
uneven = np.array([0.0, 0.1, 0.35, 0.5, 0.8, 1.0])
assert np.allclose(cr_penalty(uneven) @ uneven, 0.0) and np.allclose(cr_penalty(uneven).sum(1), 0)

# check 2: a made-up hill (top at 0.5) is recovered despite player levels and a covariate
rng = np.random.default_rng(2)
hill_player = np.repeat(np.arange(400), 25)
hill_es = rng.uniform(size=hill_player.size)
hill_z = rng.normal(size=hill_player.size)
hill = pd.DataFrame({
    "y": -((hill_es - 0.5) ** 2) + 0.2 * hill_z + rng.normal(size=400)[hill_player]
    + rng.normal(scale=0.05, size=hill_player.size),
    "es": hill_es, "z": hill_z, "player": hill_player,
})
hill_fit = fit_fe_gam(hill, "y ~ z", "es", "player")
grid_es = np.linspace(0.05, 0.95, 91)
grid_fit, _ = hill_fit.predict(grid_es)
assert abs(grid_es[np.argmax(grid_fit)] - 0.5) < 0.05
truth = -((grid_es - 0.5) ** 2)
assert np.allclose(grid_fit - grid_fit.mean(), truth - truth.mean(), atol=0.01)

# check 3: the flat top, the two-lines terms, and the Robin Hood breakpoint
assert flat_top(np.array([0.1, 0.2, 0.3]), np.array([0.0, 1.0, 0.9]), np.array([0.15] * 3),
                inverted=True).tolist() == [0.2, 0.3]
split = split_at(pd.DataFrame({"es": [0.2, 0.5, 0.8]}), 0.5, break_low=True)
assert np.allclose(split["es_low"], [-0.3, 0.0, 0.0]) and split["high"].tolist() == [0, 0, 1]
split = split_at(pd.DataFrame({"es": [0.2, 0.5, 0.8]}), 0.5, break_low=False)
assert np.allclose(split["es_high"], [0.0, 0.0, 0.3]) and split["high"].tolist() == [0, 1, 1]
assert math.isclose(robin_hood(np.linspace(0, 1, 101), 3.0, -1.0), 0.25)

# check 4: a made-up kinked curve (rising 0.3, falling 0.1, kink at 0.5) is recovered
kink_player = np.repeat(np.arange(300), 30)
kink_es = rng.uniform(size=kink_player.size)
kink_y = np.where(kink_es < 0.5, 0.3 * (kink_es - 0.5), -0.1 * (kink_es - 0.5))
kinked = split_at(pd.DataFrame({
    "y": kink_y + rng.normal(scale=0.05, size=kink_es.size), "es": kink_es, "player": kink_player,
}), 0.5, break_low=True)
fit = fit_fe_lpm(kinked, "y ~ es_low + es_high + high", "player", "player", "kinked")
assert abs(fit.term("es_low")["estimate"] - 0.3) < 0.02
assert abs(fit.term("es_high")["estimate"] + 0.1) < 0.02
print("checks passed")
''',
        self_contained=True,
    ),
    code(
        r'''
def find_spec(target: str, days: int, within: str, *, with_result: bool) -> dict[str, Any]:
    """The model of two_lines_specs() with these labels."""
    wanted = (target, days, within, with_result)
    return next(
        s for s in two_lines_specs()
        if (s["target"], s["days"], s["within"], s["with_result"]) == wanted
    )


MAIN_SPEC = find_spec("same bot", 7, "player", with_result=True)  # the main model of 2.2
FREE_SPEC = find_spec("same bot", 7, "player", with_result=False)  # the same, result free
SPEC_LABELS = ("target", "days", "within", "with_result")


def spec_key(spec: dict[str, Any]) -> str:
    """Short name of a model, used in the names of saved fits."""
    result = "result" if spec["with_result"] else "no_result"
    return f"{spec['target'].replace(' ', '_')}_{spec['days']}d_{spec['within']}_{result}"


def spec_label(spec: dict[str, Any]) -> str:
    """Readable name of a model."""
    result = "result held fixed" if spec["with_result"] else "result free"
    return f"{spec['target']}, {spec['days']} d, within {spec['within']}, {result}"


def spec_columns(spec: dict[str, Any]) -> dict[str, Any]:
    """The labels of a model, as columns of a table row."""
    return {key: spec[key] for key in SPEC_LABELS}


def control_terms(spec: dict[str, Any]) -> str:
    """The model's right-hand side without the curve terms."""
    result = f"{OUTCOME_TERM} + " if spec["with_result"] else ""
    return f"{result}n_plies_100 + {CONTROLS} + C(month)"
''',
        self_contained=True,
    ),
    code(
        r'''
shape_tests = [
    {
        **spec_columns(spec),
        **cached(f"panel_two_lines_{spec_key(spec)}", lambda spec=spec: two_lines(
            panel_games(), outcome=spec["outcome"], flag=spec["flag"], within=spec["within"],
            with_result=spec["with_result"],
        )),
    }
    for spec in two_lines_specs()
]
# z of each slope, from its 95% interval (estimate +- Z95 * se)
for row in shape_tests:
    for side in ("hard", "easy"):
        se = (row[f"slope_{side}_ci_high"] - row[f"slope_{side}_ci_low"]) / (2 * Z95)
        row[f"slope_{side}_z"] = row[f"slope_{side}"] / se
pl.DataFrame(shape_tests)
''',
    ),
    md(
        """
#### 図1のコード

図1は、モデルを使わない生の値と、2直線の検定の曲線を並べる。

- `session_ends()`：7日再訪が判明している各セッションの最後の対局を残す。
- `binned_return()`：幅0.05の期待スコアのビンごとに、セッション数と7日以内の再訪数を数える。続くセルは、49か月それぞれでこの数を集める（または保存済みの結果を読み込む）。
- `wilson_interval()`：割合の Wilson の95%区間（Wilson, 1927）。
- `two_lines_curve()`：2直線の検定の手順2の一般化加法モデルを当て直し、es の格子の上での曲線とその標準誤差を返す。図に描くためだけのもので、判定には使わない。当て直した曲線の有効自由度が、上の表の `gam_edf` と一致することを確かめる（`assert`）。
""",
    ),
    code(
        r'''
BIN_WIDTH = 0.05


def session_ends(games: pl.DataFrame) -> pl.DataFrame:
    """Last games of sessions whose 7-day return is known."""
    return games.filter(pl.col("session_last") & pl.col("return_7d").is_not_null())


def binned_return(sessions: pl.DataFrame) -> pl.DataFrame:
    """Sessions (n) and 7-day returns (k) per expected-score bin, labelled by its middle."""
    n_bins = round(1 / BIN_WIDTH)
    middle = (pl.col("es") / BIN_WIDTH).floor().clip(0, n_bins - 1) * BIN_WIDTH + BIN_WIDTH / 2
    return (
        sessions.with_columns(middle.alias("es_mid"))
        .group_by("es_mid")
        .agg(pl.len().alias("n"), pl.col("return_7d").cast(pl.Float64).sum().alias("k"))
        .sort("es_mid")
    )


made_up = pl.DataFrame({
    "session_last": [True, True, False, True], "return_7d": [True, False, True, None],
    "es": [0.51, 0.53, 0.1, 0.9],
})
assert session_ends(made_up).height == 2
assert binned_return(session_ends(made_up)).to_dicts() == [{"es_mid": 0.525, "n": 2, "k": 1.0}]
print("checks passed")
''',
        self_contained=True,
    ),
    code(
        r'''
def binned_month(month: str) -> list[dict[str, Any]]:
    """The binned session and return counts of one month."""
    return binned_return(session_ends(load_month(month, bots))).to_dicts()


binned_months = {m: cached(f"binned_{m}", lambda m=m: binned_month(m)) for m in STUDY_MONTHS}
''',
    ),
    code(
        r'''
def wilson_interval(successes: float, n: float) -> tuple[float, float]:
    """95% Wilson score interval of a proportion."""
    p = successes / n
    denom = 1 + Z95**2 / n
    centre = (p + Z95**2 / (2 * n)) / denom
    half = Z95 * math.sqrt(p * (1 - p) / n + Z95**2 / (4 * n * n)) / denom
    return centre - half, centre + half


CURVE_POINTS = 99  # grid points of a drawn smooth


def two_lines_curve(panel: pl.DataFrame, spec: dict[str, Any]) -> dict[str, Any]:
    """The GAM of a two-lines test (its step 2) on a grid of es, for drawing only."""
    data = panel.filter(pl.col(spec["flag"]) & pl.col(spec["outcome"]).is_not_null())
    frame = to_model_frame(data, [spec["outcome"], *FRAME_COLUMNS])
    formula = f"{spec['outcome']} ~ {control_terms(spec)}"
    smooth = fit_fe_gam(frame, formula, "es", spec["within"])
    grid = np.linspace(smooth.knots[0], smooth.knots[-1], CURVE_POINTS)
    fit, se = smooth.predict(grid)
    return {"edf": smooth.edf, "es": grid.tolist(), "fit": fit.tolist(), "se": se.tolist()}


# check: Wilson's interval holds the proportion and narrows with n
low, high = wilson_interval(30, 100)
wide_low, wide_high = wilson_interval(300, 1000)
assert low < 0.3 < high and wide_high - wide_low < high - low
print("checks passed")
''',
        self_contained=True,
    ),
    code(
        r'''
def two_lines_row(spec: dict[str, Any]) -> dict[str, Any]:
    """The row of shape_tests for a model."""
    return next(r for r in shape_tests if all(r[k] == spec[k] for k in SPEC_LABELS))


curves = {
    spec_key(spec): cached(
        f"panel_two_lines_curve_{spec_key(spec)}",
        lambda spec=spec: two_lines_curve(panel_games(), spec),
    )
    for spec in (FREE_SPEC, MAIN_SPEC)
}
# the redrawn smooth is the one the test used
for spec in (FREE_SPEC, MAIN_SPEC):
    assert math.isclose(curves[spec_key(spec)]["edf"], two_lines_row(spec)["gam_edf"], rel_tol=1e-6)
''',
    ),
    md(
        """
#### 図の読み方

図「再訪の曲線」：

- 左：モデルを使わない生の値。49か月分の月ごとの表を合算し、期待スコアごとに、7日以内の再訪があったセッションの割合を Wilson の95%区間とともに示す。セッションが100未満のビンは省く。プレイヤーの間の違い（例えば、とても難しい相手やとても易しい相手と指す人は、もともと戻りにくい）を含むので、下がり方の大きさは、同じプレイヤーの中で比べた値（段階3の Binscatter）よりずっと大きい。
- 中・右：2直線の検定（7日・同じボット・プレイヤー内、4年分のパネル。中は結果を統制しない、右は統制する）。
  - 青い線と帯：一般化加法モデルの es の曲線（スプラインの部分で、データの上の平均が0になるよう中心化したもの）と、その95%区間。
  - 灰色の帯：平らな上部。点線：区切り。
  - 破線の2本：難しい側と易しい側の直線。凡例に、es が0.1増えたときの再訪の変化（ポイント）と p 値を示す。直線の高さはプレイヤーの固定効果に吸収されて推定されないので、区切りでの曲線の値を通るように描いた。推定値なのは傾きだけである。

#### 出力の読み方

- 10本すべてで `shape` が `inverted U`、`u_shape` が true である。区切りはどれも es 0.45〜0.49 にある。
- 図の2本の直線は、難しい側で上がり（傾きが正）、易しい側で下がる（傾きが負）。どちらも有意なので、山の形（逆U字）と判定される。
""",
    ),
    code(
        r'''
# figure 1: the raw rate over all monthly tables, and the two-lines test
binned = (
    pl.DataFrame([row for rows in binned_months.values() for row in rows])
    .group_by("es_mid")
    .agg(pl.col("n").sum(), pl.col("k").sum())
    .sort("es_mid")
    .with_columns((pl.col("k") / pl.col("n")).alias("rate"))
)
shown_bins = binned.filter(pl.col("n") >= 100)
bounds = [wilson_interval(k, n) for k, n in zip(shown_bins["k"], shown_bins["n"], strict=True)]
raw_rate = shown_bins["rate"].to_numpy()
raw_low, raw_high = (np.array(side) for side in zip(*bounds, strict=True))


def draw_raw_rate(ax: Axes) -> None:
    """Draws the raw 7-day return rate per es bin with its Wilson intervals on ax."""
    # error bars with caps, since a shaded band of at most 1.5 points hides under the markers
    ax.errorbar(
        shown_bins["es_mid"].to_numpy(), raw_rate, yerr=[raw_rate - raw_low, raw_high - raw_rate],
        color=SERIES[0], marker="o", markersize=3, linewidth=1, elinewidth=1.2, capsize=3,
        label="rate with 95% Wilson CI",
    )
    ax.set_xlabel("Player's expected score vs the bot")
    ax.set_ylabel("7-day return rate (raw)")
    ax.set_title("Raw rate (all months)")
    ax.legend(fontsize=7, loc="lower center")


# the raw rate alone, for the paper's figure 1
raw_fig, (raw_ax,) = new_figure(1, width=4.2, height=3.6)
draw_raw_rate(raw_ax)
display(Image(filename=save_figure(raw_fig, FIGURE_DIR / "d1_return_raw.png")))

fig, (ax_raw, ax_free, ax_main) = new_figure(3, width=4.2, height=3.6)
draw_raw_rate(ax_raw)
for ax, spec in zip((ax_free, ax_main), (FREE_SPEC, MAIN_SPEC), strict=True):
    curve, test = curves[spec_key(spec)], two_lines_row(spec)
    es_grid, smooth, smooth_se = (np.array(curve[key]) for key in ("es", "fit", "se"))
    ax.axvspan(test["flat_low"], test["flat_high"], color=NEUTRAL, alpha=0.2, lw=0)
    ax.fill_between(
        es_grid, 100 * (smooth - Z95 * smooth_se), 100 * (smooth + Z95 * smooth_se),
        color=SERIES[0], alpha=0.15, lw=0,
    )
    ax.plot(es_grid, 100 * smooth, color=SERIES[0], label="GAM smooth")
    breakpoint = test["breakpoint"]
    at_break = float(np.interp(breakpoint, es_grid, smooth))
    sides = (
        ("hard", es_grid[0], breakpoint, SERIES[1]), ("easy", breakpoint, es_grid[-1], SERIES[2])
    )
    for side, left, right, color in sides:
        slope, p_value = test[f"slope_{side}"], test[f"slope_{side}_p"]
        xs = np.array([left, right])
        ax.plot(
            xs, 100 * (at_break + slope * (xs - breakpoint)), color=color, linestyle="--",
            label=f"{side} side: {10 * slope:+.1f} pp per 0.1, p = {p_value:.1g}",
        )
    ax.axvline(breakpoint, color=NEUTRAL, linestyle=":", linewidth=1)
    ax.set_xlabel("Player's expected score vs the bot")
    ax.set_title("Two lines: " + spec_label(spec).split(", ", 3)[-1])
    ax.legend(fontsize=7)
ax_free.set_ylabel("Smooth of es (pp, centred)")
display(Image(filename=save_figure(fig, FIGURE_DIR / "d1_return_curve.png")))
''',
    ),
]
"""The cells, in notebook order."""
