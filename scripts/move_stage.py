"""Copies one notebook stage, with its expected values and outputs, to another folder.

The files of each stage are listed in ``stages.yaml``. Run
``uv run python scripts/move_stage.py <id> --to <dir> [--dry-run] [--remove]``:
``--dry-run`` only prints the plan, ``--remove`` also takes the stage out of this repository
(its files, expected values, ``stages.yaml`` entry and cell module) after tagging HEAD, and
refuses to run on uncommitted changes. The target must be a new folder outside the repository.
The docs that mention the stage and the later stages that use its names are listed; editing
them is left to a person.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import itertools
import json
import re
import shutil
import subprocess
import symtable
import textwrap
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from stage_list import STAGES_FILE, Stage, find_stage, load_stages

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_FILE = "notebooks/D1_reproduction.ipynb"
EXPECTED_FILE = "expected/paper_values.json"
CACHE_DIR = "results/cache"
RESULTS_DIR = "results"
FIGURE_DIR = "results/figures"
MANIFEST_FILE = "MANIFEST.md"
DOC_GLOBS = ("README*.md", "Docs/*.md")
DEPENDENCY_HEADING = "Names used from earlier stages"
"""First words of the dependency list in each stage module's docstring."""

VALUES_START = '  "values": ['
VALUES_END = "  ]"


class MoveError(Exception):
    """A move that would overwrite files or lose uncommitted work."""


@dataclass(frozen=True)
class DocMention:
    """One line of a document that mentions the stage."""

    path: Path
    line_number: int
    text: str


@dataclass(frozen=True)
class MovePlan:
    """Everything that moving one stage copies, and what refers to it."""

    stage: Stage
    entry_text: str
    notebook: Path | None
    module: Path
    caches: tuple[Path, ...]
    results: tuple[Path, ...]
    figures: tuple[Path, ...]
    expected_values: tuple[str, ...]
    doc_mentions: tuple[DocMention, ...]
    dependents: dict[str, tuple[str, ...]]

    @property
    def files(self) -> tuple[Path, ...]:
        """Files copied as they are (the notebook, the module and the outputs)."""
        notebook = (self.notebook,) if self.notebook is not None else ()
        return (*notebook, self.module, *self.caches, *self.results, *self.figures)


def match_files(folder: Path, patterns: Iterable[str]) -> tuple[Path, ...]:
    """Files directly in ``folder`` that match any of the glob ``patterns``, sorted, no repeats."""
    found: dict[Path, None] = {}
    for pattern in patterns:
        for path in sorted(folder.glob(pattern)):
            if path.is_file():
                found[path] = None
    return tuple(found)


def _entry_id(line: str) -> str:
    """The id on a ``- id: <id>`` line, without quotes or a trailing comment."""
    return line.split(":", 1)[1].split("#", 1)[0].strip().strip("'\"")


def _entry_span(lines: list[str], stage_id: str) -> tuple[int, int]:
    """Start and end line index of the ``- id: <stage_id>`` entry of stages.yaml."""
    starts = [i for i, line in enumerate(lines) if line.startswith("- id:")]
    chosen = [i for i in starts if _entry_id(lines[i]) == stage_id]
    if len(chosen) != 1:
        raise ValueError(f"expected one '- id: {stage_id}' line in {STAGES_FILE}")
    later = [i for i in starts if i > chosen[0]]
    return chosen[0], later[0] if later else len(lines)


def stage_entry_text(stages_text: str, stage_id: str) -> str:
    """The lines of one stage's entry in the text of stages.yaml."""
    lines = stages_text.splitlines(keepends=True)
    start, end = _entry_span(lines, stage_id)
    return "".join(lines[start:end])


def drop_stage_entry(stages_text: str, stage_id: str) -> str:
    """The text of stages.yaml without one stage's entry; other lines are kept as they are."""
    lines = stages_text.splitlines(keepends=True)
    start, end = _entry_span(lines, stage_id)
    return "".join(lines[:start] + lines[end:])


def split_expected(text: str) -> tuple[list[str], list[str], list[str]]:
    """Splits paper_values.json into header, body and footer lines.

    Body lines are value lines without their trailing comma, or blank lines between groups.
    """
    lines = text.splitlines()
    start = lines.index(VALUES_START)
    end = next(i for i in range(len(lines) - 1, start, -1) if lines[i] == VALUES_END)
    body = [line.rstrip().removesuffix(",") for line in lines[start + 1 : end]]
    for line in body:
        if line:
            json.loads(line)  # one value per line, or the file is not in the expected style
    return lines[: start + 1], body, lines[end:]


