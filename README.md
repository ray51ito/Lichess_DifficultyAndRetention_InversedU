# AI Opponent Difficulty and Retention: Reproduction Code

> Japanese version: [README.ja.md](README.ja.md)

This repository reproduces every analysis of the paper

> Ray Ito (2026). AI対戦相手の難易度と再訪：オンラインチェス内のプレイヤー再訪行動の縦断的分析 [AI Opponent Difficulty and Retention: A Longitudinal Analysis of Player Revisit Behavior in Online Chess]. JSAI SIG Technical Report (in Japanese).

On Lichess, players choose which chess AI ("bot") to play, and with it how hard the game is. The study uses every rated real-time human-vs-bot game outside tournaments from August 2022 to August 2026 (49 months, 2,612,524 games, 138,408 players, 4,028 bots). Difficulty is the player's expected score against the bot, computed from the two ratings. Within the same player:

- the chance of playing the same bot again within 7, 28 or 91 days is an inverted U in the expected score, and so is the chance of playing any bot again; the shape stays when the game's result (win, draw, loss) is held fixed;
- at the same distance from an even game, return is lower after a too-strong bot than after a too-weak one (this asymmetry is not found within the same player–bot pair).

The repository recomputes the paper's numbers and figures from the Lichess open database and checks each number listed in [expected/paper_values.json](expected/paper_values.json) against the recomputed one.

## Paper and notebook

All of the analysis code is in [notebooks/D1_reproduction.ipynb](notebooks/D1_reproduction.ipynb) (explanations in Japanese; code and outputs in English). It is organised in steps that follow the paper:

| Paper | Notebook | What is computed | Output |
|---|---|---|---|
| §3 Data | step 1, 2.1 | Filtering of the games (human vs bot, real-time, outside tournaments, ratings and result known); size of the sample | `results/summary.json` (`panel.describe`) |
| §4.1 Model (eq. 1) | 2.2 | Linear probability model within player: expected score and its square, result, game length, speed, player rating, earlier games with the bot, month fixed effects; player-clustered errors | — |
| §4.1 Nine models | 2.3 | Base (same bot, within player), PairFE (same bot, within player–bot pair) and AnyBot (any bot, within player), each for 7-, 28- and 91-day return | `results/panel_horizons.csv` |
| §4.1 Two-lines test, Table 1 | 2.4 | Simonsohn's (2018) two-lines test with the Robin Hood breakpoint, as in his twolines.R, on the nine models and on Base7 without the result; fixed effects and clustered errors; z statistics | `results/panel_two_lines.csv` |
| Figure 1 | 2.4 | Raw 7-day return by expected-score bin (width 0.05) over all games, with Wilson intervals | `results/figures/d1_return_raw.png` |
| §5.1 Binscatter (eq. 2) | 3.1 | The model with 21 expected-score bins centred on an even game (es = 0.5) instead of es and es², for the nine models | `results/shape_flexible.csv` |
| Figure 2 | 3.1 | Binscatter of Base by horizon, and of Base7, PairFE7 and AnyBot7 | `results/figures/d1_binscatter_models.png` |
| §5.1 Mirror test (eq. 3), Table 2 | 3.2 | Hard-minus-easy differences of the ten bin pairs around es = 0.5 (joint Wald test and their mean), Fieller interval of the end-bin ratio | `results/shape_mirror.csv`, `results/shape_mirror_pairs.csv` |
| Figure 3 | 3.2 | The Base7 Binscatter folded at es = 0.5 | `results/figures/d1_mirror.png` |
| — | step 4 | Every number of `expected/paper_values.json`, printed vs recomputed | `results/comparison.csv` |

The notebook calls the two-lines test 「2直線の検定」 and the steps 「段階」.

## Contents

| Path | What it is |
|---|---|
| [notebooks/D1_reproduction.ipynb](notebooks/D1_reproduction.ipynb) | The executed notebook: sample rows of the data, worked examples, checks of each function on made-up data, and every output, with references |
| [expected/paper_values.json](expected/paper_values.json) | Numbers printed in the paper, with where each sits in `results/summary.json` |
| `results/` | Recomputed tables (CSV, `summary.json`), figures, and `comparison.csv` (printed vs recomputed) |
| [scripts/cells/](scripts/cells) | Source of the notebook: one module per step, plus the overview and the references |
| [scripts/build_notebook.py](scripts/build_notebook.py) | Joins the cell modules in [stages.yaml](stages.yaml) order into the notebook and optionally executes it |
| `src/lichess_d1/` | Only data locations, the plotting style and the `d1 run` command |
| [Docs/architecture.md](Docs/architecture.md) | How the files fit together, saved fits, outputs and maintenance scripts |

## Reproducing

### 1. Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12.

```bash
git clone https://github.com/konbraphat51/Lichess_D1.git
cd Lichess_D1
uv sync
```

### 2. Data

The input tables are built by [Lichess_BotDataCollection](https://github.com/konbraphat51/Lichess_BotDataCollection) from the [Lichess open database](https://database.lichess.org/):

```bash
# in Lichess_BotDataCollection
uv run lbd run 2022-08 2026-08 --newest-first
uv run lbd bot-accounts 2022-08 2026-08
uv run lbd panel 2022-08 2026-08
```

The analysis needs, under one data root: `interim/<YYYY-MM>/player_games.parquet` for the 49 months, `interim/census-panel/player_games.parquet` and `external/bot_accounts.parquet`. Collecting the data from scratch takes days (49 dumps of 5–35 GB, Stockfish on every position); see that repository's README.

### 3. Analysis

```bash
export D1_DATA_ROOT=/path/to/collection/data      # or D1_INTERIM_DIR and D1_BOT_ACCOUNTS
uv run d1 run                                      # executes the notebook: fits, tables, figures, comparison
```

Fits are saved in `results/cache/` (git-ignored) and read back on later runs, so a second run takes minutes. `uv run d1 run --refresh` (or `D1_REFRESH=1`) refits everything: the months take about 10 minutes and the four-year panel 10–30 minutes and several GB of memory. Setting `POLARS_MAX_THREADS=2` keeps the machine usable meanwhile.

The output `results/comparison.csv` has one row per checked number: the printed value, the recomputed value, and whether they agree at the printed precision.

The data end in August 2026; September 2026 is held out for a separate pre-registered test and is not used here.

## Editing the notebook

Edit the modules in `scripts/cells/`, not the `.ipynb`, then regenerate and execute it:

```bash
uv run python scripts/build_notebook.py --execute
```

[Docs/architecture.md](Docs/architecture.md) describes the layout, including `scripts/move_stage.py`, which moves a step with all of its files out of the repository.

## Tests

```bash
uv run pytest                                  # runs the notebook's self-contained cells; checks comparison.csv and move_stage.py
uv run ruff check src tests scripts notebooks
uv run mypy src tests
```

## Licence

Code: MIT ([LICENSE](LICENSE)). Data: the Lichess open database, CC0.
