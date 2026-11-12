"""Compaction configuration. Idle pause only gates when the agent is *asked* to
review; it never deletes on its own."""
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_IDLE_PAUSE_MINUTES = 15


@dataclass
class CompactionConfig:
    idle_pause_minutes: int = DEFAULT_IDLE_PAUSE_MINUTES