def render_expected(header: list[str], body: list[str], footer: list[str]) -> str:
    """Joins header, body and footer back into the one-value-per-line JSON style.

    Blank lines at the ends of the body or next to another blank line are dropped.
    """
    kept: list[str] = []
    for line in body:
        if line or (kept and kept[-1]):
            kept.append(line)
    while kept and not kept[-1]:
        kept.pop()
    last = max((i for i, line in enumerate(kept) if line), default=-1)
    lines = [f"{line}," if line and i < last else line for i, line in enumerate(kept)]
    return "\n".join([*header, *lines, *footer]) + "\n"


def value_path(line: str) -> str:
    """The summary path of one value line of paper_values.json."""
    return str(json.loads(line)["path"])


def stage_values(root: Path, stage: Stage) -> tuple[str, ...]:
    """Value lines of paper_values.json whose path starts with one of the stage's prefixes."""
    path = root / EXPECTED_FILE
    if not stage.expected_prefixes or not path.exists():
        return ()
    _, body, _ = split_expected(path.read_text(encoding="utf-8"))
    return tuple(line for line in body if line and stage.owns_value(value_path(line)))


def moved_expected_text(root: Path, stage: Stage, values: Sequence[str], commit: str) -> str:
    """A paper_values.json holding only the moved values, with a source line naming the commit."""
    _, _, footer = split_expected((root / EXPECTED_FILE).read_text(encoding="utf-8"))
    rules = json.loads((root / EXPECTED_FILE).read_text(encoding="utf-8")).get("rules", "")
    source = (
        f"Expected values of stage {stage.stage_id} (paths starting with "
        f"{_prefix_text(stage)}), moved out of Lichess_D1 at commit {commit}."
    )
    header = [
        "{",
        f'  "source": {json.dumps(source)},',
        f'  "rules": {json.dumps(rules)},',
        VALUES_START,
    ]
    return render_expected(header, list(values), footer)


def remaining_expected_text(root: Path, stage: Stage) -> str:
    """The text of paper_values.json without the stage's values; other lines are kept as they are."""
    text = (root / EXPECTED_FILE).read_text(encoding="utf-8")
    if not stage.expected_prefixes:
        return text
    header, body, footer = split_expected(text)
    kept = [line for line in body if not (line and stage.owns_value(value_path(line)))]
    return render_expected(header, kept, footer)


def _prefix_text(stage: Stage) -> str:
    """The stage's expected-value prefixes as quoted text, or 'none'."""
    return ", ".join(f"'{prefix}'" for prefix in stage.expected_prefixes) or "none"


def cell_sources(module_path: Path) -> list[str]:
    """Sources of the ``code(...)`` cells of one cell module, in order, without running it."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    found: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        first = node.args[0] if node.args else None
        if node.func.id == "code" and isinstance(first, ast.Constant):
            found.append((node.lineno, node.col_offset, str(first.value).strip()))
    return [source for _, _, source in sorted(found)]


def _global_references(table: symtable.SymbolTable) -> set[str]:
    """Names that nested scopes of ``table`` read from the module's globals."""
    names: set[str] = set()
    for child in table.get_children():
        names |= {
            symbol.get_name()
            for symbol in child.get_symbols()
            if symbol.is_global() and symbol.is_referenced()
        }
        names |= _global_references(child)
    return names


def cell_names(source: str) -> tuple[set[str], set[str]]:
    """The global names one code cell defines, and the global names it reads."""
    table = symtable.symtable(source, "<cell>", "exec")
    defined = {
        symbol.get_name()
        for symbol in table.get_symbols()
        if symbol.is_assigned() or symbol.is_imported() or symbol.is_namespace()
    }
    used = {symbol.get_name() for symbol in table.get_symbols() if symbol.is_referenced()}
    return defined, used | _global_references(table)


def stage_names(root: Path, stage: Stage) -> tuple[set[str], set[str]]:
    """The global names a stage's code cells define, and those they read before defining them.

    A name read in a cell counts unless that cell or an earlier cell of the stage defines it.
    """
    defined: set[str] = set()
    read_first: set[str] = set()
    for source in cell_sources(root / stage.module):
        cell_defined, cell_used = cell_names(source)
        read_first |= cell_used - defined - cell_defined
        defined |= cell_defined
    return defined, read_first


