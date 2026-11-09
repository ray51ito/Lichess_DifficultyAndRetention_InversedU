# AI対戦相手の難易度と再訪：再現コード

> English version (primary): [README.md](README.md)

このリポジトリは、次の論文のすべての分析を再現する。

> 伊藤 黎（2026）．AI対戦相手の難易度と再訪：オンラインチェス内のプレイヤー再訪行動の縦断的分析．人工知能学会研究会資料．

Lichess では、プレイヤーは対戦するチェスAI（ボット）を自分で選び、それによって難しさも選ぶ。2022年8月〜2026年8月の、大会外のリアルタイムの人間対ボットのレーティング戦をすべて使う（49か月、2,612,524局、プレイヤー138,408人、ボット4,028体）。難しさは、2人のレーティングから求めるボットに対するプレイヤーの期待スコアである。同じプレイヤーの中で：

- 7・28・91日以内に同じボットとまた対戦する確率は期待スコアについて逆U字になり、相手を問わずボットとまた対戦する確率も逆U字になる。対局の結果（勝ち・引き分け・負け）を固定しても、この形は残る。
- 互角から同じだけ離れたとき、強すぎるボットの後の方が、弱すぎるボットの後より再訪が低い（同じプレイヤーとボットの組の中では、この左右差は見られない）。

このリポジトリは、Lichess のオープンデータベースから論文の数値と図を計算し直し、[expected/paper_values.json](expected/paper_values.json) に挙げた数値を1つずつ再計算の値と照合する。

## 論文とノートブックの対応

分析のコードはすべて [notebooks/D1_reproduction.ipynb](notebooks/D1_reproduction.ipynb) にある（説明は日本語、コードと出力は英語）。論文の順に段階を分けている。

| 論文 | ノートブック | 計算するもの | 出力 |
|---|---|---|---|
| 3節 データ | 段階1、2.1 | 対局の抽出（人間対ボット、リアルタイム、大会外、レーティングと結果が分かる）と標本の大きさ | `results/summary.json`（`panel.describe`） |
| 4.1節 モデル（式1） | 2.2 | プレイヤー内の線形確率モデル：期待スコアとその2乗、結果、手数、持ち時間の種類、レーティング、そのボットとのそれまでの対局数、暦月の固定効果。プレイヤー単位のクラスター頑健標準誤差 | — |
| 4.1節 9つのモデル | 2.3 | Base（同じボット・プレイヤー内）、PairFE（同じボット・プレイヤーとボットの組の中）、AnyBot（ボットを問わない・プレイヤー内）を、それぞれ7・28・91日の再訪で | `results/panel_horizons.csv` |
| 4.1節 Two-lines検定、表1 | 2.4 | Simonsohn（2018）の Two-lines検定（Robin Hood 法、公開コード twolines.R に準拠）を、9つのモデルと結果を除いた Base7 に。固定効果とクラスター頑健標準誤差を使う | `results/panel_two_lines.csv` |
| 図1 | 2.4 | 全対局を合算した、期待スコアの幅0.05のビンごとの生の7日再訪率（Wilson の区間） | `results/figures/d1_return_raw.png` |
| 5.1節 Binscatter（式2） | 3.1 | es と es² の代わりに、互角（es = 0.5）を中央に置いた21のビンを使うモデルを、9つのモデルに | `results/shape_flexible.csv` |
| 図2 | 3.1 | 期間ごとの Base と、Base7・PairFE7・AnyBot7 の Binscatter | `results/figures/d1_binscatter_models.png` |
| 5.1節 鏡像差の検定（式3）、表2 | 3.2 | es = 0.5 を挟む10組のビンの「難しい側 − 易しい側」（同時の Wald 検定とその平均）、両端のビンの比の Fieller の区間 | `results/shape_mirror.csv`、`results/shape_mirror_pairs.csv` |
| 図3 | 3.2 | es = 0.5 で折り返した Base7 の Binscatter | `results/figures/d1_mirror.png` |
| — | 段階4 | `expected/paper_values.json` のすべての数値の、論文の値と再計算の値の照合 | `results/comparison.csv` |

