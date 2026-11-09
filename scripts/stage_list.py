"""Reads ``stages.yaml``, the ordered list of the notebook's stages and the files of each."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

STAGES_FILE = "stages.yaml"


@dataclass(frozen=True)
class Stage:
    """One entry of ``stages.yaml``."""

    stage_id: str
    title_ja: str
    module: str
    questions: tuple[str, ...]
    caches: tuple[str, ...]
    results: tuple[str, ...]
    figures: tuple[str, ...]
    summary_key: str | None
    expected_prefixes: tuple[str, ...]
    """Path prefixes of its values in paper_values.json (``expected_prefix``: one or a list)."""

    def owns_value(self, path: str) -> bool:
        """Whether a summary path of paper_values.json belongs to this stage."""
        return path.startswith(self.expected_prefixes) if self.expected_prefixes else False


def _strings(raw: Any) -> tuple[str, ...]:
    if isinstance(raw, str):
        return (raw,)
    return tuple(str(item) for item in (raw or []))


def _optional(raw: Any) -> str | None:
    return None if raw is None else str(raw)


def load_stages(root: Path) -> list[Stage]:
    """Reads the stages of ``stages.yaml`` under ``root``, in notebook order."""
    entries = yaml.safe_load((root / STAGES_FILE).read_text(encoding="utf-8"))
    return [
        Stage(
            stage_id=str(entry["id"]),
            title_ja=str(entry["title_ja"]),
            module=str(entry["module"]),
            questions=_strings(entry.get("questions")),
            caches=_strings(entry.get("caches")),
            results=_strings(entry.get("results")),
            figures=_strings(entry.get("figures")),
            summary_key=_optional(entry.get("summary_key")),
            expected_prefixes=_strings(entry.get("expected_prefix")),
        )
        for entry in entries
    ]


def find_stage(stages: Sequence[Stage], stage_id: str) -> Stage:
    """Returns the stage with ``stage_id``; raises KeyError when there is none."""
    for stage in stages:
        if stage.stage_id == stage_id:
            return stage
    raise KeyError(f"no stage {stage_id} in {STAGES_FILE}")
