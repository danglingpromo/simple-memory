"""Pluggable significance reviewer. A Reviewer maps candidate notes to decisions.

The default keeps everything (safe without an LLM). Wire an LLM-backed reviewer
to actually judge low-value notes; nothing is removed on a timer.
"""
from __future__ import annotations

from typing import Callable

from .compaction import Decision, NoteRef

Reviewer = Callable[[list[NoteRef]], "dict[str, Decision]"]


def keep_all(notes: list[NoteRef]) -> "dict[str, Decision]":
    return {}


default_reviewer: Reviewer = keep_all
