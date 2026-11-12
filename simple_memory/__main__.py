"""CLI: watch an input-marker file; run one compaction pass per idle period."""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import CompactionConfig, DEFAULT_IDLE_PAUSE_MINUTES
from .review import default_reviewer
from .watcher import Watcher


def main(argv=None):
    parser = argparse.ArgumentParser(description="simple-memory auto-compaction")
    parser.add_argument("--kb", default=str(Path.home() / "repos" / "agenticAwareness"))
    parser.add_argument("--input-marker", required=True, help="file whose mtime marks last user input")
    parser.add_argument("--state-dir", default=str(Path.home() / ".local" / "state" / "simple-memory"))
    parser.add_argument("--idle", type=int, default=DEFAULT_IDLE_PAUSE_MINUTES)
    parser.add_argument("--interval", type=int, default=60, help="poll seconds")
    parser.add_argument("--once", action="store_true", help="evaluate a single tick and exit")
    args = parser.parse_args(argv)

    config = CompactionConfig(idle_pause_minutes=args.idle)
    watcher = Watcher(args.kb, default_reviewer, config, args.input_marker, args.state_dir)

    if args.once:
        result = watcher.tick(datetime.now(timezone.utc))
        print("ran" if result else "idle")
        return 0

    while True:
        watcher.tick(datetime.now(timezone.utc))
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
