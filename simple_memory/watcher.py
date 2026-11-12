"""Once-after-idle watcher: triggers a single compaction pass per user input."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from schema import codec

from .compaction import apply_decisions, build_manifest, collect_notes, should_compact
from .config import CompactionConfig
from .review import Reviewer


def _mtime(path: Path) -> Optional[datetime]:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


class Watcher:
    def __init__(self, root: str | Path, reviewer: Reviewer, config: CompactionConfig,
                 input_marker: str | Path, state_dir: str | Path,
                 chat_log_source: Optional[Callable[[], list[tuple[str, str]]]] = None):
        self.root = Path(root)
        self.reviewer = reviewer
        self.config = config
        self.input_marker = Path(input_marker)
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.last_run_file = self.state_dir / "last_run"
        self.chat_log_source = chat_log_source

    def _last_input(self) -> Optional[datetime]:
        return _mtime(self.input_marker)

    def _last_run(self) -> Optional[datetime]:
        return _mtime(self.last_run_file)

    def _due(self, now: datetime) -> bool:
        last_input = self._last_input()
        if last_input is None:
            return False
        last_run = self._last_run()
        if last_run is not None and last_run >= last_input:
            return False
        return should_compact(last_input, now, self.config)

    def run_once(self, now: Optional[datetime] = None) -> Optional[dict]:
        now = now or datetime.now(timezone.utc)
        if not self._due(now):
            return None
        kb = codec.load_knowledge_base(self.root)
        logs = self.chat_log_source() if self.chat_log_source else None
        manifest = build_manifest(kb, self.config, now, self._last_input(), logs)
        decisions = self.reviewer(collect_notes(kb, logs))
        if decisions:
            apply_decisions(kb, decisions)
            codec.dump_hosts(kb, self.root)
            codec.dump_entities(kb, self.root)
            codec.dump_personas(kb, self.root)
        self.last_run_file.touch()
        manifest["applied"] = len(decisions)
        return manifest

    def tick(self, now: Optional[datetime] = None) -> Optional[dict]:
        return self.run_once(now)
