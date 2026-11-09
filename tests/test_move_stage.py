"""Tests scripts/move_stage.py on a made-up repository layout in a temporary folder."""

from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path

import move_stage
import pytest
import stage_list

ROOT = Path(__file__).resolve().parents[1]
TODAY = dt.date(2026, 11, 9)

STAGES_YAML = """\
# made-up stages
- id: 0
  title_ja: 準備
  module: scripts/cells/stage_0.py
  questions: []
  caches: []
  results: []
  figures: []
  summary_key: null
  expected_prefix: null
- id: 1
  title_ja: 一つ目
  module: scripts/cells/stage_1.py
  questions: [Q1a]
  caches: ["one_*"]
  results: ["one_*.csv"]
  figures: [d1_one.png]
  summary_key: one
  expected_prefix: one.
- id: 2
  title_ja: 二つ目
  module: scripts/cells/stage_2.py
  questions: [Q2a]
  caches: ["two_*"]
  results: ["two_*.csv"]
  figures: [d1_two.png]
  summary_key: two
  expected_prefix: two.
"""

STAGE_SOURCES = {
    "stage_0": '''
CELLS = [
    md("""
## 0. 準備
"""),
    code(r"""
import polars as pl
BASE = 1
"""),
]
''',
    "stage_1": '''
CELLS = [
    md("""
## 1. 一つ目
"""),
    code(r"""
def helper(x):
    local = x + BASE
    return pl.lit(local)


ONE = helper(2)
"""),
]
''',
    "stage_2": '''
CELLS = [
    code(r"""
def twice():
    return ONE * 2


TWO = twice()
BASE = 5
print(BASE)
"""),
]
''',
}

EXPECTED_JSON = """\
{
  "source": "made up",
  "rules": "round",
  "values": [
    {"section": "a", "what": "x", "path": "zero.n", "paper": 1, "decimals": 0},

    {"section": "b", "what": "y", "path": "one.a", "paper": 2.5, "decimals": 1},
    {"section": "b", "what": "z", "path": "one.b", "paper": 3.5, "decimals": 1},

    {"section": "c", "what": "w", "path": "two.a", "paper": 4, "decimals": 0}
  ]
}
"""

README = """\
# Made up

| Step | What |
|---|---|
| 1 One | the first |
| 2 Two | the second |

Stage 1 writes `one_x.csv` and answers Q1a.
Nothing here.
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A made-up Lichess_D1 layout with three stages."""
    root = tmp_path / "repo"
    files = {
        "stages.yaml": STAGES_YAML,
        "expected/paper_values.json": EXPECTED_JSON,
        "notebooks/D1_reproduction.ipynb": "{}\n",
        "README.md": README,
        "Docs/architecture.ja.md": "段階1の表。\n段階10ではない。\n",
        "results/cache/one_a.json": "1",
        "results/cache/one_b.json": "2",
        "results/cache/two_a.json": "3",
        "results/one_x.csv": "a\n1\n",
        "results/two_x.csv": "a\n2\n",
        "results/figures/d1_one.png": "png1",
        "results/figures/d1_two.png": "png2",
        **{f"scripts/cells/{name}.py": text for name, text in STAGE_SOURCES.items()},
    }
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    return root


def test_load_and_find_stage(repo: Path) -> None:
    stages = stage_list.load_stages(repo)
    assert [stage.stage_id for stage in stages] == ["0", "1", "2"]
    stage = stage_list.find_stage(stages, "1")
    assert stage.questions == ("Q1a",)
    assert stage.expected_prefixes == ("one.",)
    assert stages[0].summary_key is None
    with pytest.raises(KeyError):
        stage_list.find_stage(stages, "9")


def test_plan_lists_files_values_docs_and_dependents(repo: Path) -> None:
    plan = move_stage.make_plan(repo, "1")
    assert [path.name for path in plan.caches] == ["one_a.json", "one_b.json"]
    assert [path.name for path in plan.results] == ["one_x.csv"]
    assert [path.name for path in plan.figures] == ["d1_one.png"]
    assert [move_stage.value_path(line) for line in plan.expected_values] == ["one.a", "one.b"]
    mentioned = {(m.path.name, m.line_number) for m in plan.doc_mentions}
    assert mentioned == {("README.md", 5), ("README.md", 8), ("architecture.ja.md", 1)}
    assert plan.dependents == {"2": ("ONE",)}


def test_dry_run_copies_nothing(repo: Path, tmp_path: Path) -> None:
    target = tmp_path / "out"
    before = (repo / "stages.yaml").read_text(encoding="utf-8")
    report = move_stage.move_stage(repo, "1", target, is_dry_run=True)
    assert "caches (2):" in report
    assert "expected values (2):" in report
    assert "dry run" in report
    assert not target.exists()
    assert (repo / "stages.yaml").read_text(encoding="utf-8") == before


