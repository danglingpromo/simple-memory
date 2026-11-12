"""Note collection + significance-based compaction over the KnowledgeBase."""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from schema.models import KnowledgeBase

from .config import CompactionConfig


@dataclass
class NoteRef:
    path: str
    value: str
    source: str = "data"


@dataclass
class Decision:
    op: str
    value: Optional[str] = None


def should_compact(last_activity: Optional[datetime], now: datetime, config: CompactionConfig) -> bool:
    if last_activity is None:
        return False
    return (now - last_activity) >= timedelta(minutes=config.idle_pause_minutes)


def _iter_service_notes(services: dict, prefix: str):
    for name, svc in services.items():
        if svc.notes:
            yield NoteRef(f"{prefix}.{name}.notes", svc.notes)


def collect_notes(kb: KnowledgeBase, chat_logs: Optional[list[tuple[str, str]]] = None) -> list[NoteRef]:
    out: list[NoteRef] = []
    for hid, host in kb.hosts.items():
        base = f"hosts.{hid}"
        out.extend(_iter_service_notes(host.baremetal_services, f"{base}.baremetal_services"))
        out.extend(_iter_service_notes(host.containers.services, f"{base}.containers.services"))
        for i, mount in enumerate(host.mounts):
            if mount.notes:
                out.append(NoteRef(f"{base}.mounts[{i}].notes", mount.notes))
        gpu = host.hardware.gpu
        if dataclasses.is_dataclass(gpu) and getattr(gpu, "notes", None):
            out.append(NoteRef(f"{base}.hardware.gpu.notes", gpu.notes))
    for eid, ent in kb.entities.items():
        if ent.notes:
            out.append(NoteRef(f"entities.{eid}.notes", ent.notes))
    for pid, per in kb.personas.items():
        if per.notes:
            out.append(NoteRef(f"personas.{pid}.notes", per.notes))
    for src, text in (chat_logs or []):
        if text:
            out.append(NoteRef(src, text, source="chat_log"))
    return out


def build_manifest(kb: KnowledgeBase, config: CompactionConfig, now: datetime,
                   last_activity: Optional[datetime],
                   chat_logs: Optional[list[tuple[str, str]]] = None) -> dict:
    candidates = collect_notes(kb, chat_logs)
    return {
        "idle_pause_minutes": config.idle_pause_minutes,
        "trigger": should_compact(last_activity, now, config),
        "candidate_count": len(candidates),
        "candidates": [{"path": c.path, "source": c.source, "value": c.value} for c in candidates],
    }


def apply_decisions(kb: KnowledgeBase, decisions: dict[str, Decision]) -> int:
    changed = 0
    for path, dec in decisions.items():
        target = _resolve_note(kb, path)
        if target is None:
            continue
        new = None if dec.op == "drop" else dec.value
        if getattr(target, "notes", None) != new:
            target.notes = new
            changed += 1
    return changed


def _resolve_note(kb: KnowledgeBase, path: str):
    parts = path.split(".")
    if parts[0] == "hosts" and len(parts) >= 4:
        host = kb.hosts.get(parts[1])
        if host is None:
            return None
        if parts[2] == "baremetal_services":
            svc = host.baremetal_services.get(parts[3])
            return svc if svc and len(parts) > 4 and parts[4] == "notes" else None
        if parts[2] == "containers" and parts[3] == "services" and len(parts) >= 6:
            svc = host.containers.services.get(parts[4])
            return svc if svc and parts[5] == "notes" else None
        if parts[2] == "mounts":
            idx = int(parts[3].strip("[]"))
            if idx < len(host.mounts) and parts[4] == "notes":
                return host.mounts[idx]
            return None
        if parts[2] == "hardware" and parts[3] == "gpu" and len(parts) > 4 and parts[4] == "notes":
            gpu = host.hardware.gpu
            return gpu if dataclasses.is_dataclass(gpu) else None
        return None
    if parts[0] == "entities" and len(parts) == 3 and parts[2] == "notes":
        return kb.entities.get(parts[1])
    if parts[0] == "personas" and len(parts) == 3 and parts[2] == "notes":
        return kb.personas.get(parts[1])
    return None
