"""simple-memory: significance-based compaction of agentic awareness notes.

Runs once after the last user input (default 15 min idle). Removal is based on
significance, never on a timer. Reads/writes the agenticAwareness YAML files
through their strict schema.
"""
import os as _os
import sys as _sys
from pathlib import Path as _Path

_ROOT = _os.environ.get(
    "AGENTICAWARENESS_ROOT", str(_Path.home() / "repos" / "agenticAwareness")
)
if _ROOT and _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)

from .config import CompactionConfig, DEFAULT_IDLE_PAUSE_MINUTES
from .compaction import (
    NoteRef,
    Decision,
    collect_notes,
    should_compact,
    build_manifest,
    apply_decisions,
)
from .review import Reviewer, default_reviewer, keep_all
from .watcher import Watcher

__all__ = [
    "CompactionConfig",
    "DEFAULT_IDLE_PAUSE_MINUTES",
    "NoteRef",
    "Decision",
    "collect_notes",
    "should_compact",
    "build_manifest",
    "apply_decisions",
    "Reviewer",
    "default_reviewer",
    "keep_all",
    "Watcher",
]