def test_copy_mirrors_files_and_writes_manifest(repo: Path, tmp_path: Path) -> None:
    target = tmp_path / "out"
    move_stage.move_stage(repo, "1", target, today=TODAY)
    for relative in (
        "notebooks/D1_reproduction.ipynb",
        "scripts/cells/stage_1.py",
        "results/cache/one_a.json",
        "results/cache/one_b.json",
        "results/one_x.csv",
        "results/figures/d1_one.png",
    ):
        assert (target / relative).read_bytes() == (repo / relative).read_bytes()
    assert not (target / "results/cache/two_a.json").exists()
    moved = json.loads((target / "expected/paper_values.json").read_text(encoding="utf-8"))
    assert [value["path"] for value in moved["values"]] == ["one.a", "one.b"]
    assert moved["rules"] == "round"
    lines = (target / "expected/paper_values.json").read_text(encoding="utf-8").splitlines()
    assert sum(line.startswith('    {"section"') for line in lines) == 2
    assert (target / "stages.yaml").read_text(encoding="utf-8").startswith("- id: 1\n")
    manifest = (target / "MANIFEST.md").read_text(encoding="utf-8")
    assert "Source commit: `unknown`" in manifest
    assert "`results/cache/one_a.json`" in manifest
    assert "stage 2: ONE" in manifest
    assert "2026-11-09" in manifest
    assert (repo / "results/cache/one_a.json").exists()  # copying alone keeps the stage


def test_remove_takes_the_stage_out(repo: Path, tmp_path: Path) -> None:
    target = tmp_path / "out"
    move_stage.move_stage(repo, "1", target, is_removing=True, today=TODAY)
    for relative in (
        "scripts/cells/stage_1.py",
        "results/cache/one_a.json",
        "results/one_x.csv",
        "results/figures/d1_one.png",
    ):
        assert not (repo / relative).exists()
        assert (target / relative).exists()
    assert (repo / "results/cache/two_a.json").exists()
    assert (repo / "notebooks/D1_reproduction.ipynb").exists()
    assert [stage.stage_id for stage in stage_list.load_stages(repo)] == ["0", "2"]
    stages_text = (repo / "stages.yaml").read_text(encoding="utf-8")
    assert stages_text == STAGES_YAML.replace(move_stage.stage_entry_text(STAGES_YAML, "1"), "")
    remaining = (repo / "expected/paper_values.json").read_text(encoding="utf-8")
    assert [value["path"] for value in json.loads(remaining)["values"]] == ["zero.n", "two.a"]
    assert "\n\n\n" not in remaining
    assert "removed from" in (target / "MANIFEST.md").read_text(encoding="utf-8")


def test_expected_round_trip_keeps_text() -> None:
    header, body, footer = move_stage.split_expected(EXPECTED_JSON)
    assert move_stage.render_expected(header, body, footer) == EXPECTED_JSON
    assert move_stage.render_expected(header, ["", body[0], "", ""], footer).count(",\n  ]") == 0


def test_a_list_of_prefixes_selects_each(repo: Path) -> None:
    stages_path = repo / "stages.yaml"
    text = stages_path.read_text(encoding="utf-8")
    stages_path.write_text(
        text.replace("expected_prefix: one.", "expected_prefix: [one.a, zero.]"), encoding="utf-8"
    )
    stage = stage_list.find_stage(stage_list.load_stages(repo), "1")
    assert stage.expected_prefixes == ("one.a", "zero.")
    paths = [move_stage.value_path(line) for line in move_stage.stage_values(repo, stage)]
    assert paths == ["zero.n", "one.a"]
    remaining = json.loads(move_stage.remaining_expected_text(repo, stage))
    assert [value["path"] for value in remaining["values"]] == ["one.b", "two.a"]


def test_stage_without_values_keeps_expected_file(repo: Path) -> None:
    stage = stage_list.find_stage(stage_list.load_stages(repo), "0")
    assert move_stage.stage_values(repo, stage) == ()
    assert move_stage.remaining_expected_text(repo, stage) == EXPECTED_JSON


def test_cell_names_follow_python_scopes() -> None:
    defined, used = move_stage.cell_names(
        "import json\nX = 1\ndef f(a):\n    b = a + Y\n    return json.dumps(b)\n"
    )
    assert defined == {"json", "X", "f"}
    assert "Y" in used
    assert "json" in used
    assert not {"a", "b"} & used