def stage_dependencies(root: Path, stages: Sequence[Stage]) -> dict[str, dict[str, list[str]]]:
    """For each stage, the names it reads from earlier stages, by the latest stage defining each."""
    names = [stage_names(root, stage) for stage in stages]
    dependencies: dict[str, dict[str, list[str]]] = {}
    for index, stage in enumerate(stages):
        by_stage: dict[str, list[str]] = {}
        for name in sorted(names[index][1]):
            sources = [i for i in range(index) if name in names[i][0]]
            if sources:
                by_stage.setdefault(stages[sources[-1]].stage_id, []).append(name)
        dependencies[stage.stage_id] = {
            earlier.stage_id: by_stage[earlier.stage_id]
            for earlier in stages[:index]
            if earlier.stage_id in by_stage
        }
    return dependencies


def format_dependencies(by_stage: dict[str, list[str]]) -> str:
    """The dependency list written in a stage module's docstring."""
    if not by_stage:
        return f"{DEPENDENCY_HEADING}: none."
    lines = [f"{DEPENDENCY_HEADING}:"]
    for stage_id, names in by_stage.items():
        lines += textwrap.wrap(
            f"stage {stage_id}: {', '.join(names)}",
            width=96,
            initial_indent="    ",
            subsequent_indent="        ",
            break_on_hyphens=False,
        )
    return "\n".join(lines)


def stage_dependents(
    root: Path, stages: Sequence[Stage], stage_id: str
) -> dict[str, tuple[str, ...]]:
    """Later stages that read names defined in ``stage_id``, with those names."""
    dependencies = stage_dependencies(root, stages)
    return {
        later: tuple(by_stage[stage_id])
        for later, by_stage in dependencies.items()
        if stage_id in by_stage
    }


def mention_patterns(stage: Stage) -> list[re.Pattern[str]]:
    """Patterns of text in the docs that refer to the stage."""
    number = re.escape(stage.stage_id)
    words = [
        rf"\b(?:[Ss]tep|[Ss]tage)s? {number}(?![0-9])",
        rf"段階\s?{number}(?![0-9])",
        rf"^\|\s*{number}\s",
        re.escape(Path(stage.module).name),
        *(rf"\b{re.escape(question)}\b" for question in stage.questions),
        *(re.escape(figure) for figure in stage.figures if "*" not in figure),
    ]
    if stage.summary_key is not None:
        words.append(rf"summary\[\"{re.escape(stage.summary_key)}\"\]")
    return [re.compile(word) for word in words]


def find_doc_mentions(root: Path, stage: Stage) -> tuple[DocMention, ...]:
    """Lines of README*.md and Docs/*.md that mention the stage."""
    patterns = mention_patterns(stage)
    mentions: list[DocMention] = []
    for doc in sorted({path for pattern in DOC_GLOBS for path in root.glob(pattern)}):
        for number, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), start=1):
            if any(pattern.search(line) for pattern in patterns):
                mentions.append(DocMention(doc, number, line.strip()))
    return tuple(mentions)


def make_plan(root: Path, stage_id: str) -> MovePlan:
    """Collects what moving ``stage_id`` would copy, and what refers to it."""
    stages = load_stages(root)
    stage = find_stage(stages, stage_id)
    notebook = root / NOTEBOOK_FILE
    return MovePlan(
        stage=stage,
        entry_text=stage_entry_text((root / STAGES_FILE).read_text(encoding="utf-8"), stage_id),
        notebook=notebook if notebook.exists() else None,
        module=root / stage.module,
        caches=match_files(root / CACHE_DIR, stage.caches),
        results=match_files(root / RESULTS_DIR, stage.results),
        figures=match_files(root / FIGURE_DIR, stage.figures),
        expected_values=stage_values(root, stage),
        doc_mentions=find_doc_mentions(root, stage),
        dependents=stage_dependents(root, stages, stage_id),
    )


def describe_plan(plan: MovePlan, root: Path, target: Path) -> str:
    """The plan as text: files and values to copy, docs to edit, stages that depend on it."""
    stage = plan.stage
    lines = [
        f"Stage {stage.stage_id} ({stage.title_ja}) -> {target}",
        f"  questions: {', '.join(stage.questions) or 'none'}",
        f"  summary key: {stage.summary_key}; expected prefixes: {_prefix_text(stage)}",
        f"  notebook: {_relative(plan.notebook, root) if plan.notebook else 'not built'}",
        f"  module: {_relative(plan.module, root)}",
    ]
    for label, paths in (
        ("caches", plan.caches),
        ("results", plan.results),
        ("figures", plan.figures),
    ):
        lines.append(f"  {label} ({len(paths)}):")
        lines += [f"    {_relative(path, root)}" for path in paths]
    lines.append(f"  expected values ({len(plan.expected_values)}):")
    lines += [f"    {value_path(line)}" for line in plan.expected_values]
    lines.append(f"  docs that mention the stage ({len(plan.doc_mentions)} lines):")
    lines += [f"    {_relative(m.path, root)}:{m.line_number}: {m.text}" for m in plan.doc_mentions]
    lines.append("  later stages that use its names:")
    lines += [
        f"    stage {later}: {', '.join(names)}" for later, names in plan.dependents.items()
    ] or ["    none"]
    return "\n".join(lines)


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _git(root: Path, *args: str) -> str | None:
    """Output of a git command in ``root``, or None outside a git repository."""
    if not (root / ".git").exists():
        return None
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip()


