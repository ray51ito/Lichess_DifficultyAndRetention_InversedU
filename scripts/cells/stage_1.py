"""Notebook cells of stage 1: the data and the games used.

Names used from earlier stages:
    stage 0: Any, config, display, math, pl
"""

from __future__ import annotations

import nbformat

from .common import code, md

CELLS: list[nbformat.NotebookNode] = [
    md(
        """
## 1. データの中身と、使う対局

### 問い

- データの1行には何が入っているか。
- どの対局を分析に含めるか。
- 期待スコア、セッション、再訪は、行からどう読み取れるか。

### データ

- 月ごとに表 `player_games.parquet` が1つある。1行が**人間とボットの1局**に当たる。
- 列名は人間の側から付けてある。`player` が人間、`opponent` がボット、`player_score` が人間の結果である。

次のセルは、分析で読む列（月ごとの表と、段階2・3で使う4年分のパネルの表）を挙げ、例として1か月分（2024年12月）を読み込む。
""",
    ),
    code(
        r"""
MONTH_COLUMNS = (
    "game_id", "player", "opponent", "start", "speed", "is_tournament", "player_elo",
    "opponent_elo", "player_score", "expected_score", "outcome", "session_last",
    "session_length", "return_7d", "pair_game_index",
)
PANEL_COLUMNS = (
    *MONTH_COLUMNS, "month", "end", "n_plies", "player_session_last", "return_28d",
    "return_91d", "any_return_7d", "any_return_28d", "any_return_91d",
)

EXAMPLE_MONTH = "2024-12"
raw = pl.read_parquet(
    config.month_dir(EXAMPLE_MONTH) / "player_games.parquet", columns=list(MONTH_COLUMNS)
)
print(f"{EXAMPLE_MONTH}: {raw.height:,} games in player_games.parquet")
pl.DataFrame({"column": raw.columns, "type": [str(t) for t in raw.dtypes]})
""",
    ),
    md(
        """
### 残す対局

次をすべて満たす対局だけを分析に含める。
下のコードでは、各条件が `removal_rules()` の1行に対応しており、どの条件にも当てはまらない対局を残す。

- 「人間」がボットでないこと。人間かどうかを直接確認してはおらず、既知のボットでないアカウントを人間とみなす。判定は2段階である。
  1. 称号による判定：Lichess はボットのアカウントに `BOT` という称号を付けており、ダンプの各対局には双方の称号が記録されている。片方だけにこの称号がある対局をデータに含める。
  2. 一覧による判定：2023年12月〜2024年9月のダンプでは、多くのボットに称号が付いていない。そのため、ボット同士の対局が人間対ボットの対局に見えることがある。こうしたアカウントは一覧 `bot_accounts.parquet` で除く。
     - 一覧に入るのは、いずれかの月に `BOT` 称号付きで現れたアカウントと、称号なしで1か月に10体以上の別々のボットと対戦し、Lichess API で取得したプロフィールに称号があったアカウントである。
     - これらのダンプでは名前の大文字小文字も不揃いなので、名前は小文字の ID で照合する。
     - この期間以外の月では、この条件で除かれる対局が1局もないこともある。

  この判定では、次の2つを見逃す。

  - 通常のアカウントで、裏でエンジンを使う人
  - 1か月の対戦ボットが10体未満の、称号のないボット
- リアルタイムの対局（ブレット、ブリッツ、ラピッド、クラシカル）であること。通信戦は1局に何日もかかるため、セッションが定義できない。
- 大会の対局でないこと。大会では相手をプレイヤーが選べない。
- 双方のレーティングと結果が分かること。

続いて `add_derived()` が、モデルで使う変数を加える。

- `es`：期待スコア
- `player_elo_c`：レーティングを (レーティング − 1500) / 100 にしたもの
- `log_pair_idx`：1 + このボットとそれまでに対戦した局数、の対数
""",
    ),
    code(
        r'''
ANALYSIS_SPEEDS = ("bullet", "blitz", "rapid", "classical")


def removal_rules(bots: set[str]) -> dict[str, pl.Expr]:
    """Each rule that removes a game from the analysis (a game is kept when none applies)."""
    return {
        "the 'human' is a known bot account": pl.col("player").str.to_lowercase().is_in(bots),
        "not a real-time game (e.g. correspondence)": ~pl.col("speed").is_in(ANALYSIS_SPEEDS),
        "tournament game": pl.col("is_tournament"),
        "a rating is missing": pl.col("player_elo").is_null() | pl.col("opponent_elo").is_null(),
        "the result is missing": pl.col("player_score").is_null(),
    }


def analysis_filter(table: pl.DataFrame, bots: set[str]) -> pl.DataFrame:
    """The games no removal rule applies to."""
    return table.filter(~pl.any_horizontal(*removal_rules(bots).values()))


def add_derived(games: pl.DataFrame) -> pl.DataFrame:
    """Adds the model variables es, player_elo_c and log_pair_idx."""
    return games.with_columns(
        pl.col("expected_score").alias("es"),
        ((pl.col("player_elo") - 1500) / 100).alias("player_elo_c"),
        (pl.col("pair_game_index") + 1).log().alias("log_pair_idx"),
    )


def load_bot_accounts() -> set[str]:
    """Lowercase ids of known bot accounts, including those shown without the BOT title."""
    path = config.BOT_ACCOUNTS_PATH
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing; without it untitled bots count as humans")
    return set(pl.read_parquet(path, columns=["user"])["user"].to_list())


def load_games(folder: Any, columns: tuple[str, ...], bots: set[str]) -> pl.DataFrame:
    """The analysis sample of one month's (or the panel's) player_games.parquet."""
    table = pl.read_parquet(folder / "player_games.parquet", columns=list(columns))
    return add_derived(analysis_filter(table, bots))


def load_month(month: str, bots: set[str]) -> pl.DataFrame:
    """The analysis sample of one study month."""
    return load_games(config.month_dir(month), MONTH_COLUMNS, bots)


# checks on made-up rows: only "alice" passes every rule
made_up = pl.DataFrame({
    "player": ["ToromBot", "alice", "bob", "carol", "dave"],
    "speed": ["blitz", "blitz", "correspondence", "rapid", "bullet"],
    "is_tournament": [False, False, False, True, False],
    "player_elo": [1500, 1500, 1500, 1500, None],
    "opponent_elo": [1500] * 5,
    "player_score": [1.0] * 5,
})
assert analysis_filter(made_up, {"torombot"})["player"].to_list() == ["alice"]
derived = add_derived(pl.DataFrame({
    "expected_score": [0.05, 0.55], "player_elo": [1200, 1700], "pair_game_index": [0, 9],
}))
assert derived["player_elo_c"].to_list() == [-3.0, 2.0]
assert math.isclose(derived["log_pair_idx"][1], math.log(10))
print("checks passed")
''',
        self_contained=True,
    ),
    md(
        """
次のセルは、例の月にこれらの条件を適用する。表は、各条件で除かれる対局数を示す（1局が複数の条件に当てはまることもある）。
""",
    ),
    code(
        r"""
bots = load_bot_accounts()
display(pl.DataFrame({
    "reason for removal": list(removal_rules(bots)),
    "games removed": [raw.filter(rule).height for rule in removal_rules(bots).values()],
}))
games = add_derived(analysis_filter(raw, bots))
print(f"kept {games.height:,} of {raw.height:,} games ({100 * games.height / raw.height:.1f}%)")
""",
    ),
    md(
        """
### 1人の人間と1体のボット

次のセルは、例の月にある人間が1体のボットと対戦したすべての対局を示す。

- この組は、決まった規則（4〜6局、2つのセッション、1回の再訪、ほぼ互角の対局）で選んでおり、この段階の考え方が数行で見渡せるようにしてある。
- 人間の名前は `player_A` に置き換えた。ボットは公開アカウントなので名前をそのまま示す。
""",
    ),
    code(
        r'''
# the example: one player-bot pair with 4-6 games, two sessions, one return, near-even games
pairs = games.group_by("player", "opponent").agg(
    pl.len().alias("games"),
    pl.col("session_last").sum().alias("sessions"),
    pl.col("return_7d").sum().alias("returns"),
    pl.col("es").mean().alias("mean_es"),
)
example = (
    pairs.filter(
        pl.col("games").is_between(4, 6)
        & (pl.col("sessions") == 2)
        & (pl.col("returns") == 1)
        & pl.col("mean_es").is_between(0.35, 0.65)
    )
    .sort("player", "opponent")
    .row(0, named=True)
)
SHOWN = [
    "start", "player", "opponent", "speed", "player_elo", "opponent_elo", "player_score",
    "expected_score", "session_length", "session_last", "return_7d", "pair_game_index",
]


def example_rows(table: pl.DataFrame, columns: list[str] = SHOWN) -> pl.DataFrame:
    """The example pair's games in time order, with the player's name replaced."""
    is_pair = (pl.col("player") == example["player"]) & (pl.col("opponent") == example["opponent"])
    return (
        table.filter(is_pair)
        .sort("start")
        .with_columns(pl.lit("player_A").alias("player"))
        .select(columns)
    )


example_rows(raw)
''',
    ),
    md(
        """
### 列の意味

| 列 | 意味 |
|---|---|
| `start` | 対局の開始時刻（UTC） |
| `player`、`opponent` | 人間とボット |
| `speed` | 持ち時間の種類：ブレット、ブリッツ、ラピッド、クラシカル（または通信戦） |
| `player_elo`、`opponent_elo` | 対局前の双方の Lichess レーティング |
| `player_score` | 人間の結果：1 = 勝ち、0.5 = 引き分け、0 = 負け |
| `expected_score` | 人間にとってボットがどれだけ易しいか（Elo の式。下を参照） |
| `session_length` | その対局が属するセッションの対局数 |
| `session_last` | セッションの最後の対局なら true |
| `return_7d` | セッションの最後の対局の30分後から7日後までに、このボットとまた対戦したか。7日後がデータの終わりを越える場合は欠測。ほかの対局では意味をもたない。 |
| `pair_game_index` | この人間がこのボットとそれまでに対戦した局数（0 = 初めて） |

### 例の読み方

- 1つ目のセッション：12月1日に `player_A` はボット `sargon-2ply` とラピッドを10分以内に3局指した（`session_length` = 3）。
  - ボットは約80点弱いので、`expected_score` は約0.6（やや易しい）になる。
  - 3局目でセッションが終わり（`session_last` = true）、2日後にまた対戦したので `return_7d` = true になる。
- 2つ目のセッション：12月3日の2局である。その後7日以内にはこのボットと対戦しなかったので、その `return_7d` は false である。
- 分析では、1セッションが1行（その最後の対局）になる。
""",
    ),
    md(
        """
### 期待スコアの計算例

`expected_score` は Elo の式（Elo, 1978）から求める。

- 最初の表：レーティング1500のプレイヤーが、400点弱いボットから400点強いボットまでと対戦するときの値。
- 2つ目の表：同じ式を例の行に当てはめ、データに入っている値と一致することを示す。
""",
    ),
    code(
        r'''
def elo_expected_score(player_rating: pl.Expr, bot_rating: pl.Expr) -> pl.Expr:
    """Elo's expected score of the player against the bot."""
    return 1 / (1 + 10 ** ((bot_rating - player_rating) / 400))


display(
    pl.DataFrame({"player rating": [1500] * 5, "bot rating": [1100, 1300, 1500, 1700, 1900]})
    .with_columns(expected_score=elo_expected_score(pl.col("player rating"), pl.col("bot rating")))
)
example_rows(games, ["player_elo", "opponent_elo", "expected_score"]).with_columns(
    recomputed=elo_expected_score(pl.col("player_elo"), pl.col("opponent_elo"))
)
''',
    ),
]
"""The cells, in notebook order."""