ノートブックでは、Two-lines検定を「2直線の検定」と呼ぶ。

## 内容

| 場所 | 内容 |
|---|---|
| [notebooks/D1_reproduction.ipynb](notebooks/D1_reproduction.ipynb) | 実行済みのノートブック。データの行の例、計算例、作りもののデータでの各関数の確認、すべての出力を、参考文献つきで示す |
| [expected/paper_values.json](expected/paper_values.json) | 論文に書いた数値と、それぞれが `results/summary.json` のどこにあるか |
| `results/` | 計算し直した表（CSV、`summary.json`）、図、`comparison.csv`（論文の値と再計算の値） |
| [scripts/cells/](scripts/cells) | ノートブックの元。段階ごとに1つのモジュールと、概要と参考文献のモジュール |
| [scripts/build_notebook.py](scripts/build_notebook.py) | セルのモジュールを [stages.yaml](stages.yaml) の順につないでノートブックを作り、実行もできる |
| `src/lichess_d1/` | データの場所、図の体裁、`d1 run` コマンドだけ |
| [Docs/architecture.ja.md](Docs/architecture.ja.md) | ファイルの関係、保存する当てはめ、出力、保守用のスクリプト |

## 再現の手順

### 1. 準備

[uv](https://docs.astral.sh/uv/) と Python 3.12 が要る。

```bash
git clone https://github.com/konbraphat51/Lichess_D1.git
cd Lichess_D1
uv sync
```

### 2. データ

入力の表は、[Lichess_BotDataCollection](https://github.com/konbraphat51/Lichess_BotDataCollection) が [Lichess のオープンデータベース](https://database.lichess.org/) から作る。

```bash
# Lichess_BotDataCollection で
uv run lbd run 2022-08 2026-08 --newest-first
uv run lbd bot-accounts 2022-08 2026-08
uv run lbd panel 2022-08 2026-08
```

分析には、1つのデータの場所の下に次が要る：49か月分の `interim/<YYYY-MM>/player_games.parquet`、`interim/census-panel/player_games.parquet`、`external/bot_accounts.parquet`。データを一から集めるには数日かかる（5〜35 GB のダンプ49本と、すべての局面の Stockfish 評価）。そのリポジトリの README を参照。

### 3. 分析

```bash
export D1_DATA_ROOT=/path/to/collection/data      # または D1_INTERIM_DIR と D1_BOT_ACCOUNTS
uv run d1 run                                      # ノートブックを実行する：当てはめ、表、図、照合
```

当てはめの結果は `results/cache/` に保存され（git の対象外）、次からはそれを読み込むので、2回目以降は数分で終わる。`uv run d1 run --refresh`（または `D1_REFRESH=1`）ですべて当てはめ直す。月ごとの分析に約10分、4年分のパネルに10〜30分と数 GB のメモリがかかる。`POLARS_MAX_THREADS=2` を設定すると、その間も計算機を使いやすい。

出力の `results/comparison.csv` は、照合する数値1つにつき1行で、論文の値、再計算の値、論文の桁数で一致するかを示す。

データは2026年8月までである。2026年9月は別の事前登録した検定のために取っておき、ここでは使わない。

## ノートブックの編集

`.ipynb` ではなく `scripts/cells/` のモジュールを編集し、ノートブックを作り直して実行する。

```bash
uv run python scripts/build_notebook.py --execute
```

構成は [Docs/architecture.ja.md](Docs/architecture.ja.md) に書いた。1つの段階をそのすべてのファイルとともにリポジトリの外へ移す `scripts/move_stage.py` もそこで説明する。

## テスト

```bash
uv run pytest                                  # ノートブックの自己完結したセルを実行し、comparison.csv と move_stage.py を確かめる
uv run ruff check src tests scripts notebooks
uv run mypy src tests
```

## ライセンス

コード：MIT（[LICENSE](LICENSE)）。データ：Lichess のオープンデータベース、CC0。