def current_commit(root: Path) -> str:
    """The full hash of HEAD, or 'unknown' outside a git repository."""
    return _git(root, "rev-parse", "HEAD") or "unknown"


def has_uncommitted_changes(root: Path) -> bool:
    """Whether tracked or new files differ from HEAD."""
    return bool(_git(root, "status", "--porcelain"))


def tag_before_move(root: Path, stage_id: str, today: dt.date) -> str | None:
    """Tags HEAD as ``pre-move-stage<id>-<YYYYMMDD>``; None without git.

    A tag of that name on HEAD is reused; one on another commit gets a ``-2``, ``-3``... name.
    """
    head = _git(root, "rev-parse", "HEAD")
    if head is None:
        return None
    base = f"pre-move-stage{stage_id}-{today:%Y%m%d}"
    for number in itertools.count(1):
        name = base if number == 1 else f"{base}-{number}"
        tagged = _git(root, "rev-parse", "--verify", "--quiet", f"refs/tags/{name}^{{commit}}")
        if tagged == head:
            return name
        if tagged is None:
            return name if _git(root, "tag", name) is not None else None
    raise AssertionError("unreachable")


def planned_destinations(plan: MovePlan, root: Path, target: Path) -> list[Path]:
    """Every file that moving the stage writes in ``target``, including MANIFEST.md."""
    copies = [target / _relative(source, root) for source in plan.files]
    expected = [target / EXPECTED_FILE] if plan.expected_values else []
    return [*copies, *expected, target / STAGES_FILE, target / MANIFEST_FILE]


def check_move(plan: MovePlan, root: Path, target: Path, *, is_removing: bool) -> None:
    """Raises MoveError when the move could overwrite files or lose uncommitted work."""
    if target.resolve().is_relative_to(root.resolve()):
        raise MoveError(f"the target {target} must be outside the repository {root}")
    existing = [path for path in planned_destinations(plan, root, target) if path.exists()]
    if existing:
        raise MoveError(f"the target already holds {existing[0]}; choose a new folder")
    if is_removing and has_uncommitted_changes(root):
        raise MoveError("commit the changes first: --remove restores from the tagged commit")


def copy_stage(plan: MovePlan, root: Path, target: Path, commit: str) -> list[Path]:
    """Copies the stage's files, expected values and stages.yaml entry into ``target``."""
    copied: list[Path] = []
    for source in plan.files:
        destination = target / _relative(source, root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(destination)
    if plan.expected_values:
        destination = target / EXPECTED_FILE
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            moved_expected_text(root, plan.stage, plan.expected_values, commit),
            encoding="utf-8",
            newline="\n",
        )
        copied.append(destination)
    destination = target / STAGES_FILE
    destination.write_text(plan.entry_text, encoding="utf-8", newline="\n")
    copied.append(destination)
    return copied


