"""LLM-backed significance reviewer for the local OpenAI-compatible proxy.

Sends candidate notes to the model and asks which are low-value. Any network or
parse failure falls back to keep-all, so a flaky model never destroys data.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from typing import Optional

from .compaction import Decision, NoteRef

DEFAULT_BASE_URL = "http://127.0.0.1:8787/v1"
DEFAULT_MODEL = "unsloth/Qwen3.8-Flash-Next-GGUF"

SYSTEM_PROMPT = (
    "You compact an agent's long-term memory. Each note is a free-text note an "
    "agent left for its future self. Judge each note's SIGNIFICANCE for future "
    "tasks. Age is NOT a reason to drop a note. Return one decision per note id."
)


@dataclass
class LLMConfig:
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    api_key: Optional[str] = None
    timeout: int = 120
    temperature: float = 0.2
    max_tokens: int = 1024

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            base_url=os.environ.get("SIMPLE_MEMORY_BASE_URL", DEFAULT_BASE_URL),
            model=os.environ.get("SIMPLE_MEMORY_MODEL", DEFAULT_MODEL),
            api_key=os.environ.get("UNSLOTH_PROXY_API_KEY"),
            timeout=int(os.environ.get("SIMPLE_MEMORY_TIMEOUT", "120")),
        )


def _user_prompt(notes: list[NoteRef]) -> str:
    lines = [f"[{i}] {n.value}" for i, n in enumerate(notes)]
    schema = json.dumps(
        {"decisions": [{"id": 0, "action": "keep|drop|rewrite", "value": "rewritten text or null"}]},
    )
    return (
        "Notes:\n" + "\n".join(lines) +
        "\n\nDecide significance for each note id. Reply ONLY with JSON matching:\n" + schema
    )


def _post_chat(cfg: LLMConfig, prompt: str) -> Optional[str]:
    body = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
    }
    req = urllib.request.Request(
        f"{cfg.base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.api_key or 'unused'}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None


def _parse(content: str) -> list[dict]:
    match = re.search(r"\[\s*\{.*\}\s*\]", content, re.DOTALL)
    if not match:
        return []
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, dict):
        parsed = parsed.get("decisions", [])
    return [d for d in parsed if isinstance(d, dict) and "id" in d]


class LLMReviewer:
    def __init__(self, notes: list[NoteRef], config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig.from_env()
        self._notes = notes

    def __call__(self, notes: list[NoteRef]) -> "dict[str, Decision]":
        if not notes:
            return {}
        content = _post_chat(self.config, _user_prompt(notes))
        if content is None:
            return {}
        decisions: "dict[str, Decision]" = {}
        for item in _parse(content):
            idx = item.get("id")
            if not isinstance(idx, int) or idx < 0 or idx >= len(notes):
                continue
            action = str(item.get("action", "keep")).lower()
            path = notes[idx].path
            if action == "drop":
                decisions[path] = Decision("drop")
            elif action == "rewrite" and item.get("value"):
                decisions[path] = Decision("rewrite", value=str(item["value"]).strip())
        return decisions