def test_dependencies_name_the_latest_defining_stage(repo: Path) -> None:
    stages = stage_list.load_stages(repo)
    dependencies = move_stage.stage_dependencies(repo, stages)
    assert dependencies["0"] == {}
    assert dependencies["1"] == {"0": ["BASE", "pl"]}
    assert dependencies["2"] == {"1": ["ONE"]}  # BASE is redefined in stage 2 itself
    text = move_stage.format_dependencies(dependencies["1"])
    assert text == "Names used from earlier stages:\n    stage 0: BASE, pl"
    assert move_stage.format_dependencies({}) == "Names used from earlier stages: none."


def test_reads_before_a_later_definition_count(tmp_path: Path) -> None:
    module = tmp_path / "scripts/cells/stage_9.py"
    module.parent.mkdir(parents=True)
    module.write_text('CELLS = [code("print(ONE)"), code("ONE = 2\\nprint(ONE)")]\n', "utf-8")
    stage = stage_list.Stage("9", "t", "scripts/cells/stage_9.py", (), (), (), (), None, ())
    defined, read_first = move_stage.stage_names(tmp_path, stage)
    assert defined == {"ONE"}
    assert "ONE" in read_first


def test_entry_lines_may_quote_the_id_or_carry_a_comment() -> None:
    text = '- id: "1"  # first\n  module: a.py\n- id: 2\n  module: b.py\n'
    assert move_stage.stage_entry_text(text, "1") == '- id: "1"  # first\n  module: a.py\n'
    assert move_stage.drop_stage_entry(text, "1") == "- id: 2\n  module: b.py\n"


def test_move_refuses_a_used_target(repo: Path, tmp_path: Path) -> None:
    target = tmp_path / "out"
    target.mkdir()
    (target / "MANIFEST.md").write_text("an earlier move\n", encoding="utf-8")
    with pytest.raises(move_stage.MoveError):
        move_stage.move_stage(repo, "1", target, is_removing=True)
    assert (target / "MANIFEST.md").read_text(encoding="utf-8") == "an earlier move\n"
    assert (repo / "scripts/cells/stage_1.py").exists()
    with pytest.raises(move_stage.MoveError):
        move_stage.move_stage(repo, "1", repo / "archive")
    assert not (repo / "archive").exists()


@pytest.fixture
def git_repo(repo: Path) -> Path:
    """The made-up layout as a git repository with one commit."""
    git(repo, "init", "-q")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "made up")
    return repo


def git(repo: Path, *args: str) -> str:
    """Runs git in ``repo`` with a made-up author and returns its output."""
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


HAS_GIT = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")


@HAS_GIT
def test_remove_tags_the_source_commit(git_repo: Path, tmp_path: Path) -> None:
    head = git(git_repo, "rev-parse", "HEAD")
    move_stage.move_stage(git_repo, "2", tmp_path / "out", is_removing=True, today=TODAY)
    assert git(git_repo, "rev-parse", "pre-move-stage2-20261109") == head
    manifest = (tmp_path / "out/MANIFEST.md").read_text(encoding="utf-8")
    assert f"Source commit: `{head}`; tag `pre-move-stage2-20261109`." in manifest
    assert "git checkout pre-move-stage2-20261109 --" in manifest


@HAS_GIT
def test_a_second_move_on_the_same_day_gets_its_own_tag(git_repo: Path, tmp_path: Path) -> None:
    git(git_repo, "tag", "pre-move-stage2-20261109")
    (git_repo / "README.md").write_text("changed\n", encoding="utf-8")
    git(git_repo, "commit", "-q", "-am", "later")
    head = git(git_repo, "rev-parse", "HEAD")
    move_stage.move_stage(git_repo, "2", tmp_path / "out", is_removing=True, today=TODAY)
    assert git(git_repo, "rev-parse", "pre-move-stage2-20261109-2") == head


@HAS_GIT
def test_remove_refuses_uncommitted_changes(git_repo: Path, tmp_path: Path) -> None:
    (git_repo / "scripts/cells/stage_2.py").write_text("CELLS = []\n", encoding="utf-8")
    with pytest.raises(move_stage.MoveError):
        move_stage.move_stage(git_repo, "2", tmp_path / "out", is_removing=True, today=TODAY)
    assert (git_repo / "scripts/cells/stage_2.py").exists()
    assert not (tmp_path / "out").exists()
    assert git(git_repo, "tag") == ""


def test_real_stage_docstrings_list_their_dependencies() -> None:
    stages = stage_list.load_stages(ROOT)
    dependencies = move_stage.stage_dependencies(ROOT, stages)
    for stage in stages:
        text = (ROOT / stage.module).read_text(encoding="utf-8")
        docstring = text.split('"""', 2)[1]
        assert move_stage.format_dependencies(dependencies[stage.stage_id]) in docstring, stage