def manifest_text(
    plan: MovePlan,
    root: Path,
    target: Path,
    copied: Sequence[Path],
    *,
    commit: str,
    tag: str | None,
    is_dirty: bool,
    is_removed: bool,
    today: dt.date,
) -> str:
    """MANIFEST.md: what was copied, from which commit, and how to restore it."""
    stage = plan.stage
    restore_paths = [STAGES_FILE, stage.module]
    if plan.expected_values:
        restore_paths.append(EXPECTED_FILE)
    reference = tag or commit
    lines = [
        f"# Stage {stage.stage_id} of Lichess_D1: {stage.title_ja}",
        "",
        f"- Moved on {today.isoformat()} by `scripts/move_stage.py`"
        f" ({'removed from' if is_removed else 'still in'} Lichess_D1).",
        f"- Source commit: `{commit}`"
        + (" (with uncommitted changes)" if is_dirty else "")
        + (f"; tag `{tag}`" if tag else "")
        + ".",
        f"- Questions: {', '.join(stage.questions) or 'none'}; summary key:"
        f" `{stage.summary_key}`; expected prefixes: {_prefix_text(stage)}.",
        "",
        "## Copied files",
        "",
        "Paths are relative to this folder and mirror the repository layout.",
        "",
        *(f"- `{_relative(path, target)}`" for path in copied),
        "",
        (
            f"`{EXPECTED_FILE}` holds the {len(plan.expected_values)} expected values of the"
            f" stage; `{STAGES_FILE}` holds its entry."
            if plan.expected_values
            else f"The stage has no expected values; `{STAGES_FILE}` holds its entry."
        ),
        "",
        "## Docs that mentioned the stage",
        "",
        *(f"- `{_relative(m.path, root)}:{m.line_number}`: {m.text}" for m in plan.doc_mentions),
        *([] if plan.doc_mentions else ["- none"]),
        "",
        "## Later stages that used its names",
        "",
        *(f"- stage {later}: {', '.join(names)}" for later, names in plan.dependents.items()),
        *([] if plan.dependents else ["- none"]),
        "",
        "## How to restore",
        "",
        "1. In Lichess_D1, take back the stage's entry, module and expected values:",
        f"   `git checkout {reference} -- {' '.join(restore_paths)}`.",
        "   If those files changed since, instead add the entry of this folder's"
        f" `{STAGES_FILE}`, copy back `{stage.module}` and append the lines of this folder's"
        f" `{EXPECTED_FILE}`.",
        "2. Copy back the saved fits, tables and figures: copy this folder's `results/`"
        " over the repository's `results/`.",
        "3. Undo the edits made after the move in the docs and later stages listed above.",
        "4. Rebuild and check: `uv run python scripts/build_notebook.py --execute`,"
        " then `uv run pytest -q`.",
        "",
    ]
    return "\n".join(lines)


def remove_stage(plan: MovePlan, root: Path) -> None:
    """Removes the stage's outputs, module, expected values and stages.yaml entry from ``root``."""
    for path in (plan.module, *plan.caches, *plan.results, *plan.figures):
        path.unlink()
    if plan.expected_values:
        (root / EXPECTED_FILE).write_text(
            remaining_expected_text(root, plan.stage), encoding="utf-8", newline="\n"
        )
    stages_path = root / STAGES_FILE
    stages_path.write_text(
        drop_stage_entry(stages_path.read_text(encoding="utf-8"), plan.stage.stage_id),
        encoding="utf-8",
        newline="\n",
    )


def move_stage(
    root: Path,
    stage_id: str,
    target: Path,
    *,
    is_dry_run: bool = False,
    is_removing: bool = False,
    today: dt.date | None = None,
) -> str:
    """Moves one stage as the command line does and returns the text to print."""
    plan = make_plan(root, stage_id)
    report = describe_plan(plan, root, target)
    if is_dry_run:
        return f"{report}\n(dry run: nothing copied)"
    check_move(plan, root, target, is_removing=is_removing)
    day = today or dt.date.today()
    commit = current_commit(root)
    is_dirty = has_uncommitted_changes(root)
    tag = tag_before_move(root, stage_id, day) if is_removing else None
    target.mkdir(parents=True, exist_ok=True)
    copied = copy_stage(plan, root, target, commit)
    manifest = target / MANIFEST_FILE
    manifest.write_text(
        manifest_text(
            plan,
            root,
            target,
            copied,
            commit=commit,
            tag=tag,
            is_dirty=is_dirty,
            is_removed=is_removing,
            today=day,
        ),
        encoding="utf-8",
        newline="\n",
    )
    if is_removing:
        remove_stage(plan, root)
    action = "copied and removed" if is_removing else "copied"
    return f"{report}\n{action}: {len(copied)} files; manifest {manifest}"


def main(argv: Sequence[str] | None = None) -> None:
    """Parses arguments and moves the stage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage_id", help="the id of the stage in stages.yaml")
    parser.add_argument("--to", type=Path, required=True, help="folder to copy the stage into")
    parser.add_argument("--dry-run", action="store_true", help="only print the plan")
    parser.add_argument("--remove", action="store_true", help="also remove it from Lichess_D1")
    args = parser.parse_args(argv)
    try:
        report = move_stage(
            ROOT,
            args.stage_id,
            args.to.resolve(),
            is_dry_run=args.dry_run,
            is_removing=args.remove,
        )
    except (MoveError, KeyError, ValueError) as error:
        parser.exit(1, f"move_stage: {error}\n")
    print(report)


if __name__ == "__main__":
    main()
