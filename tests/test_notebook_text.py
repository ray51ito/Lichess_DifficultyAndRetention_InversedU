"""Checks the text of the built notebook: citations against the reference list, unused top-level
names in code cells, and terms that must not come back."""

import ast
import re
from pathlib import Path
from typing import Any

import nbformat

from lichess_d1 import config

# Heading of the markdown cell that holds the reference list
REFERENCES_HEADING = "## 参考文献"
# References without an author and year, matched by a keyword anywhere in the body
KEYWORD_REFERENCES = ("scalachess",)
# Retired terms that must not appear in any cell or output
FORBIDDEN_TERMS = (re.compile("ビンの曲線"), re.compile("binned curve", re.IGNORECASE))
# Top-level names allowed to stay unread by every code cell
UNUSED_NAMES_ALLOWED: frozenset[str] = frozenset()

# Half- and full-width forms (U+FF08, U+FF09, U+FF0C, U+FF1B) are both used in the prose
_OPEN = r"[(\uFF08]"
_CLOSE = r"[)\uFF09]"
_COMMA = r"[,\uFF0C]"
_YEAR = r"(?:1[5-9]|20)\d\d"
_SURNAME = r"[A-ZÀ-ÖØ-Þ][\w'\u2019\-]*"
_PARENTHESES = re.compile(rf"{_OPEN}([^()\uFF08\uFF09]*){_CLOSE}")
_PART_SEPARATOR = re.compile(r"[;\uFF1B]")
# Authors with the first surname captured: "Royston, Altman & Sauerbrei", "James et al."
_AUTHORS = (
    rf"(?<![A-Za-zÀ-ÿ'\u2019\-])({_SURNAME})"
    rf"(?:(?:{_COMMA}\s*|\s*&\s*|\s+and\s+){_SURNAME})*(?:\s+et al\.)?"
)
# One part of a parenthesis: "Wooldridge, 2010, 10章", "Smith 2020"
_PARENTHETICAL = re.compile(rf"{_AUTHORS}{_COMMA}?\s*({_YEAR})(?![\d年])")
# Authors outside the parenthesis: "Cattaneo et al. (2024)", "Curran & Bauer (2011)"
_NARRATIVE = re.compile(rf"{_AUTHORS}\s*{_OPEN}({_YEAR})[a-z]?(?:{_CLOSE}|{_COMMA})")
_REFERENCE_LINE = re.compile(rf"^- ({_SURNAME})[,.].*?\(({_YEAR})[a-z]?\)")

Key = tuple[str, str]


def _read_cells(notebook_path: Path) -> list[Any]:
    notebook = nbformat.read(notebook_path, as_version=4)  # type: ignore[no-untyped-call]
    return list(notebook.cells)


def _split_references(cells: list[Any]) -> tuple[str, str]:
    """Returns the body markdown and the reference-list cell."""
    markdown = [cell.source for cell in cells if cell.cell_type == "markdown"]
    references = [text for text in markdown if text.startswith(REFERENCES_HEADING)]
    assert len(references) == 1, f"expected one {REFERENCES_HEADING!r} cell, got {len(references)}"
    body = "\n".join(text for text in markdown if text is not references[0])
    return body, references[0]


def find_references(reference_cell: str) -> set[Key]:
    """Returns (first-author surname, year) of each reference, or (keyword, "") for keyword ones."""
    keys: set[Key] = set()
    for line in reference_cell.splitlines():
        if not line.startswith("- "):
            continue
        keywords = [word for word in KEYWORD_REFERENCES if word in line.lower()]
        match = _REFERENCE_LINE.match(line)
        if keywords:
            keys.update((word, "") for word in keywords)
        elif match:
            keys.add((match.group(1).lower(), match.group(2)))
        else:
            raise AssertionError(f"unparsable reference line: {line}")
    return keys


def find_citations(body: str) -> set[Key]:
    """Returns (first-author surname, year) of each citation in the body, plus keyword citations."""
    keys: set[Key] = set()
    for group in _PARENTHESES.findall(body):
        for part in _PART_SEPARATOR.split(group):
            match = _PARENTHETICAL.search(part)
            if match:
                keys.add((match.group(1).lower(), match.group(2)))
    keys.update((m.group(1).lower(), m.group(2)) for m in _NARRATIVE.finditer(body))
    keys.update((word, "") for word in KEYWORD_REFERENCES if word in body.lower())
    return keys


def check_references(notebook_path: Path) -> tuple[list[Key], list[Key]]:
    """Returns the references never cited and the citations missing from the reference list."""
    body, reference_cell = _split_references(_read_cells(notebook_path))
    references = find_references(reference_cell)
    citations = find_citations(body)
    return sorted(references - citations), sorted(citations - references)


def _collect_defined_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                names.update(
                    sub.id
                    for sub in ast.walk(target)
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store)
                )
    return names


def _collect_used_names(tree: ast.Module) -> set[str]:
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            used.add(node.attr)
    return used


def check_unused_names(notebook_path: Path) -> list[str]:
    """Returns top-level names (not starting with "_") defined in a code cell that no code cell
    ever reads."""
    trees = [
        ast.parse(cell.source) for cell in _read_cells(notebook_path) if cell.cell_type == "code"
    ]
    defined = set().union(*(_collect_defined_names(tree) for tree in trees))
    used = set().union(*(_collect_used_names(tree) for tree in trees))
    unused = defined - used - UNUSED_NAMES_ALLOWED
    return sorted(name for name in unused if not name.startswith("_"))


def _collect_cell_texts(cell: Any) -> list[str]:
    texts = [cell.source]
    for output in cell.get("outputs", []):
        if "text" in output:
            texts.append(output["text"])
        texts.extend(
            value for kind, value in output.get("data", {}).items() if kind.startswith("text/")
        )
    return texts


def check_forbidden_terms(notebook_path: Path) -> list[str]:
    """Returns "cell <index>: <term>" for each forbidden term in a cell's source or text output."""
    found: list[str] = []
    for index, cell in enumerate(_read_cells(notebook_path)):
        text = "\n".join(_collect_cell_texts(cell))
        found.extend(
            f"cell {index}: {match}" for term in FORBIDDEN_TERMS for match in term.findall(text)
        )
    return found


def test_references_match_citations() -> None:
    uncited, missing = check_references(config.NOTEBOOK_PATH)
    assert not uncited and not missing, f"uncited references: {uncited}; not in list: {missing}"


def test_no_unused_top_level_names() -> None:
    unused = check_unused_names(config.NOTEBOOK_PATH)
    assert not unused, f"top-level names never used: {unused}"


def test_no_forbidden_terms() -> None:
    found = check_forbidden_terms(config.NOTEBOOK_PATH)
    assert not found, f"forbidden terms: {found}"
